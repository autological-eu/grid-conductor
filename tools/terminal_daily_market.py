"""Daily simple rules with an explicit final-48h network mode settlement."""
import argparse
import fcntl
import json
import logging
import os
from pathlib import Path
import resource
import signal
import time

import numpy as np
import pandas as pd
import pypsa
import highspy

from daily_market_clearing import (write_json, make_solver, clear_optimal, residual,
                                  price_forecast, forecast_with_hydro, TOL)
from european_reservoir_clearing_2025 import setup, REFERENCE
from perfect_foresight_dispatch import build_lp
from synthetic_bids_2025 import SOURCE
from hourly_renewable_estimates import digest
from simple_resource_bids import (configuration, cost_assumptions, compile_case,
                                  prepare_storage, ROOT)
from terminal_settlement_bids import storage_bids


def daily_lp(n,m,start,end,initial,terminal,bids):
    p = build_lp(n,m,start,end,initial,terminal)
    T=end-start; nb=p['nb']; ns=p['ns']
    upper=p['upper'].reshape(T,p['width']); lower=p['lower'].reshape(T,p['width'])
    upper[:,nb:nb+ns]=bids['charge_max']; upper[:,nb+ns:nb+2*ns]=bids['discharge_max']
    lower[-1,nb+2*ns:nb+3*ns]=bids['reachable_lower']
    upper[-1,nb+2*ns:nb+3*ns]=bids['reachable_upper']
    # Resource opportunity bids are distinct from physical variable operating cost.
    operating=p['cost'].reshape(T,p['width']).copy()
    operating[:,nb+ns:nb+2*ns]+=bids['wear']
    p['operating_cost']=operating.ravel()
    costs=p['cost'].reshape(T,p['width'])
    costs[:,nb:nb+ns]=-bids['buy']
    costs[:,nb+ns:nb+2*ns]=bids['sell']
    return p


def clear_day(n,m,start,end,initial,terminal,bids,cache=None,limit=60):
    begin=time.perf_counter(); p=daily_lp(n,m,start,end,initial,terminal,bids)
    if cache is None or cache['hours']!=end-start:
        h=make_solver(p,limit); cache=dict(hours=end-start,solver=h)
    else:
        h=cache['solver']; cols=np.arange(len(p['cost']),dtype=np.int32)
        rows=np.arange(len(p['row_lower']),dtype=np.int32)
        h.changeColsBounds(len(cols),cols,p['lower'],p['upper'])
        h.changeColsCost(len(cols),cols,p['cost'])
        h.changeRowsBounds(len(rows),rows,p['row_lower'],p['row_upper'])
    preparation=time.perf_counter()-begin; begin=time.perf_counter()
    h,attempts=clear_optimal(h,p,limit); cache['solver']=h
    seconds=time.perf_counter()-begin; sol=h.getSolution(); x=np.asarray(sol.col_value)
    error=residual(p,x); values=x.reshape(end-start,p['width']);nb=p['nb'];ns=p['ns']
    charge=values[:,nb:nb+ns]; discharge=values[:,nb+ns:nb+2*ns]
    soc=values[:,nb+2*ns:nb+3*ns]; spill=values[:,nb+3*ns:]
    previous=np.vstack([initial,soc[:-1]])
    water=float(abs(soc-previous*p['phi']-charge*p['eta_c']+discharge/p['eta_d']-p['inflow']+spill).max())
    cycles=int(np.count_nonzero((charge>1e-6)&(discharge>1e-6)))
    if error>TOL or water>TOL or cycles: raise ValueError('Daily physical replay/cycling failed')
    return dict(values=values,prices=np.asarray(sol.row_dual).reshape(end-start,p['rowwidth'])[:,:m['nz']],
                bid_objective_eur=float(p['cost']@x),operating_cost_eur=float(p['operating_cost']@x),
                maximum_primal_residual=error,maximum_water_residual=water,simultaneous_storage_hours=cycles,
                solver_seconds=seconds,preparation_seconds=preparation,solver_attempts=attempts),cache


def native_day(n,m,start,end,initial,bids):
    """Independent native formulation of full bids, with free closing inventory."""
    p=n.copy(snapshots=n.snapshots[start:end]);p.remove('GlobalConstraint',p.global_constraints.index)
    p.storage_units.cyclic_state_of_charge=False
    p.storage_units.state_of_charge_initial=pd.Series(initial,index=p.storage_units.index)
    # Zero-capacity source units have zero modes; avoid 0/0 in per-unit bounds.
    power=p.storage_units.p_nom.values
    p.storage_units_t.p_min_pu=pd.DataFrame(-np.divide(bids['charge_max'],power,
                                                    out=np.zeros_like(bids['charge_max']),where=power>0),
                                          index=p.snapshots,columns=p.storage_units.index)
    p.storage_units_t.p_max_pu=pd.DataFrame(np.divide(bids['discharge_max'],power,
                                                   out=np.zeros_like(bids['discharge_max']),where=power>0),
                                          index=p.snapshots,columns=p.storage_units.index)
    p.storage_units_t.marginal_cost=pd.DataFrame(bids['sell'],index=p.snapshots,columns=p.storage_units.index)
    for z in m['zones']: p.add('Bus','zone:'+z,carrier='AC',v_nom=380)
    p.generators.bus=p.generators.bus.map(m['buszone']).map(lambda z:'zone:'+z)
    p.storage_units.bus=p.storage_units.bus.map(m['buszone']).map(lambda z:'zone:'+z)
    p.generators_t.marginal_cost=pd.DataFrame(m['native_cost'][start:end],index=p.snapshots,columns=p.generators.index)
    p.remove('Load',p.loads.index)
    for j,z in enumerate(m['zones']):p.add('Load','load:'+z,bus='zone:'+z,p_set=pd.Series(m['load'][start:end,j],index=p.snapshots))
    distribution={}
    for z,weights in m['weights'].items():
        distribution[z]=[]
        for bus,w in weights.items():
            name='redistribute:'+z+':'+bus;distribution[z].append((name,w))
            p.add('Link',name,bus0='zone:'+z,bus1=bus,p_nom=1e6,p_min_pu=-1,efficiency=1)
    def extra(net,snapshots):
        v=net.model['Link-p']
        for z,ids in distribution.items():
            total=v.sel(name=[name for name,_ in ids]).sum('name')
            for name,w in ids:net.model.add_constraints(v.sel(name=name)==w*total,name='gsk:'+name)
        def labelled(a):return pd.Series(a,index=p.storage_units.index).rename_axis('name').to_xarray()
        closing=net.model['StorageUnit-state_of_charge'].sel(snapshot=snapshots[-1])
        net.model.add_constraints(closing>=labelled(bids['reachable_lower']),name='reachable-lower')
        net.model.add_constraints(closing<=labelled(bids['reachable_upper']),name='reachable-upper')
        willingness=pd.DataFrame(bids['buy'],index=snapshots,columns=p.storage_units.index).rename_axis(index='snapshot',columns='name').stack().to_xarray()
        purchases=net.model['StorageUnit-p_store']
        net.model.add_objective(net.model.objective.expression-(willingness*purchases).sum(),overwrite=True)
    status,condition=p.optimize(solver_name='highs',solver_options={'threads':1,'output_flag':False,'time_limit':120},extra_functionality=extra)
    if status!='ok' or condition!='optimal': raise ValueError('Native daily rule solve failed')
    return dict(bid_objective_eur=float(p.objective),prices=p.buses_t.marginal_price[['zone:'+z for z in m['zones']]].values)


def load_inputs(args):
    overrides=json.loads(Path(args.rules).read_text()) if args.rules else {}
    settings=configuration(overrides);assumptions,cost_source=cost_assumptions()
    market=json.loads(Path(args.fuel_prices).read_text()) if args.fuel_prices else None
    investments=json.loads(Path(args.investments).read_text()) if args.investments else []
    return settings,assumptions,cost_source,market,investments


def run(args):
    begin=time.perf_counter(); settings,assumptions,cost_source,market,investments=load_inputs(args)
    n,reference,domain,_,capacity_audit,_,_=setup()
    with np.load(REFERENCE/'annual-state.npz',allow_pickle=False) as a:initial=np.maximum(a['inventories_mwh'].reshape(60,160)[0],0)
    np.testing.assert_array_equal(n.storage_units.index.values,np.asarray(domain['storage_ids']))
    weather=pypsa.Network(SOURCE).get_switchable_as_dense('Generator','p_max_pu')
    names=['terminal_settlement_bids.py','simple_daily_market.py','simple_resource_bids.py','thermal_bid_rules.py','daily_market_clearing.py',
           'perfect_foresight_dispatch.py','european_physical_bids_2025.py','european_reservoir_clearing_2025.py',
           'synthetic_bids_2025.py','irena_linear_dispatch_capacity.py','derive_physical_zonal_constraints.py',
           'hourly_renewable_estimates.py','submonthly_inventory_driver.py']
    manifest=dict(producer_file='terminal_daily_market.py',terminal_mode_window_hours=48,producer=digest(__file__),source=digest(SOURCE),dependencies={name:digest(ROOT/'tools'/name) for name in names},
                  boundary_sha256=digest(REFERENCE/'annual-state.npz'),hours=args.hours,settings=settings,
                  cost_source=cost_source,thermal_assumptions=assumptions,capacity_audit=capacity_audit,
                  initial_inventory_mwh=initial.tolist(),investments=investments,
                  price_inputs_sha256=digest(args.fuel_prices) if args.fuel_prices else None,
                  price_sources=market['sources'] if market else 'Prepared cost-table constants, not observed fuel prices',
                  packages=dict(pypsa=pypsa.__version__,numpy=np.__version__,highs=highspy.Highs().version()),
                  scope='Daily arithmetic rules, hourly UTC approximation, physical N-0/GSK; not annual optimum or EUPHEMIA reconstruction')
    if market is not None:
        write_json(args.output/'fuel-inputs.json',market)
        manifest['saved_price_inputs_sha256']=digest(args.output/'fuel-inputs.json')
    write_json(args.output/'manifest.json',manifest)
    summaries=[]
    for label,changes in [('baseline',[])]+([('investment',investments)] if investments else []):
        folder=args.output/label;folder.mkdir()
        case,m,generators=compile_case(n,reference,changes,weather,settings,assumptions,market)
        current=np.r_[initial,np.zeros(len(case.storage_units)-len(initial))];terminal=current.copy()
        forecast,forecast_receipt=price_forecast(forecast_with_hydro(case,m,args.hours),args.hours,args.time_limit)
        prepared=prepare_storage(case,m,forecast,current,terminal,settings)
        path=folder/'preparation.npz';np.savez_compressed(path,**{k:v for k,v in prepared.items() if isinstance(v,np.ndarray)})
        write_json(folder/'preparation.json',dict(forecast=forecast_receipt,strategy_preparation_seconds=prepared['preparation_seconds'],
                                                  sha256=digest(path),generators=generators))
        print(label,'forecast',forecast_receipt['seconds'],'strategy preparation',prepared['preparation_seconds'],flush=True)
        records=[];cache=None
        for day,start in enumerate(range(0,args.hours,24)):
            end=start+24;bids=storage_bids(case,m,start,end,current,terminal,prepared,settings)
            result,cache=clear_day(case,m,start,end,current,terminal,bids,cache,args.time_limit)
            nb=m['A'].shape[1];ns=len(case.storage_units); final=result['values'][-1,nb+2*ns:nb+3*ns]
            cap=(case.storage_units.p_nom*case.storage_units.max_hours).values
            corrected=np.minimum(np.maximum(final,0),cap);correction=float(abs(final-corrected).max())
            if correction>1e-6:raise ValueError('Material inventory clipping')
            if args.native and day in {0,args.hours//48,args.hours//24-1}:
                check=native_day(case,m,start,end,current,bids);difference=check['bid_objective_eur']-result['bid_objective_eur']
                if abs(difference)>max(.05,abs(result['bid_objective_eur'])*1e-8):raise ValueError('Native bid objective mismatch')
                result['native_check']=dict(difference_eur=difference,price_maximum_difference_eur_mwh=float(abs(check['prices']-result['prices']).max()))
            path=folder/f'{day:03d}.npz'
            np.savez_compressed(path,values=result['values'],prices=result['prices'],initial=current,
                                **{k:v for k,v in bids.items() if isinstance(v,np.ndarray)})
            record={k:v for k,v in result.items() if not isinstance(v,np.ndarray)}
            record.update(day=day,start_hour=start,end_hour=end,bid_rules=bids['operators'],bid_rule_seconds=bids['seconds'],
                          witness_sha256=digest(path),maximum_boundary_roundoff_mwh=correction)
            write_json(folder/f'{day:03d}.json',record);records.append(record);current=corrected
            write_json(args.output/'status.json',dict(status='running',pid=os.getpid(),case=label,days_completed=day+1))
            print(label,'day',day+1,'solve',result['solver_seconds'],flush=True)
        closure=float(abs(current-terminal).max())
        if closure>TOL:raise ValueError('Horizon closure failed')
        summary=dict(case=label,hours=args.hours,zones=m['zones'],storage_ids=case.storage_units.index.tolist(),
                     operating_cost_eur=sum(r['operating_cost_eur'] for r in records),
                     bid_objective_eur=sum(r['bid_objective_eur'] for r in records),
                     forecast_seconds=forecast_receipt['seconds'],strategy_preparation_seconds=prepared['preparation_seconds'],
                     daily_rule_seconds=sum(r['bid_rule_seconds'] for r in records),
                     clearing_seconds=sum(r['solver_seconds'] for r in records),closure_residual_mwh=closure,
                     maximum_primal_residual=max(r['maximum_primal_residual'] for r in records),
                     maximum_water_residual=max(r['maximum_water_residual'] for r in records),
                     simultaneous_storage_hours=sum(r['simultaneous_storage_hours'] for r in records),
                     preparation_sha256=digest(folder/'preparation.npz'),
                     receipts_sha256={f'{r["day"]:03d}.json':digest(folder/f'{r["day"]:03d}.json') for r in records},
                     native_checks=[dict(day=r['day'],**r['native_check']) for r in records if 'native_check' in r])
        write_json(folder/'summary.json',summary);summaries.append(summary)
    write_json(args.output/'summary.json',dict(status='completed_rule_based_policy_not_annual_optimum',provenance=manifest,cases=summaries,
                                              elapsed_seconds=time.perf_counter()-begin,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                                              operating_cost_change_eur=summaries[1]['operating_cost_eur']-summaries[0]['operating_cost_eur'] if len(summaries)>1 else None))


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.WARNING)
    parser=argparse.ArgumentParser();parser.add_argument('--hours',type=int,default=48)
    parser.add_argument('--investments');parser.add_argument('--rules');parser.add_argument('--fuel-prices')
    parser.add_argument('--native',action='store_true');parser.add_argument('--time-limit',type=float,default=60)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.hours<24 or args.hours>8760 or args.hours%24 or not np.isfinite(args.time_limit) or args.time_limit<=0:
        parser.error('Whole UTC days and finite positive time limit required')
    resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3));signal.alarm(3600)
    args.output.mkdir(parents=True,exist_ok=True)
    with (args.output/'driver.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (args.output/'manifest.json').exists():parser.error('Fresh output root required')
        try:run(args)
        except Exception as exc:
            write_json(args.output/'status.json',dict(status='failed',error=str(exc)));raise
        write_json(args.output/'status.json',dict(status='completed',summary_sha256=digest(args.output/'summary.json')))
