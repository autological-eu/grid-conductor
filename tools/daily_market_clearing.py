"""Competitive daily synthetic clearing with forecast-informed storage policies.

Forecasts are storage-free network prices, not realised prices. Each storage
operator plans separately over the full declared horizon. Only the next day is
cleared; inventories carry forward. This is not an equilibrium or annual optimum.
"""
import argparse
import fcntl
import json
import logging
import os
import resource
import signal
import time
from pathlib import Path

import highspy
import numpy as np
import pandas as pd
import pypsa
from scipy.sparse import coo_matrix, hstack

from european_physical_bids_2025 import solver as forecast_solver
from european_reservoir_clearing_2025 import setup, REFERENCE
from hourly_renewable_estimates import digest
from perfect_foresight_dispatch import build_lp, compile_case, native_check
from synthetic_bids_2025 import SOURCE

ROOT = Path(__file__).resolve().parents[1]
THROUGHPUT_COST = .001  # EUR/MWh; explicit bid friction, not generation cost.
TOL = 1e-4


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def make_solver(p, limit=60, solver='simplex'):
    A = p['A']; h = highspy.Highs()
    for key, value in [('output_flag', False), ('threads', 1), ('solver', solver),
                       ('time_limit', limit)]:
        h.setOptionValue(key, value)
    lp = highspy.HighsLp()
    lp.num_col_ = A.shape[1]; lp.num_row_ = A.shape[0]
    lp.col_cost_ = p['cost']; lp.col_lower_ = p['lower']; lp.col_upper_ = p['upper']
    lp.row_lower_ = p['row_lower']; lp.row_upper_ = p['row_upper']
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_ = A.indptr; lp.a_matrix_.index_ = A.indices
    lp.a_matrix_.value_ = A.data
    h.passModel(lp)
    return h


def optimal(h):
    h.run(); retry = h.getModelStatus() != highspy.HighsModelStatus.kOptimal
    if retry:
        h.clearSolver(); h.run()
    if h.getModelStatus() != highspy.HighsModelStatus.kOptimal:
        raise ValueError('Nonoptimal result: ' + str(h.getModelStatus()))
    return retry


def clear_optimal(h,p,limit):
    """Bound simplex stalls; accept only an optimal unchanged-input solve."""
    attempts=[]
    h.setOptionValue('solver','simplex')
    h.setOptionValue('time_limit',min(10.,limit))
    for method in ['warm_simplex','cold_simplex','cold_ipm']:
        if method=='cold_simplex':h.clearSolver()
        if method=='cold_ipm':h=make_solver(p,limit,'ipm')
        started=time.perf_counter();h.run()
        status=h.getModelStatus()
        attempts.append(dict(method=method,status=str(status),seconds=time.perf_counter()-started))
        if status==highspy.HighsModelStatus.kOptimal:return h,attempts
    raise ValueError('Nonoptimal daily result after bounded fallback: '+str(status))


def residual(p, x):
    ax = p['A'] @ x
    return max(float(np.maximum(p['lower'] - x, 0).max()),
               float(np.maximum(x - p['upper'], 0).max()),
               float(np.maximum(p['row_lower'] - ax, 0).max()),
               float(np.maximum(ax - p['row_upper'], 0).max()))


def price_forecast(m, hours, limit=60):
    """Perfect exogenous inputs, storage-free clearing prices; no observed prices."""
    h = forecast_solver(m); h.setOptionValue('time_limit', limit)
    nc = m['A'].shape[1]; columns = np.arange(nc, dtype=np.int32)
    rows = np.arange(m['A'].shape[0], dtype=np.int32)
    prices = []; largest = 0.; begin = time.perf_counter(); retries = 0
    for t in range(hours):
        p = dict(A=m['A'], cost=np.r_[m['cost'][t], np.zeros(m['nl'] + m['nz'])],
                 lower=np.r_[np.zeros(m['ng']), m['link_min'][t], np.full(m['nz'], -np.inf)],
                 upper=np.r_[m['availability'][t], m['link_max'][t], np.full(m['nz'], np.inf)],
                 row_lower=np.r_[m['load'][t], np.zeros(len(m['islands'])), -m['ratings']],
                 row_upper=np.r_[m['load'][t], np.zeros(len(m['islands'])), m['ratings']])
        h.changeColsBounds(nc, columns, p['lower'], p['upper'])
        h.changeColsCost(nc, columns, p['cost'])
        h.changeRowsBounds(len(rows), rows, p['row_lower'], p['row_upper'])
        retries += int(optimal(h)); sol = h.getSolution()
        largest = max(largest, residual(p, np.asarray(sol.col_value)))
        if largest > TOL: raise ValueError('Forecast network replay failed')
        prices.append(sol.row_dual[:m['nz']])
    return np.asarray(prices), dict(seconds=time.perf_counter()-begin,
                                    maximum_residual=largest, cold_retries=retries)


def forecast_with_hydro(n,m,hours):
    """Add mean-inflow hydro offers ONLY to the expected-price proxy.

    Not dispatch-derived availability; no water is added to actual clearing.
    The constant offer is capped by turbines and based on declared horizon mean
    inflow times discharge efficiency. Storage arbitrage is excluded here.
    """
    s=n.storage_units.loc[n.storage_units.carrier=='hydro']
    if s.empty:return m
    inflow=n.get_switchable_as_dense('StorageUnit','inflow').loc[:,s.index].iloc[:hours]
    sustainable=np.minimum((inflow.mean()*s.efficiency_dispatch).values,
                            (s.p_nom*s.p_max_pu).values)
    rows=np.array([m['zones'].index(m['buszone'][bus]) for bus in s.bus])
    G=coo_matrix((np.ones(len(s)),(rows,np.arange(len(s)))),shape=(m['A'].shape[0],len(s))).tocsc()
    f=m.copy();f['A']=hstack([m['A'][:,:m['ng']],G,m['A'][:,m['ng']:]],format='csc')
    f['availability']=np.c_[m['availability'],np.tile(sustainable,(len(m['load']),1))]
    f['cost']=np.c_[m['cost'],np.tile(s.marginal_cost.values,(len(m['load']),1))]
    f['ng']=m['ng']+len(s)
    return f


def reachable_bounds(inflow, charge, discharge, cap, eta_c, eta_d, phi, terminal):
    """Exact separable backward inventory reachability for declared bid modes.

    Spill can cancel current inflow only. These bounds ensure existence of a
    future water-feasible trajectory, not that future network scarcity disappears.
    """
    T, ns = inflow.shape; lo = np.zeros((T+1, ns)); hi = np.tile(cap, (T+1, 1))
    lo[-1] = terminal; hi[-1] = terminal
    for t in range(T-1, -1, -1):
        lo[t] = np.maximum(0, (lo[t+1] - inflow[t] - charge[t]*eta_c) / phi)
        hi[t] = np.minimum(cap, (hi[t+1] + discharge[t]/eta_d) / phi)
        if np.any(lo[t] > hi[t] + 1e-6): raise ValueError('Unreachable closing inventory')
    return lo, hi


def plan_storage(n, m, forecast, initial, terminal, limit=60):
    """Independent price-taking hourly operator plans; extract future energy values."""
    T = len(forecast); s = n.storage_units; ns = len(s)
    inflow = n.get_switchable_as_dense('StorageUnit', 'inflow').iloc[:T].values
    cap = (s.p_nom*s.max_hours).values
    eta_c = s.efficiency_store.values; eta_d = s.efficiency_dispatch.values
    phi = 1-s.standing_loss.values
    cmax = (-s.p_nom*s.p_min_pu).values; dmax = (s.p_nom*s.p_max_pu).values
    if len(n.stores) or any(not v.empty for k,v in n.storage_units_t.items() if k != 'inflow'):
        raise ValueError('Unsupported temporal storage/Stores')
    if (not np.isfinite(inflow).all() or (inflow < 0).any() or
        np.any(eta_d <= 0) or np.any(eta_d > 1) or np.any(eta_c < 0) or
        np.any(eta_c > 1) or np.any(phi <= 0) or np.any(phi > 1)):
        raise ValueError('Invalid storage physics')
    for boundary in [initial, terminal]:
        if np.shape(boundary) != (ns,) or not np.isfinite(boundary).all() or np.any(boundary < 0) or np.any(boundary > cap+1e-6):
            raise ValueError('Invalid inventory boundary')
    values = np.zeros((T, ns, 4)); future = np.zeros((T, ns)); records=[]
    j = np.arange(T); begin=time.perf_counter()
    for k, (asset, row) in enumerate(s.iterrows()):
        area=m['zones'].index(m['buszone'][row.bus]); price=forecast[:,area]
        rr=np.r_[j,j,j,j,j[1:]]
        cc=np.r_[4*j,4*j+1,4*j+2,4*j+3,4*j[:-1]+2]
        vv=np.r_[np.full(T,-eta_c[k]),np.full(T,1/eta_d[k]),np.ones(2*T),np.full(T-1,-phi[k])]
        A=coo_matrix((vv,(rr,cc)),shape=(T,4*T)).tocsc()
        # Negative-price selling is not an operator's profit-maximising offer;
        # forbid it so negative prices cannot reward artificial loss cycles.
        dc=np.where(price > 0, dmax[k], 0.)
        upper=np.c_[np.full(T,cmax[k]),dc,np.full(T,cap[k]),inflow[:,k]].ravel()
        lower=np.zeros(4*T); lower[-2]=terminal[k]; upper[-2]=terminal[k]
        rhs=inflow[:,k].copy(); rhs[0]+=phi[k]*initial[k]
        cost=np.c_[price+THROUGHPUT_COST, row.marginal_cost-price+THROUGHPUT_COST,
                   np.zeros((T,2))].ravel()
        p=dict(A=A,lower=lower,upper=upper,cost=cost,row_lower=rhs,row_upper=rhs)
        h=make_solver(p,limit); started=time.perf_counter(); retry=optimal(h)
        sol=h.getSolution(); x=np.asarray(sol.col_value); error=residual(p,x)
        if error>TOL: raise ValueError('Operator plan replay failed '+asset)
        v=x.reshape(T,4); values[:,k]=v
        if np.any((v[:,0]>1e-6)&(v[:,1]>1e-6)): raise ValueError('Operator plan cycles '+asset)
        # Value at end of hour t is negative derivative of subsequent cost.
        # Next water-row RHS changes by phi * previous end inventory.
        dual=np.asarray(sol.row_dual)
        future[:-1,k]=-phi[k]*dual[1:]
        records.append(dict(asset=asset,seconds=time.perf_counter()-started,
                            maximum_residual=error,cold_retry=retry))
    # A submitted direction is fixed for that delivery hour; quantities remain
    # endogenous in clearing. Idle planner hours offer discharge only. Natural
    # reservoir spill remains available even when a generation bid is rejected.
    charging=values[:,:,0]>1e-6
    charge=np.where(charging,cmax,0.)
    discharge=np.where(charging,0.,dmax)
    lo,hi=reachable_bounds(inflow,charge,discharge,cap,eta_c,eta_d,phi,terminal)
    if np.any(initial<lo[0]-TOL) or np.any(initial>hi[0]+TOL):
        raise ValueError('Submitted modes cannot close initial inventory')
    return dict(values=values,future_value=future,charge_max=charge,discharge_max=discharge,
                reachable_lower=lo,reachable_upper=hi,inflow=inflow,
                seconds=time.perf_counter()-begin,operators=records)


def daily_lp(n,m,start,end,initial,terminal,policy):
    p=build_lp(n,m,start,end,initial,terminal)
    ns=p['ns']; nb=p['nb']; upper=p['upper'].reshape(end-start,p['width'])
    lower=p['lower'].reshape(end-start,p['width'])
    upper[:,nb:nb+ns]=policy['charge_max'][start:end]
    upper[:,nb+ns:nb+2*ns]=policy['discharge_max'][start:end]
    # The final day closes exactly; earlier days have reachable bounds, never
    # fixed reference/plan inventories.
    lower[-1,nb+2*ns:nb+3*ns]=policy['reachable_lower'][end]
    upper[-1,nb+2*ns:nb+3*ns]=policy['reachable_upper'][end]
    p['operating_cost']=p['cost'].copy()
    cost=p['cost'].reshape(end-start,p['width'])
    cost[:,nb+ns:nb+2*ns]+=THROUGHPUT_COST
    cost[-1,nb+2*ns:nb+3*ns]-=policy['future_value'][end-1]
    return p


def clear_day(n,m,start,end,initial,terminal,policy,cache=None,limit=60):
    started=time.perf_counter(); p=daily_lp(n,m,start,end,initial,terminal,policy)
    if cache is None or cache['hours'] != end-start:
        h=make_solver(p,limit); cache=dict(hours=end-start,solver=h)
    else:
        h=cache['solver']; cols=np.arange(len(p['cost']),dtype=np.int32)
        rows=np.arange(len(p['row_lower']),dtype=np.int32)
        h.changeColsBounds(len(cols),cols,p['lower'],p['upper'])
        h.changeColsCost(len(cols),cols,p['cost'])
        h.changeRowsBounds(len(rows),rows,p['row_lower'],p['row_upper'])
    prepared=time.perf_counter()-started; started=time.perf_counter()
    h,attempts=clear_optimal(h,p,limit); cache['solver']=h
    elapsed=time.perf_counter()-started; sol=h.getSolution(); x=np.asarray(sol.col_value)
    error=residual(p,x)
    if error>TOL: raise ValueError('Daily primal replay failed')
    v=x.reshape(end-start,p['width']); nb=p['nb']; ns=p['ns']
    c=v[:,nb:nb+ns]; d=v[:,nb+ns:nb+2*ns]; soc=v[:,nb+2*ns:nb+3*ns]
    previous=np.vstack([initial,soc[:-1]])
    water=float(np.abs(soc-previous*p['phi']-c*p['eta_c']+d/p['eta_d']-p['inflow']+v[:,nb+3*ns:]).max())
    cycling=int(np.count_nonzero((c>1e-6)&(d>1e-6)))
    if water>TOL or cycling: raise ValueError('Daily water/cycling replay failed')
    return dict(values=v,prices=np.asarray(sol.row_dual).reshape(end-start,p['rowwidth'])[:,:m['nz']],
                objective=float(p['operating_cost']@x),bid_objective=float(p['cost']@x),
                maximum_primal_residual=error,maximum_inventory_residual=water,
                simultaneous_storage_hours=cycling,solver_seconds=elapsed,
                preparation_seconds=prepared,cold_retry=len(attempts)>1,solver_attempts=attempts,variables=p['A'].shape[1],
                rows=p['A'].shape[0],nonzeros=p['A'].nnz),cache


def native_day(n,m,start,end,initial,terminal,policy,result):
    # Native comparison fixes the end inventory actually selected by the bid
    # policy, preserving submitted directions. Add the same discharge friction.
    p=n.copy(); ns=len(p.storage_units)
    p.storage_units_t.p_min_pu=pd.DataFrame(-policy['charge_max']/p.storage_units.p_nom.values,
                                         index=p.snapshots[:len(policy['charge_max'])],columns=p.storage_units.index)
    p.storage_units_t.p_max_pu=pd.DataFrame(policy['discharge_max']/p.storage_units.p_nom.values,
                                         index=p.snapshots[:len(policy['discharge_max'])],columns=p.storage_units.index)
    # Conditioned end inventory makes the terminal value a constant. Native
    # operating cost needs the same small throughput friction as daily clearing.
    p.storage_units.marginal_cost+=THROUGHPUT_COST
    values=result['values']; nb=m['A'].shape[1]
    friction=THROUGHPUT_COST*values[:,nb+ns:nb+2*ns].sum()
    check=native_check(p,m,start,end,initial,terminal,result['objective']+friction)
    check['comparison']='Native operating optimum conditional on cleared terminal inventories and submitted directions; not annual policy optimality'
    return check


def provenance(args, initial, audit):
    names=['perfect_foresight_dispatch.py','european_reservoir_clearing_2025.py',
           'european_physical_bids_2025.py','irena_linear_dispatch_capacity.py',
           'synthetic_bids_2025.py','derive_physical_zonal_constraints.py',
           'hourly_renewable_estimates.py','submonthly_inventory_driver.py']
    return dict(source=digest(SOURCE),producer=digest(__file__),
                dependencies={name:digest(Path(__file__).with_name(name)) for name in names},
                boundary_sha256=digest(REFERENCE/'annual-state.npz'),
                initial_inventory_mwh=initial.tolist(),hours=args.hours,
                investments=json.loads(Path(args.investments).read_text()) if args.investments else [],
                capacity_audit=audit,throughput_cost_eur_mwh=THROUGHPUT_COST,
                calendar='24 hourly UTC periods per day; hourly approximation, not local 23/25h or quarter-hour market calendar',
                forecast='Network forecast excludes storage arbitrage and adds mean-inflow turbine-capped hydro offers; perfect source demand/availability/costs, no observed prices or equilibrium iteration',
                protocol=dict(primal_tolerance=TOL,native_absolute_eur=.05,native_relative=1e-8,time_limit=args.time_limit),
                packages=dict(pypsa=pypsa.__version__,highs=highspy.Highs().version(),numpy=np.__version__,scipy=__import__('scipy').__version__))


def run(args):
    begin=time.perf_counter(); n,ref,domain,_,audit,_,_=setup()
    with np.load(REFERENCE/'annual-state.npz',allow_pickle=False) as f:
        initial=np.maximum(f['inventories_mwh'].reshape(60,160)[0],0)
    np.testing.assert_array_equal(n.storage_units.index.values,np.array(domain['storage_ids']))
    weather=pypsa.Network(SOURCE).get_switchable_as_dense('Generator','p_max_pu').copy()
    manifest=provenance(args,initial,audit); write_json(args.output/'manifest.json',manifest)
    cases=[('baseline',[])]+([('investment',manifest['investments'])] if manifest['investments'] else [])
    summaries=[]
    for label,items in cases:
        case,m=compile_case(n,ref,items,weather)
        start_state=np.r_[initial,np.zeros(len(case.storage_units)-len(initial))]
        closing=start_state.copy(); folder=args.output/label; folder.mkdir()
        fprices,forecast_receipt=price_forecast(forecast_with_hydro(case,m,args.hours),args.hours,args.time_limit)
        print(label,'forecast complete',forecast_receipt['seconds'],flush=True)
        policy=plan_storage(case,m,fprices,start_state,closing,args.time_limit)
        np.savez_compressed(folder/'policy.npz',forecast=fprices,**{k:v for k,v in policy.items() if isinstance(v,np.ndarray)})
        write_json(folder/'policy.json',dict(seconds=policy['seconds'],operators=policy['operators'],forecast=forecast_receipt,sha256=digest(folder/'policy.npz')))
        print(label,'operator plans complete',policy['seconds'],flush=True)
        current=start_state.copy(); records=[]; cache=None
        native_days={0,args.hours//24//2,args.hours//24-1} if args.native else set()
        for day,start in enumerate(range(0,args.hours,24)):
            end=start+24
            result,cache=clear_day(case,m,start,end,current,closing,policy,cache,args.time_limit)
            values=result['values']; nb=m['A'].shape[1]; ns=len(case.storage_units)
            final=values[-1,nb+2*ns:nb+3*ns].copy()
            # Clip only recorded numerical bound roundoff, never a material state.
            cap=(case.storage_units.p_nom*case.storage_units.max_hours).values
            corrected=np.minimum(np.maximum(final,0),cap)
            correction=float(np.abs(corrected-final).max())
            if correction>1e-6: raise ValueError('Material inventory clipping')
            if day in native_days:
                result['native_check']=native_day(case,m,start,end,current,final,policy,result)
            path=folder/f'{day:03d}.npz'
            np.savez_compressed(path,values=values,prices=result['prices'],initial=current)
            record={k:v for k,v in result.items() if not isinstance(v,np.ndarray)}
            record.update(day=day,start_hour=start,end_hour=end,witness_sha256=digest(path),maximum_boundary_roundoff_mwh=correction)
            write_json(folder/f'{day:03d}.json',record); records.append(record); current=corrected
            write_json(args.output/'status.json',dict(status='running',pid=os.getpid(),case=label,days_completed=day+1,total_days=args.hours//24))
            if day%30==0 or end==args.hours:print(label,'day',day+1,'/',args.hours//24,'solve',result['solver_seconds'],flush=True)
        closure=float(np.abs(current-closing).max())
        if closure>TOL: raise ValueError('Annual/horizon closure failed')
        value=dict(case=label,hours=args.hours,days=len(records),storage_units=len(case.storage_units),
                   zones=m['zones'],storage_ids=case.storage_units.index.tolist(),
                   total_operating_cost_eur=sum(r['objective'] for r in records),
                   forecast=forecast_receipt,operator_planning_seconds=policy['seconds'],
                   clearing_seconds=sum(r['solver_seconds'] for r in records),
                   preparation_seconds=sum(r['preparation_seconds'] for r in records),
                   maximum_primal_residual=max(r['maximum_primal_residual'] for r in records),
                   maximum_inventory_residual=max(r['maximum_inventory_residual'] for r in records),
                   closure_residual_mwh=closure,simultaneous_storage_hours=sum(r['simultaneous_storage_hours'] for r in records),
                   cold_retries=sum(int(r['cold_retry']) for r in records),
                   interior_point_fallbacks=sum(any(a['method']=='cold_ipm' for a in r['solver_attempts']) for r in records),
                   policy_sha256=digest(folder/'policy.npz'),daily_receipts_sha256={f'{r["day"]:03d}.json':digest(folder/f'{r["day"]:03d}.json') for r in records},
                   native_checks=[dict(day=r['day'],**r['native_check']) for r in records if 'native_check' in r])
        write_json(folder/'summary.json',value); summaries.append(value)
    write_json(args.output/'summary.json',dict(provenance=manifest,cases=summaries,
        total_elapsed_seconds=time.perf_counter()-begin,peak_process_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        operating_cost_change_eur=summaries[1]['total_operating_cost_eur']-summaries[0]['total_operating_cost_eur'] if len(summaries)>1 else None,
        status='completed_daily_policy_simulation_not_annual_optimum',
        limitations=['Independent price-taking storage policies use no-arbitrage expected prices with mean-inflow hydro offers; not self-consistent perfect price forecasts or strategic equilibrium',
                     'Charge/sell directions fixed by operator plan; cleared quantities and daily inventories adapt, but mode restrictions can bias investment estimates',
                     'UTC hourly calendar; not actual local delivery-day or quarter-hour EUPHEMIA order types',
                     'Country/island GSK physical N-0 constraints, not audited bidding-zone/commercial JAO constraints',
                     'Synthetic thermal costs and IRENA linear wind/solar commissioning; empirical and investment gates remain open',
                     'Gross operating-cost differences exclude capex; no emissions result or browser integration']))


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.WARNING)
    parser=argparse.ArgumentParser(); parser.add_argument('--hours',type=int,default=48)
    parser.add_argument('--investments'); parser.add_argument('--native',action='store_true')
    parser.add_argument('--time-limit',type=float,default=60)
    parser.add_argument('--output',type=Path,required=True); args=parser.parse_args()
    if args.hours<24 or args.hours>8760 or args.hours%24 or not np.isfinite(args.time_limit) or args.time_limit<=0:
        parser.error('Whole UTC days and finite positive time budget required')
    resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3)); signal.alarm(7200)
    args.output.mkdir(parents=True,exist_ok=True)
    with (args.output/'driver.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (args.output/'manifest.json').exists() or (args.output/'baseline').exists():parser.error('Use fresh output; no implicit resume or overwrite')
        write_json(args.output/'status.json',dict(status='running',pid=os.getpid()))
        try:run(args)
        except Exception as exc:
            write_json(args.output/'status.json',dict(status='failed',error=str(exc)));raise
        write_json(args.output/'status.json',dict(status='completed',summary_sha256=digest(args.output/'summary.json')))
