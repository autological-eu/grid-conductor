"""Source-backed fixed hydro update; country pooling remains an explicit proxy.

No observed generation/price matching. Rebuild a feasible fixed schedule from HBV
inflow, observed boundary stocks and hourly physical-network envelopes. Frozen
source/reference files are never edited. This is not an annual market optimum.
"""
import argparse
import fcntl
import json
import logging
from pathlib import Path
import resource
import signal
import time
import highspy
import numpy as np
import pandas as pd
import pypsa
import xarray as xr
from scipy.sparse import coo_matrix, eye, hstack, vstack, diags
from hybrid_fixed_hydro_2025 import (load, compiled, resource_costs, verified_fuel, FUEL,
                                      clear, component_replay, HOURS, identity)
from simple_resource_bids import cost_assumptions
from european_physical_bids_2025 import compile_model, solver, native_check
from fixed_reservoir_screening_2025 import fixed_injections
from european_reservoir_clearing_2025 import FOLDER
from hourly_renewable_estimates import digest
from nve_hydro_inputs_2025 import compile_inputs, ROOT


def schedule(inflow, initial, terminal, capacity, lower, upper, target):
    """Electrical-equivalent energy balance, optimal L1 schedule adjustment."""
    T = len(inflow)
    I = eye(T, format='csc'); Z = I * 0
    delta = I - diags(np.ones(T-1), -1, shape=(T,T), format='csc')
    A = vstack([hstack([I, delta, I, Z]), hstack([I,Z,Z,-I]),
                hstack([-I,Z,Z,-I])], format='csc')
    rhs = inflow.copy(); rhs[0] += initial
    rowlo = np.r_[rhs, np.full(2*T, -np.inf)]
    rowhi = np.r_[rhs, target, -target]
    lo = np.r_[lower, np.zeros(3*T)]
    hi = np.r_[upper, np.full(T,capacity), inflow, np.full(T,np.inf)]
    lo[2*T-1] = hi[2*T-1] = terminal
    h = highspy.Highs()
    for key,value in [('threads',1),('output_flag',False),('time_limit',120),('solver','simplex')]:
        h.setOptionValue(key,value)
    lp = highspy.HighsLp(); lp.num_col_=4*T; lp.num_row_=3*T
    lp.col_cost_=np.r_[np.zeros(2*T),np.full(T,10.),np.ones(T)]
    lp.col_lower_=lo; lp.col_upper_=hi; lp.row_lower_=rowlo; lp.row_upper_=rowhi
    lp.a_matrix_.format_=highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_=A.indptr; lp.a_matrix_.index_=A.indices; lp.a_matrix_.value_=A.data
    h.passModel(lp); h.run()
    if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:
        raise ValueError('Updated water schedule infeasible/nonoptimal: '+str(h.getModelStatus()))
    x=np.asarray(h.getSolution().col_value); ax=A@x
    residual=max(float(np.maximum(lo-x,0).max()),float(np.maximum(x-hi,0).max()),
                 float(np.maximum(rowlo-ax,0).max()),float(np.maximum(ax-rowhi,0).max()))
    if residual>1e-4:raise ValueError('Schedule primal failed')
    return x[:T],x[T:2*T],x[2*T:3*T],dict(maximum_lp_residual_mwh=residual,
             l1_adjustment_objective_mwh=float(h.getObjectiveValue()),solver_seconds=h.getRunTime())


def delivery_bounds(m, area, turbine):
    """Feasible aggregate hydro interval under each hour's network and inputs."""
    h=solver(m); h.setOptionValue('primal_feasibility_tolerance',1e-9)
    j=m['zones'].index(area); old=m['A'].shape[1]
    h.changeColsCost(m['ng'],np.arange(m['ng'],dtype=np.int32),np.zeros(m['ng']))
    h.addCol(-1.,0.,turbine,1,np.array([j],dtype=np.int32),np.array([1.]))
    emergency=np.flatnonzero(m['emergency_mask']).astype(np.int32)
    emergency_row=m['A'].shape[0]
    h.addRow(0.,np.inf,len(emergency),emergency,np.ones(len(emergency)))
    gen=np.arange(m['ng'],dtype=np.int32)
    emergency_cost=m['emergency_mask'].astype(float)
    cols=np.arange(m['ng']+m['nl'],dtype=np.int32);rows=np.arange(m['nz'],dtype=np.int32)
    low=[];high=[];floors=[];begin=time.perf_counter()
    for t in range(8760):
        lo=np.r_[np.zeros(m['ng']),m['link_min'][t]];hi=np.r_[m['availability'][t],m['link_max'][t]]
        h.changeColsBounds(len(cols),cols,lo,hi);h.changeRowsBounds(len(rows),rows,m['load'][t],m['load'][t])
        # Reject hydro levels which create avoidable emergency production elsewhere.
        # This is an adequacy envelope, not price fitting or economic hydro dispatch.
        h.changeRowBounds(emergency_row,0.,np.inf)
        h.changeColsCost(len(gen),gen,emergency_cost);h.changeColCost(old,0.)
        h.setOptionValue('time_limit',h.getRunTime()+10.);h.run()
        if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:
            raise ValueError('Emergency-floor envelope failed at '+str(t))
        floor=max(0.,float(np.asarray(h.getSolution().col_value)[emergency].sum()))
        floors.append(floor)
        h.changeRowBounds(emergency_row,0.,floor+1e-3)
        h.changeColsCost(len(gen),gen,np.zeros(m['ng']))
        endpoints=[]
        for direction in [1.,-1.]:
            h.changeColCost(old,direction);h.setOptionValue('time_limit',h.getRunTime()+10.);h.run()
            if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:
                raise ValueError('Network envelope failed at '+str(t))
            x=np.asarray(h.getSolution().col_value);ax=m['A']@x[:old];ax[j]+=x[old]
            residual=max(float(abs(ax[:m['nz']]-m['load'][t]).max()),
                float(abs(ax[m['nz']:m['nz']+len(m['islands'])]).max()),
                float(np.maximum(abs(ax[m['nz']+len(m['islands']):])-m['ratings'],0).max()),
                float(np.maximum(lo-x[:len(cols)],0).max()),float(np.maximum(x[:len(cols)]-hi,0).max()))
            residual=max(residual,max(0.,float(x[emergency].sum())-floor-1e-3))
            if residual>1e-4:raise ValueError('Envelope live replay failed')
            endpoints.append(float(x[old]))
        left=max(0.,endpoints[0]);right=min(turbine,endpoints[1])
        if left>right+1e-7:raise ValueError('Reversed hydro envelope')
        # Keep fixed injections inside the envelope rather than at rounded vertices.
        margin=min(1e-4,max(0.,right-left)/4)
        low.append(left+margin);high.append(right-margin)
        if t%2000==0:print('delivery-envelope',t,flush=True)
    return np.array(low),np.array(high),time.perf_counter()-begin,float(sum(floors)/1e6)


def native_water(n,ids,power,state,inflow,initial,capacity,eta):
    """Native PyPSA replays a fixed 48-hour schedule and its energy basis."""
    T=48; p=pypsa.Network();p.set_snapshots(n.snapshots[:T]);p.add('Bus','hydro',carrier='AC')
    for j,name in enumerate(ids):
        s=n.storage_units.loc[name]
        p.add('StorageUnit',name,bus='hydro',carrier='hydro',p_nom=s.p_nom,
              p_min_pu=0.,
              p_max_pu=pd.Series(power[:T,j]/s.p_nom,index=p.snapshots),
              max_hours=capacity[j]/s.p_nom,efficiency_dispatch=eta[j],efficiency_store=0.,
              cyclic_state_of_charge=False,state_of_charge_initial=initial[j],
              inflow=pd.Series(inflow[:T,j],index=p.snapshots),marginal_cost=1.)
    p.add('Load','fixed-production',bus='hydro',p_set=pd.Series(power[:T].sum(axis=1),index=p.snapshots))
    def extra(net,snapshots):
        for variable,values in [('StorageUnit-state_of_charge',state[:T]),('StorageUnit-p_dispatch',power[:T])]:
            net.model.add_constraints(net.model[variable]==pd.DataFrame(values,index=p.snapshots,columns=ids).rename_axis(index='snapshot',columns='name').to_xarray().to_array('name').transpose('snapshot','name'),name='fixed-replay-'+variable)
    status,condition=p.optimize(solver_name='highs',solver_options={'threads':1,'output_flag':False,'time_limit':60},extra_functionality=extra)
    if (status,condition)!=('ok','optimal'):raise ValueError('Native water replay failed')
    error=float(abs(p.storage_units_t.state_of_charge.loc[:,ids].values-state[:T]).max())
    if error>1e-4:raise ValueError('Native stock mismatch')
    return dict(hours=T,status=condition,maximum_stock_difference_mwh=error)


def run(out):
    logging.getLogger('pypsa').setLevel(logging.ERROR);started=time.perf_counter()
    n,oldbase,common=load();su=n.storage_units.query("carrier=='hydro'");mask=(su.bus.map(n.buses.country)=='NO').values
    ids=su.index[mask];s=su.loc[ids];eta=s.efficiency_dispatch.values
    if np.ptp(eta)>1e-12 or not np.all(s.standing_loss==0) or len({oldbase['buszone'][b] for b in s.bus})!=1:
        raise ValueError('Unsupported Norwegian pooled-reservoir representation')
    area=oldbase['buszone'][s.bus.iloc[0]];shares=s.p_nom.values/s.p_nom.sum()
    weatherpath=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/profile_hydro.nc'
    with xr.open_dataarray(weatherpath) as weather:
        np.testing.assert_array_equal(weather.time.values,n.snapshots.values)
        inflow,target_stock,cap,source=compile_inputs(weather.sel(countries='NO').values)
    source['weather_shape_sha256']=digest(weatherpath)
    ror=n.generators.index[(n.generators.carrier=='ror') & (n.generators.bus.map(n.buses.country)=='NO')]
    reservoir_share=float(s.p_nom.sum()/(s.p_nom.sum()+n.generators.loc[ror].p_nom.sum()))
    ror_profile=inflow[:,None]*(1-reservoir_share)/n.generators.loc[ror].p_nom.sum()
    n.generators_t.p_max_pu.loc[:,ror]=np.minimum(np.repeat(ror_profile,len(ror),axis=1),1.)
    cost=resource_costs(n,oldbase['cost'],verified_fuel(FUEL),cost_assumptions()[0],'resource_bids')
    base=compile_model(n)
    oldpower=np.concatenate([np.load(FOLDER/f'{i:02d}.npz',allow_pickle=False)['hydro_power'] for i in range(59)])
    oldinjections=fixed_injections(oldpower,su.bus.map(base['buszone']).tolist(),base['zones'])
    base['load']=common['source_load']-oldinjections
    base['load'][:,base['zones'].index(area)]+=oldpower[:,mask].sum(axis=1)
    bounds_model=compiled(n,base.copy(),cost)
    lower,upper,envelope_seconds,emergency_floor=delivery_bounds(bounds_model,area,float(s.p_nom.sum()))
    natural=inflow*reservoir_share;initial=float(target_stock[0]);terminal=float(target_stock[-1])
    budget=natural.sum()+initial-terminal
    reference=oldpower[:,mask].sum(axis=1)
    target=reference*budget/reference.sum()
    hydro,state,spill,plan=schedule(natural,initial,terminal,cap,lower,upper,target)
    power=hydro[:,None]*shares;waterstate=state[:,None]*shares/eta
    storedinflow=natural[:,None]*shares/eta;storedspill=spill[:,None]*shares/eta
    initial_units=initial*shares/eta;capacity=cap*shares/eta
    n.storage_units.loc[ids,'max_hours']=capacity/s.p_nom.values
    previous=np.vstack([initial_units,waterstate[:-1]])
    residual=float(abs(waterstate-previous-storedinflow+power/eta+storedspill).max())
    worst=max(residual,float(np.maximum(-waterstate,0).max()),float(np.maximum(waterstate-capacity,0).max()),
              float(np.maximum(-power,0).max()),float(np.maximum(power-s.p_nom.values,0).max()))
    if worst>1e-4 or abs(state[-1]-terminal)>1e-4:raise ValueError('Updated annual water replay failed')
    watercheck=native_water(n,ids,power,waterstate,storedinflow,initial_units,capacity,eta)
    allpower=oldpower.copy();allpower[:,mask]=power
    base['load']=common['source_load']-fixed_injections(allpower,su.bus.map(base['buszone']).tolist(),base['zones'])
    m=compiled(n,base,cost)
    np.savez_compressed(out/'water.npz',power=power,inventory=waterstate,spill=storedspill,inflow=storedinflow,
                        initial=initial_units,terminal=terminal*shares/eta,capacity=capacity,eta=eta,
                        network_lower=lower,network_upper=upper)
    prep=time.perf_counter()-started
    result=clear(m,out/'resource_bids.npz',10.)
    with np.load(out/'resource_bids.npz',allow_pickle=False) as values:
        result['physics']=component_replay(n,m,values['values'])
        result['native_checks']=[native_check(n,m|dict(cost=m['native_cost']),t,float(values['objectives'][t])) for t in HOURS]
        prices=values['prices'][:,m['zones'].index(area)]
        # Report ROR allocation bounds when renewable offers are merged.
        groups={}
        for j,z in enumerate(n.generators.bus.map(base['buszone'])):
            groups.setdefault((z,cost[:,j].tobytes(),n.generators.iloc[j].carrier=='emergency'),[]).append(j)
        loenergy=hienergy=0.
        for j,((z,_,_),js) in enumerate(groups.items()):
            if z!=area:continue
            rids=[k for k in js if n.generators.index[k] in ror];oids=[k for k in js if k not in rids]
            if not rids:continue
            available=base['availability'][:,rids].sum(axis=1)
            other=base['availability'][:,oids].sum(axis=1) if oids else 0.
            loenergy+=np.maximum(values['values'][:,j]-other,0).sum()/1e6
            hienergy+=np.minimum(values['values'][:,j],available).sum()/1e6
    result.update(hydro_source=source,reservoir_share=reservoir_share,water_plan=plan,water_native=watercheck,
        water_residual_mwh=worst,fixed_reservoir_twh=float(hydro.sum()/1e6),
        spill_electrical_twh=float(spill.sum()/1e6),total_hydro_bounds_twh=[float(hydro.sum()/1e6)+loenergy,float(hydro.sum()/1e6)+hienergy],
        no_hours_above_1000=int((prices>1000).sum()),no_mean_price=float(prices.mean()),
        offline_schedule_and_bounds_seconds=prep,delivery_bounds_seconds=envelope_seconds,minimum_emergency_envelope_twh=emergency_floor,envelope_emergency_allowance_mw=1e-3,envelope_inner_margin_mw=1e-4,end_to_end_seconds=time.perf_counter()-started,
        dependencies=identity(FUEL),new_sources={p.name:digest(p) for p in [Path(__file__),ROOT/'tools/nve_hydro_inputs_2025.py']},
        water_witness_sha256=digest(out/'water.npz'),status='source_updated_fixed_hydro_country_proxy_not_market_acceptance',
        limitations=['No commercial-zone mapping or hydro investment response.',
                     'Norwegian reservoir energy capacity and boundary stocks are country-pooled NVE proxies; turbines remain original fleet.',
                     'Offline schedule minimises deviation from the retained pattern subject to new inputs and network bounds; not annual economic optimisation.',
                     'NVE gross-stock/net-inflow electrical-equivalent basis and hourly/weekly allocation remain declared assumptions.',
                     'Demand, other-country hydro, wind/solar, bid rules and original physical/GSK constraints are unchanged.'])
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['fixed_reservoir_twh','total_hydro_bounds_twh','no_hours_above_1000','physics','offline_schedule_and_bounds_seconds','end_to_end_seconds']},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'data/hydro-observations-2025/nve-updated-model-v1')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    if (args.out/'summary.json').exists():raise ValueError('Use a fresh output root')
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(900)
    with (args.out/'driver.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(args.out)
