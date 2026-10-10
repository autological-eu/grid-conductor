"""Fresh Europe-wide trial of the compact formulation with source/replay evidence."""
import argparse
import fcntl
import json
import logging
import os
from pathlib import Path
import resource
import signal
import time
import platform

import numpy as np
import pandas as pd
import pypsa
import scipy
import highspy

from compact_zonal_market import Window, transport_network, storage_data, replay, FRICTION, TOL
from european_reservoir_clearing_2025 import setup, REFERENCE
from simple_resource_bids import compile_case, configuration, cost_assumptions
from synthetic_bids_2025 import SOURCE
from hourly_renewable_estimates import digest
from daily_market_clearing import write_json

ROOT=Path(__file__).resolve().parents[1]


def load_case(fuel,hours):
    n,reference,domain,_,audit,_,_=setup()
    market=json.loads(Path(fuel).read_text())
    weather=pypsa.Network(SOURCE).get_switchable_as_dense('Generator','p_max_pu')
    assumptions,cost_source=cost_assumptions();settings=configuration()
    case,m,_=compile_case(n,reference,[],weather,settings,assumptions,market)
    with np.load(REFERENCE/'annual-state.npz',allow_pickle=False) as a:
        initial=np.maximum(a['inventories_mwh'].reshape(60,160)[0],0)
    np.testing.assert_array_equal(case.storage_units.index,np.asarray(domain['storage_ids']))
    return case,transport_network(case,m),storage_data(case,m,initial,hours),audit,cost_source


def native_window(n,m,s,start,current,H,result,penalty):
    """Separate native zonal Link/StorageUnit formulation of the same window."""
    begin=time.perf_counter()
    snapshots=n.snapshots[start:start+H];p=pypsa.Network();p.set_snapshots(snapshots)
    for j,z in enumerate(m['zones']):
        p.add('Bus',z)
        p.add('Load','load:'+z,bus=z,p_set=pd.Series(m['load'][start:start+H,j],index=snapshots))
    for j,z in enumerate(m['offer_zones']):
        p.add('Generator','offer:'+str(j),bus=z,p_nom=1.,
              p_max_pu=pd.Series(m['availability'][start:start+H,j],index=snapshots),
              marginal_cost=pd.Series(m['cost'][start:start+H,j],index=snapshots))
    for j,row in enumerate(m['links']):
        p.add('Link','flow:'+str(j),bus0=m['zones'][row['a']],bus1=m['zones'][row['b']],
              p_nom=1.,efficiency=row['efficiency'],
              p_min_pu=pd.Series(m['link_min'][start:start+H,j],index=snapshots),
              p_max_pu=pd.Series(m['link_max'][start:start+H,j],index=snapshots))
    for j,name in enumerate(s['ids']):
        power=max(s['charge'][j],s['discharge'][j],1.)
        p.add('StorageUnit',name,bus=m['zones'][s['area'][j]],p_nom=power,max_hours=s['cap'][j]/power,
              p_min_pu=-s['charge'][j]/power,p_max_pu=s['discharge'][j]/power,
              efficiency_store=s['eta_c'][j],efficiency_dispatch=s['eta_d'][j],standing_loss=1-s['phi'][j],
              state_of_charge_initial=current[j],cyclic_state_of_charge=False,
              marginal_cost=s['discharge_cost'][j],inflow=pd.Series(s['inflow'][start:start+H,j],index=snapshots))
    def extra(net,snapshots):
        stock=net.model['StorageUnit-state_of_charge']
        def labelled(a):return pd.Series(a,index=s['ids']).rename_axis('name').to_xarray()
        for k in sorted({min(24,H)-1,H-1}):
            end=stock.sel(snapshot=snapshots[k])
            net.model.add_constraints(end>=labelled(s['reachable_lower'][start+k+1]),name='closing-lower:'+str(k))
            net.model.add_constraints(end<=labelled(s['reachable_upper'][start+k+1]),name='closing-upper:'+str(k))
        hydro=[s['ids'][j] for j in s['hydro']]
        if hydro:
            deficit=net.model.add_variables(lower=0,coords=[pd.Index(hydro,name='name')],name='target-deficit')
            excess=net.model.add_variables(lower=0,coords=[pd.Index(hydro,name='name')],name='target-excess')
            target=pd.Series(s['target'][start+H,s['hydro']],index=hydro).rename_axis('name').to_xarray()
            net.model.add_constraints(stock.sel(snapshot=snapshots[-1],name=hydro)+deficit-excess==target,name='seasonal-target')
            net.model.add_objective(net.model.objective.expression+penalty*(deficit+excess).sum(),overwrite=True)
        net.model.add_objective(net.model.objective.expression+FRICTION*net.model['StorageUnit-p_store'].sum(),overwrite=True)
    status,condition=p.optimize(solver_name='highs',solver_options={'threads':1,'output_flag':False,'time_limit':120},extra_functionality=extra)
    if status!='ok' or condition!='optimal':raise ValueError('Native compact check failed')
    difference=float(p.objective-result['objective_eur'])
    if abs(difference)>max(.05,abs(result['objective_eur'])*1e-8):raise ValueError('Native compact objective mismatch')
    return dict(start_hour=start,hours=H,objective_difference_eur=difference,
                native_objective_eur=float(p.objective),seconds=time.perf_counter()-begin,
                maximum_price_difference_eur_mwh=float(np.abs(p.buses_t.marginal_price[m['zones']].values-result['prices']).max()))


def provenance(args,audit,cost_source):
    names=['compact_zonal_market.py','run_compact_zonal_2025.py','simple_resource_bids.py','thermal_bid_rules.py',
           'european_reservoir_clearing_2025.py','european_physical_bids_2025.py','perfect_foresight_dispatch.py',
           'daily_market_clearing.py','irena_linear_dispatch_capacity.py','synthetic_bids_2025.py',
           'derive_physical_zonal_constraints.py','hourly_renewable_estimates.py','submonthly_inventory_driver.py']
    return dict(source_sha256=digest(SOURCE),boundary_sha256=digest(REFERENCE/'annual-state.npz'),
                fuel_sha256=digest(args.fuel_prices),fuel_path=str(Path(args.fuel_prices).relative_to(ROOT)),
                dependencies={name:digest(ROOT/'tools'/name) for name in names},capacity_audit=audit,cost_source=cost_source,
                hours=args.hours,lookahead_hours=args.lookahead,seasonal_stock_penalty_eur_mwh=args.penalty,
                packages=dict(python=platform.python_version(),pypsa=pypsa.__version__,numpy=np.__version__,scipy=scipy.__version__,highs=highspy.Highs().version()),
                resource_guards=dict(address_space_gib=6,wall_seconds=1800,solver_window_seconds=args.time_limit,threads=1),
                scope='Experimental transport/rolling-storage simplification of daily model; not physical/commercial clearing, annual optimum or accepted scenario engine')


def run(args):
    begin=time.perf_counter();n,m,s,audit,cost_source=load_case(args.fuel_prices,args.hours)
    manifest=provenance(args,audit,cost_source);write_json(args.output/'manifest.json',manifest)
    write_json(args.output/'network.json',dict(zones=m['zones'],links=m['links'],storage_ids=s['ids']))
    prep=time.perf_counter()-begin;current=s['initial'].copy();windows={};records=[];native=[];parts=[];prices=[]
    for day,start in enumerate(range(0,args.hours,24)):
        H=min(24+args.lookahead,args.hours-start)
        if H not in windows:windows[H]=Window(m,s,H,args.penalty)
        w=windows[H];result,_=w.clear(start,current,args.time_limit)
        if args.native and day in {0,args.hours//48,args.hours//24-1}:
            native.append(native_window(n,m,s,start,current,H,result,args.penalty))
            np.savez_compressed(args.output/f'native-window-{day:03d}.npz',initial=current,values=result['values'],soft=result['soft'],prices=result['prices'])
        part=w.unpack(result['values'][:24]);parts.append(part);prices.append(result['prices'][:24])
        current=part['inventory'][-1].copy()
        if np.any((part['charge']>1e-6)&(part['discharge']>1e-6)):
            raise ValueError('Simultaneous storage directions')
        records.append(dict(day=day,start_hour=start,window_hours=H,status='optimal',
                            **{k:v for k,v in result.items() if not isinstance(v,np.ndarray)},
                            variables=w.A.shape[1],rows=w.A.shape[0],nonzeros=w.A.nnz))
        write_json(args.output/'status.json',dict(status='running',pid=os.getpid(),days_completed=day+1))
        if day%25==0 or day==args.hours//24-1:print('day',day+1,'window solve',result['solver_seconds'],flush=True)
    dispatch={key:np.concatenate([part[key] for part in parts]) for key in parts[0]}
    dispatch['prices']=np.concatenate(prices)
    checked=replay(m,s,dispatch)
    solve_elapsed=time.perf_counter()-begin
    np.savez_compressed(args.output/'annual.npz',**dispatch)
    germany=m['zones'].index('0:DE')
    observed=np.array([np.nan if v is None else v for v in json.loads((ROOT/'public/research/zone-prices-2025/DE-LU.json').read_text())])[:args.hours]
    valid=np.isfinite(observed);estimated=dispatch['prices'][:,germany];error=estimated[valid]-observed[valid]
    comparison=dict(pairs=int(valid.sum()),mae_eur_mwh=float(abs(error).mean()),rmse_eur_mwh=float(np.sqrt(np.mean(error**2))),
                    bias_eur_mwh=float(error.mean()),correlation=float(np.corrcoef(estimated[valid],observed[valid])[0,1]),
                    model_negative_hours=int(np.count_nonzero(estimated[valid]<-1e-6)),observed_negative_hours=int(np.count_nonzero(observed[valid]<0)),
                    observation_sha256=digest(ROOT/'public/research/zone-prices-2025/DE-LU.json'),scope='Untuned country proxy versus DE-LU, unclipped')
    areas=[]
    for j,z in enumerate(m['zones']):
        mask=(m['offer_zones']==z)&m['emergency_mask'];shortage=dispatch['generation'][:,mask].sum(axis=1)
        areas.append(dict(area=z,demand_twh=float(m['load'][:args.hours,j].sum()/1e6),
                          emergency_supply_twh=float(shortage.sum()/1e6),shortage_hours=int(np.count_nonzero(shortage>1e-6)),
                          mean_price_eur_mwh=float(dispatch['prices'][:,j].mean()),
                          hydro_generation_twh=float(dispatch['discharge'][:,s['hydro'][s['area'][s['hydro']]==j]].sum()/1e6)))
    summary=dict(status='completed_experimental_rolling_transport_policy',provenance=manifest,
                 days=len(records),hours=args.hours,areas=len(m['zones']),offers=len(m['offer_zones']),links=len(m['links']),storage_units=len(s['ids']),
                 input_preparation_seconds=prep,solver_seconds=sum(r['solver_seconds'] for r in records),
                 daily_vector_preparation_seconds=sum(r['preparation_seconds'] for r in records),
                 loop_and_preparation_seconds=solve_elapsed,native_checks=native,native_seconds=sum(r['seconds'] for r in native),
                 elapsed_seconds=time.perf_counter()-begin,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                 annual_witness_sha256=digest(args.output/'annual.npz'),records=records,physics=checked,germany=comparison,area_summary=areas)
    write_json(args.output/'summary.json',summary)
    print(json.dumps({k:summary[k] for k in ['hours','solver_seconds','elapsed_seconds','physics','germany']}),flush=True)


def audit(folder):
    summary=json.loads((folder/'summary.json').read_text());p=summary['provenance']
    for name,sha in p['dependencies'].items():
        if digest(ROOT/'tools'/name)!=sha:raise ValueError('Changed producer/dependency')
    fuel=ROOT/p['fuel_path']
    if (digest(SOURCE)!=p['source_sha256'] or digest(fuel)!=p['fuel_sha256']
        or digest(REFERENCE/'annual-state.npz')!=p['boundary_sha256']
        or digest(folder/'annual.npz')!=summary['annual_witness_sha256']):raise ValueError('Changed input/witness')
    _,m,s,_,_=load_case(fuel,p['hours'])
    with np.load(folder/'annual.npz',allow_pickle=False) as a:checked=replay(m,s,{k:a[k] for k in a.files})
    if checked!=summary['physics']:raise ValueError('Replay summary mismatch')
    receipt=dict(status='independent_component_equations_replayed',hours=p['hours'],physics=checked,
                 checker_sha256=digest(__file__),summary_sha256=digest(folder/'summary.json'),
                 scope='Saved implemented hours only; native checks are separate sampled windows; no annual optimality/empirical acceptance')
    write_json(folder/'replay.json',receipt);print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.WARNING)
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fuel-prices',default=str(ROOT/'data/daily-market-2025/monthly-fuel-annual-v2/fuel-inputs.json'))
    parser.add_argument('--hours',type=int,default=8760);parser.add_argument('--lookahead',type=int,default=24)
    parser.add_argument('--penalty',type=float,default=40.);parser.add_argument('--time-limit',type=float,default=60.)
    parser.add_argument('--native',action='store_true');parser.add_argument('--audit',action='store_true');args=parser.parse_args()
    if args.hours<24 or args.hours>8760 or args.hours%24 or args.lookahead<0 or args.lookahead%24 or args.lookahead>168 or not np.isfinite(args.penalty) or args.penalty<0 or not np.isfinite(args.time_limit) or args.time_limit<=0:
        parser.error('Invalid horizon/penalty/limit')
    resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3));signal.alarm(1800)
    if args.audit:audit(args.output)
    else:
        args.output.mkdir(parents=True,exist_ok=False)
        with (args.output/'driver.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            try:run(args)
            except Exception as exc:
                write_json(args.output/'status.json',dict(status='failed',pid=os.getpid(),error=str(exc)));raise
            write_json(args.output/'status.json',dict(status='completed',summary_sha256=digest(args.output/'summary.json')))
