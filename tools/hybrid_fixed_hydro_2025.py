"""Fixed-hydro physical hourly clearing with simple resource/fuel offers.

Fresh controlled bid ablations; frozen hydro/reference producers are untouched.
No electricity-price inputs, forecast stage, adaptive hydro or battery/PHS dispatch.
"""
import argparse
import fcntl
import json
import logging
import os
from pathlib import Path
import platform
import resource
import signal
import time
import numpy as np
import pandas as pd
import pypsa
import highspy
from european_reservoir_clearing_2025 import setup, FOLDER, REFERENCE, WORKSPACE, aggregate_offers
from european_physical_bids_2025 import compile_model, solver, native_check
from fixed_reservoir_screening_2025 import water_replay, fixed_injections, OUT as REFERENCE_PUBLIC
from simple_resource_bids import cost_assumptions, RENEWABLES, THERMAL, OTHER
from thermal_bid_rules import validate_market
from prepare_fuel_prices import compile_prices
from synthetic_bids_2025 import SOURCE
from hourly_renewable_estimates import digest
from daily_market_clearing import write_json
ROOT=Path(__file__).resolve().parents[1]
FUEL=ROOT/'data/daily-market-2025/monthly-fuel-annual-v2/fuel-inputs.json'
VARIANTS=('legacy','fuel_only','resource_bids')
HOURS=(348,4692,8364)
TOL=1e-4


def resource_costs(n,legacy,market,assumptions,variant):
    """Vectorised audited thermal rule, replacing rather than adding total cost."""
    if variant not in VARIANTS:raise ValueError('Unknown bid variant')
    if variant=='legacy':return legacy.copy()
    rows=validate_market(market,n.snapshots)
    gas=np.array([r['gas_eur_mwh_th'] for r in rows]);oil=np.array([r['oil_eur_mwh_th'] for r in rows])
    carbon=np.array([r['co2_eur_t'] for r in rows])
    cost=legacy.copy() if variant=='fuel_only' else n.get_switchable_as_dense('Generator','marginal_cost').to_numpy().copy()
    for j,(_,g) in enumerate(n.generators.iterrows()):
        carrier=g.carrier
        if carrier not in RENEWABLES|THERMAL|OTHER:raise ValueError('Unsupported carrier '+str(carrier))
        replace=carrier in ('CCGT','OCGT','oil') if variant=='fuel_only' else carrier in THERMAL
        if replace:
            if not np.isfinite(g.efficiency) or not 0<g.efficiency<=1:raise ValueError('Invalid turbine efficiency')
            a=assumptions[carrier];fuel=gas if carrier in ('CCGT','OCGT') else oil if carrier=='oil' else a['fuel_eur_mwh_th']
            cost[:,j]=(fuel+carbon*a['emissions_t_mwh_th'])/g.efficiency+a['variable_om_eur_mwh_el']
        elif variant=='resource_bids' and carrier in RENEWABLES:cost[:,j]=0.
    if not np.isfinite(cost).all():raise ValueError('Nonfinite offers')
    return cost


def load():
    start=time.perf_counter();n,_,domain,states,capacity_audit,_,_=setup();m=compile_model(n)
    retained=json.loads((REFERENCE_PUBLIC/'summary.json').read_text());provenance=retained['provenance']
    expected={'source':SOURCE,'producer':ROOT/'tools/european_reservoir_clearing_2025.py',
        'base':ROOT/'tools/european_physical_bids_2025.py','capacity':ROOT/'tools/irena_linear_dispatch_capacity.py',
        'annual_state':REFERENCE/'annual-state.npz','workspace':WORKSPACE,
        'gsk':ROOT/'tools/derive_physical_zonal_constraints.py','cost':ROOT/'tools/synthetic_bids_2025.py'}
    if provenance['source_signature']!={k:digest(v) for k,v in expected.items()}:raise ValueError('Frozen reference source changed')
    if provenance['producer_sha256']!=digest(ROOT/'tools/fixed_reservoir_screening_2025.py'):raise ValueError('Frozen producer changed')
    hydro={k:[] for k in ('hydro_power','inventory','spill')};cursor=0
    for i,b in enumerate(domain['blocks']):
        if b['start_hour']!=cursor:raise ValueError('Broken hydro calendar')
        cursor=b['end_hour_exclusive'];file=FOLDER/f'{i:02d}.npz'
        if digest(file)!=provenance['witness_sha256'][i]:raise ValueError('Changed hydro witness')
        with np.load(file,allow_pickle=False) as a:
            np.testing.assert_allclose(a['inventory'][-1],states[i+1],rtol=0,atol=TOL)
            for k in hydro:hydro[k].append(a[k].copy())
    if cursor!=8760:raise ValueError('Incomplete hydro calendar')
    hydro={k:np.concatenate(v) for k,v in hydro.items()};su=n.storage_units.query("carrier=='hydro'")
    water=water_replay(hydro['hydro_power'],hydro['inventory'],hydro['spill'],n.get_switchable_as_dense('StorageUnit','inflow').loc[:,su.index].to_numpy(),states[0],(su.p_nom*su.max_hours).to_numpy(),(su.p_nom*su.p_max_pu).to_numpy(),su.efficiency_dispatch.to_numpy(),1-su.standing_loss.to_numpy())
    injections=fixed_injections(hydro['hydro_power'],su.bus.map(m['buszone']).tolist(),m['zones'])
    source_load=m['load'].copy();m['load']=source_load-injections
    return n,m,dict(capacity_audit=capacity_audit,water_residual_mwh=water,
        hydro_injections_sha256=__import__('hashlib').sha256(injections.tobytes()).hexdigest(),
        reference_summary_sha256=digest(REFERENCE_PUBLIC/'summary.json'),
        fixed_cost=hydro['hydro_power']@su.marginal_cost.to_numpy(),source_load=source_load,
        preparation_seconds=time.perf_counter()-start)


def verified_fuel(path):
    market=json.loads(Path(path).read_text());a=market['assumptions']
    wb=ROOT/'data/fuel-prices/world-bank-monthly-2026.xlsx';ecb=ROOT/'data/fuel-prices/ecb-2025-api.csv'
    if [digest(wb),digest(ecb)]!=[r['sha256'] for r in market['provenance']]:raise ValueError('Changed raw fuel/FX source')
    rebuilt=compile_prices(wb,ecb,2025,a['gas_basis_multiplier'],a['oil_mwh_th_per_barrel'],a['co2_eur_t'])
    if rebuilt!=market:raise ValueError('Fuel compiler/raw reconstruction mismatch')
    return market


def compiled(n,m,cost):
    case=m.copy();case['cost']=cost
    return aggregate_offers(n,case)


def component_replay(n,m,values):
    """Reconstruct zonal balances and passive flows from components, not LP A."""
    if values.shape!=(8760,m['A'].shape[1]) or not np.isfinite(values).all():raise ValueError('Invalid annual primal')
    ng,nl=m['ng'],m['nl'];g=values[:,:ng];f=values[:,ng:ng+nl];q=values[:,ng+nl:]
    supply=np.zeros_like(m['load'])
    for j,z in enumerate(m['offer_zones']):supply[:,m['zones'].index(z)]+=g[:,j]
    worst=float(abs(supply-m['load']-q).max())
    for value,low,high in [(g,0,m['availability']),(f,m['link_min'],m['link_max'])]:
        worst=max(worst,float(np.maximum(low-value,0).max()),float(np.maximum(value-high,0).max()))
    injection=pd.DataFrame(0.,index=n.snapshots,columns=n.buses.index)
    for z,weights in m['weights'].items():
        for bus,w in weights.items():injection[bus]+=q[:,m['zones'].index(z)]*w
    for j,(_,link) in enumerate(n.links.iterrows()):
        injection[link.bus0]-=f[:,j];injection[link.bus1]+=link.efficiency*f[:,j]
    branch_error=0.;island_error=0.
    for _,row in n.sub_networks.iterrows():
        sn=row.obj;island_error=max(island_error,float(abs(injection.loc[:,sn.buses_i()].sum(axis=1)).max()))
        if len(sn.buses_i())<2:continue
        sn.calculate_PTDF();flows=injection.loc[:,sn.buses_o].to_numpy()@np.asarray(sn.PTDF).T
        limits=np.array([float(n.df(c).loc[name].s_nom*n.df(c).loc[name].s_max_pu) for c,name in sn.branches_i()])
        branch_error=max(branch_error,float(np.maximum(abs(flows)-limits,0).max()))
    worst=max(worst,branch_error,island_error)
    if worst>TOL:raise ValueError('Component replay failed '+str(worst))
    short=g[:,m['emergency_mask']]
    return dict(maximum_residual_mw=worst,passive_limit_excess_mw=branch_error,island_balance_residual_mw=island_error,
        emergency_supply_twh=float(short.sum()/1e6),shortage_hours=int(np.count_nonzero(short.sum(axis=1)>1e-6)))


def clear(m,output,limit):
    h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
    cols=np.arange(m['ng']+m['nl'],dtype=np.int32);gen=np.arange(m['ng'],dtype=np.int32);rows=np.arange(m['nz'],dtype=np.int32)
    prices=[];values=[];objectives=[];statuses=[];retry=[];solve=0.;vectors=0.;start=time.perf_counter()
    for t in range(8760):
        begin=time.perf_counter();lo=np.r_[np.zeros(m['ng']),m['link_min'][t]];hi=np.r_[m['availability'][t],m['link_max'][t]]
        h.changeColsBounds(len(cols),cols,lo,hi);h.changeColsCost(len(gen),gen,m['cost'][t]);h.changeRowsBounds(len(rows),rows,m['load'][t],m['load'][t]);vectors+=time.perf_counter()-begin
        begin=time.perf_counter();h.setOptionValue('time_limit',h.getRunTime()+limit);h.run()
        if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:
            retry.append(dict(hour=t,warm_status=str(h.getModelStatus())));h.clearSolver();h.setOptionValue('time_limit',h.getRunTime()+limit);h.run()
        solve+=time.perf_counter()-begin
        if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:raise ValueError('Nonoptimal hour '+str(t))
        sol=h.getSolution();x=np.asarray(sol.col_value);ax=m['A']@x
        error=max(float(abs(ax[:m['nz']]-m['load'][t]).max()),float(abs(ax[m['nz']:m['nz']+len(m['islands'])]).max()),float(np.maximum(abs(ax[m['nz']+len(m['islands']):])-m['ratings'],0).max()),float(np.maximum(lo-x[:len(cols)],0).max()),float(np.maximum(x[:len(cols)]-hi,0).max()))
        if error>TOL:raise ValueError('Live LP residual failed')
        values.append(x);prices.append(np.asarray(sol.row_dual[:m['nz']]));objectives.append(h.getObjectiveValue());statuses.append(error)
        if t%2000==0:print(output.name,t,flush=True)
    loop=time.perf_counter()-start
    begin=time.perf_counter();np.savez_compressed(output,values=np.asarray(values),prices=np.asarray(prices),objectives=np.asarray(objectives))
    return dict(solver_seconds=solve,vector_update_seconds=vectors,loop_with_live_replay_seconds=loop,
        witness_export_seconds=time.perf_counter()-begin,optimal_hours=8760,maximum_live_residual_mw=max(statuses),cold_retries=retry,
        witness_sha256=digest(output),generation_offers=m['ng'],variables=m['A'].shape[1],constraints=m['A'].shape[0],nonzeros=m['A'].nnz)


def identity(path):
    names=['hybrid_fixed_hydro_2025.py','fixed_reservoir_screening_2025.py','european_reservoir_clearing_2025.py','european_physical_bids_2025.py',
        'simple_resource_bids.py','thermal_bid_rules.py','prepare_fuel_prices.py','irena_linear_dispatch_capacity.py','synthetic_bids_2025.py',
        'derive_physical_zonal_constraints.py','hourly_renewable_estimates.py','submonthly_inventory_driver.py','daily_market_clearing.py']
    return dict(dependencies={name:digest(ROOT/'tools'/name) for name in names},fuel_path=str(Path(path).relative_to(ROOT)),fuel_sha256=digest(path),
        source_sha256=digest(SOURCE),resource_guards=dict(memory_gib=5,wall_seconds=900,threads=1,hour_limit_seconds=10),
        packages=dict(python=platform.python_version(),pypsa=pypsa.__version__,highs=highspy.Highs().version(),numpy=np.__version__),
        evaluation='Untuned descriptive comparison; no price fitting, empirical acceptance or investment integration',
        input_blockers=['Audited ENTSO-E zonal demand and generator/bus-to-commercial-zone mapping unavailable',
            'Nuclear availability ending in 2024 is a declared proxy; outages/commitment unverified',
            'Prepared coal/lignite fuel constants, fixed EUR80/t carbon and crude oil/heating-value proxies remain'])


def run(args):
    begin=time.perf_counter();n,base,common=load();market=verified_fuel(args.fuel);assumptions,cost_source=cost_assumptions()
    p=identity(args.fuel);p.update(reference_summary_sha256=common['reference_summary_sha256'],hydro_injections_sha256=common['hydro_injections_sha256'],
        capacity_audit=common['capacity_audit'],fuel_sources=market['sources'],fuel_assumptions=market['assumptions'],cost_source=cost_source,
        predeclared_variants=list(VARIANTS),native_hours=list(HOURS),validation_calendar='2025-01-01T00:00Z to 2026-01-01T00:00Z')
    write_json(args.output/'manifest.json',p);results={}
    for variant in VARIANTS:
        bid_start=time.perf_counter();costs=resource_costs(n,base['cost'],market,assumptions,variant);m=compiled(n,base,costs)
        bid_seconds=time.perf_counter()-bid_start
        path=args.output/(variant+'.npz');r=clear(m,path,10.);r['bid_compilation_seconds']=bid_seconds
        checks=[];start=time.perf_counter()
        with np.load(path,allow_pickle=False) as a:
            r['physics']=component_replay(n,m,a['values']);r['annual_variable_cost_eur']=float(a['objectives'].sum()+common['fixed_cost'].sum())
            native_m=m|dict(cost=m['native_cost'])
            for hour in HOURS:checks.append(native_check(n,native_m,hour,float(a['objectives'][hour])))
        r['component_replay_and_native_seconds']=time.perf_counter()-start;r['native_checks']=checks
        write_json(args.output/(variant+'-summary.json'),r);results[variant]=r
    with np.load(ROOT/'data/fixed-reservoir-screening-2025/hourly.npz',allow_pickle=False) as old,np.load(args.output/'legacy.npz',allow_pickle=False) as fresh:
        gap=float(abs(old['objectives']-fresh['objectives']-common['fixed_cost']).max())
        pricegap=float(abs(old['prices']-fresh['prices']).max())
        if gap>.05:raise ValueError('Controlled legacy no longer reproduces retained objectives')
    summary=dict(status='completed_fixed_hydro_resource_bid_comparison',hours=8760,areas=base['nz'],passive_branches=len(base['ratings']),controllable_links=base['nl'],
        zones=base['zones'],provenance=p,common_preparation_seconds=common['preparation_seconds'],water_residual_mwh=common['water_residual_mwh'],
        retained_legacy_maximum_objective_difference_eur=gap,retained_legacy_maximum_dual_difference_eur_mwh=pricegap,
        cases=results,elapsed_seconds=time.perf_counter()-begin,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
    write_json(args.output/'summary.json',summary);print(json.dumps({k:summary[k] for k in ['elapsed_seconds','peak_rss_mib','retained_legacy_maximum_objective_difference_eur']}),flush=True)


def audit(args):
    summary=json.loads((args.output/'summary.json').read_text());p=summary['provenance']
    for name,sha in p['dependencies'].items():
        if digest(ROOT/'tools'/name)!=sha:raise ValueError('Changed calculation source')
    if digest(ROOT/p['fuel_path'])!=p['fuel_sha256'] or digest(SOURCE)!=p['source_sha256']:raise ValueError('Changed source input')
    n,base,common=load();market=verified_fuel(ROOT/p['fuel_path']);assumptions,_=cost_assumptions();results={}
    for variant in VARIANTS:
        path=args.output/(variant+'.npz');r=summary['cases'][variant]
        if digest(path)!=r['witness_sha256']:raise ValueError('Changed primal witness')
        m=compiled(n,base,resource_costs(n,base['cost'],market,assumptions,variant))
        with np.load(path,allow_pickle=False) as a:results[variant]=component_replay(n,m,a['values'])
        if results[variant]!=r['physics']:raise ValueError('Independent replay changed')
    write_json(args.output/'replay.json',dict(status='all_three_8760_hour_component_replays_passed',summary_sha256=digest(args.output/'summary.json'),cases=results,water_residual_mwh=common['water_residual_mwh']))
    print('Independent source, fuel, water, area, island, passive-flow and bound replay passed',flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--fuel',type=Path,default=FUEL);p.add_argument('--audit',action='store_true');args=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(900)
    if args.audit:audit(args)
    else:
        args.output.mkdir(parents=True,exist_ok=False)
        with (args.output/'driver.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            try:run(args)
            except Exception as exc:write_json(args.output/'status.json',dict(status='failed',error=str(exc),pid=os.getpid()));raise
            write_json(args.output/'status.json',dict(status='completed',summary_sha256=digest(args.output/'summary.json')))
