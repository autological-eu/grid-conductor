"""Fast physical clearing with an audited, fixed hourly reservoir schedule.

No dispatch is used as generator availability. Reservoir output is an explicit
fixed injection; this conditional screening case cannot adapt hydro to investment.
"""
import csv,json,time,logging
from pathlib import Path
import numpy as np
import pandas as pd
import highspy
from european_physical_bids_2025 import ROOT,compile_model,solver,native_check
from european_reservoir_clearing_2025 import setup,FOLDER,REFERENCE,WORKSPACE
from hourly_renewable_estimates import digest
OUT=ROOT/'public/research/fixed-reservoir-screening-2025'
CACHE=ROOT/'data/fixed-reservoir-screening-2025'
ANNUAL=ROOT/'public/research/european-reservoir-clearing-2025'

def fixed_injections(power,hydro_zones,zones):
    power=np.asarray(power,dtype=float)
    if power.ndim!=2 or power.shape[1]!=len(hydro_zones) or not np.isfinite(power).all() or np.any(power < -1e-4):raise ValueError('Invalid precomputed hydro')
    result=np.zeros((len(power),len(zones)))
    for j,z in enumerate(hydro_zones):
        if z not in zones:raise ValueError('Unknown reservoir area')
        result[:,zones.index(z)]+=power[:,j]
    return result

def water_replay(power,inventory,spill,inflow,initial,capacity,turbine,eta,phi):
    if not all(np.isfinite(a).all() for a in [power,inventory,spill,inflow,initial]):raise ValueError('Nonfinite water witness')
    previous=np.vstack([initial,inventory[:-1]])
    residual=max(float(abs(inventory-previous*phi-inflow+power/eta+spill).max()),float(np.maximum(-power,0).max()),float(np.maximum(power-turbine,0).max()),float(np.maximum(-inventory,0).max()),float(np.maximum(inventory-capacity,0).max()),float(np.maximum(-spill,0).max()),float(np.maximum(spill-inflow,0).max()))
    if residual>1e-4:raise ValueError('Precomputed water feasibility failed')
    if abs(inventory[-1]-initial).max()>1e-4:raise ValueError('Annual water closure failed')
    return residual

def run():
    logging.getLogger('pypsa').setLevel(logging.ERROR);begin=time.perf_counter()
    n,_,domain,states,audit,original,_=setup();m=compile_model(n);demand=m['load'].copy()
    annual=json.loads((ANNUAL/'summary.json').read_text());replay=json.loads((ANNUAL/'replay.json').read_text());manifest=json.loads((FOLDER/'manifest.json').read_text())
    if replay['status']!='all_59_saved_primals_replayed' or replay['hours']!=8760 or replay['source_signature']!=manifest or annual['signature']!=manifest:raise ValueError('Annual source audit mismatch')
    expected={'source':ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/networks/base_s_128_elec_.nc','producer':ROOT/'tools/european_reservoir_clearing_2025.py','base':ROOT/'tools/european_physical_bids_2025.py','capacity':ROOT/'tools/irena_linear_dispatch_capacity.py','annual_state':REFERENCE/'annual-state.npz','workspace':WORKSPACE,'gsk':ROOT/'tools/derive_physical_zonal_constraints.py','cost':ROOT/'tools/synthetic_bids_2025.py'}
    if manifest!={k:digest(v) for k,v in expected.items()}:raise ValueError('Frozen source changed')
    data={k:[] for k in ['hydro_power','inventory','spill','prices']};witnesses=[];cursor=0
    for i,b in enumerate(domain['blocks']):
        if b['start_hour']!=cursor:raise ValueError('Broken calendar')
        cursor=b['end_hour_exclusive'];p=FOLDER/f'{i:02d}.npz';r=json.loads((FOLDER/f'{i:02d}.json').read_text())
        if digest(p)!=r['witness_sha256']:raise ValueError('Hydro witness changed')
        witnesses.append(r['witness_sha256'])
        with np.load(p,allow_pickle=False) as a:
            np.testing.assert_allclose(a['inventory'][-1],states[i+1],atol=1e-4,rtol=0)
            for k in data:data[k].append(a[k].copy())
    if cursor!=8760:raise ValueError('Incomplete year')
    data={k:np.concatenate(v) for k,v in data.items()};hydro=n.storage_units.query("carrier=='hydro'")
    if data['hydro_power'].shape!=(8760,len(hydro)):raise ValueError('Hydro shape mismatch')
    inflow=n.get_switchable_as_dense('StorageUnit','inflow').loc[:,hydro.index].values
    water=water_replay(data['hydro_power'],data['inventory'],data['spill'],inflow,states[0],(hydro.p_nom*hydro.max_hours).values,(hydro.p_nom*hydro.p_max_pu).values,hydro.efficiency_dispatch.values,1-hydro.standing_loss.values)
    hz=hydro.bus.map(m['buszone']).tolist();injections=fixed_injections(data['hydro_power'],hz,m['zones']);m['load']=demand-injections
    # Negative residual demand is a fixed injection, not a fabricated negative source load.
    fixed_cost=data['hydro_power']@hydro.marginal_cost.values;h=solver(m)
    h.setOptionValue('time_limit',30);h.setOptionValue('primal_feasibility_tolerance',1e-8)
    preparation=time.perf_counter()-begin;started=time.perf_counter();cols=np.arange(m['ng']+m['nl'],dtype=np.int32);gcols=np.arange(m['ng'],dtype=np.int32);zrows=np.arange(m['nz'],dtype=np.int32)
    prices=[];objectives=[];shortages=[];values=[];checks=[];retries=[];worst=0.
    for t in range(8760):
        lower=np.r_[np.zeros(m['ng']),m['link_min'][t]];upper=np.r_[m['availability'][t],m['link_max'][t]]
        h.changeColsBounds(len(cols),cols,lower,upper);h.changeColsCost(m['ng'],gcols,m['cost'][t]);h.changeRowsBounds(m['nz'],zrows,m['load'][t],m['load'][t]);h.run()
        if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:retries.append(t);h.clearSolver();h.run()
        if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:raise ValueError(f'Hour {t} failed: {h.getModelStatus()}')
        sol=h.getSolution();x=np.asarray(sol.col_value);ax=m['A']@x
        residual=max(float(abs(ax[:m['nz']]-m['load'][t]).max()),float(abs(ax[m['nz']:m['nz']+len(m['islands'])]).max()),float(np.maximum(abs(ax[m['nz']+len(m['islands']):])-m['ratings'],0).max()),float(np.maximum(lower-x[:len(cols)],0).max()),float(np.maximum(x[:len(cols)]-upper,0).max()))
        if residual>1e-4:raise ValueError('Hourly primal replay failed')
        worst=max(worst,residual);prices.append(sol.row_dual[:m['nz']]);objectives.append(h.getObjectiveValue()+fixed_cost[t]);shortages.append(x[original:m['ng']].sum());values.append(x)
        if t in [348,4692,8364]:checks.append((t,h.getObjectiveValue()))
    seconds=time.perf_counter()-started;native=[native_check(n,m,t,c) for t,c in checks];total=sum(objectives);difference=total-annual['total_operating_cost_eur']
    if abs(difference)>max(.1,abs(total)*1e-10):raise ValueError('Fixed-schedule annual objective mismatch: '+str(difference))
    prices=np.asarray(prices);values=np.asarray(values);CACHE.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
    np.savez_compressed(CACHE/'hourly.npz',prices=prices,values=values,hydro_injections=injections,objectives=objectives)
    de=m['zones'].index('0:DE');observed=np.array([np.nan if v is None else v for v in json.loads((ROOT/'public/research/zone-prices-2025/DE-LU.json').read_text())]);valid=np.isfinite(observed);error=prices[valid,de]-observed[valid];reference_error=prices[:,de]-data['prices'][:,de]
    pd.DataFrame({'utc':n.snapshots,'fixed_hydro_de_eur_mwh':prices[:,de],'chronological_de_eur_mwh':data['prices'][:,de],'observed_de_lu_eur_mwh':observed}).to_csv(OUT/'hourly-de.csv',index=False)
    gz=n.generators.bus.map(m['buszone']).values;emergency=n.generators.carrier.eq('emergency').values;areas=[]
    for j,z in enumerate(m['zones']):
        shortage=values[:,:m['ng']][:,(gz==z)&emergency].sum(axis=1)
        areas.append(dict(area=z,demand_twh=float(demand[:,j].sum()/1e6),fixed_hydro_twh=float(injections[:,j].sum()/1e6),emergency_supply_twh=float(shortage.sum()/1e6),shortage_hours=int(np.count_nonzero(shortage>1e-6)),mean_price_eur_mwh=float(prices[:,j].mean()),price_mae_vs_chronological_eur_mwh=float(abs(prices[:,j]-data['prices'][:,j]).mean())))
    pd.DataFrame(areas).to_csv(OUT/'area-summary.csv',index=False)
    summary=dict(status='annual_fixed_reservoir_schedule_screening_not_adaptive_hydro',hours=8760,preparation_and_water_audit_seconds=preparation,warm_solve_replay_seconds=seconds,chronological_solver_seconds=annual['solver_seconds'],solver_time_ratio=annual['solver_seconds']/seconds,maximum_network_residual_mw=worst,maximum_water_residual_mwh=water,annual_operating_cost_eur=total,objective_difference_vs_chronological_eur=difference,emergency_supply_twh=float(sum(shortages)/1e6),shortage_hours=int(np.count_nonzero(np.asarray(shortages)>1e-6)),native_checks=native,cold_retries=retries,germany=dict(mae_eur_mwh=float(abs(error).mean()),bias_eur_mwh=float(error.mean()),rmse_eur_mwh=float(np.sqrt((error**2).mean())),price_mae_vs_chronological_eur_mwh=float(abs(reference_error).mean()),maximum_price_difference_vs_chronological_eur_mwh=float(abs(reference_error).max())),area_summary=areas,provenance=dict(producer_sha256=digest(__file__),source_signature=manifest,water_replay_sha256=digest(ANNUAL/'replay.json'),annual_summary_sha256=digest(ANNUAL/'summary.json'),witness_sha256=witnesses,observed_prices_sha256=digest(ROOT/'public/research/zone-prices-2025/DE-LU.json')),limitations=['Fixed offline reservoir output: no hydro response to investments or changed inputs','Hourly marginal prices condition on fixed hydro; they need not equal water-coupled marginal prices','Same source GSK, IRENA wind/PV, original weather and demand; no market or annual optimum acceptance','Other 67 battery/PHS units excluded; reservoir water feasibility inherited and independently replayed','Offline schedule and preparation cost excluded from fast-loop timing'])
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n');print(json.dumps({k:summary[k] for k in ['warm_solve_replay_seconds','objective_difference_vs_chronological_eur','emergency_supply_twh','germany']}),flush=True)

if __name__=='__main__':
    import fcntl,resource
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));CACHE.mkdir(exist_ok=True)
    with (CACHE/'driver.lock').open('w') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run()
