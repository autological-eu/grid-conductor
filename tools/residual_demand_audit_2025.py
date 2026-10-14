"""Europe-wide availability/demand diagnostic, never a dispatch or price fit."""
import argparse,fcntl,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
from bidding_zone_network_2025 import ROOT,build
from nve_hydro_diagnostics import digest
from audit_2025_generation_observations import audit as generation_audit
from run_bidding_zone_network_2025 import observed
from compare_native_exchange_reference import CODES

BASE=ROOT/'data/bidding-zone-network-2025/annual-v7'
FAMILIES={'wind':{'onwind','offwind-ac','offwind-dc','offwind-float'},
          'solar':{'solar','solar-hsat'},'nuclear':{'nuclear'},'ror':{'ror'},
          'biomass':{'biomass'},'thermal':{'CCGT','OCGT','coal','lignite','oil'}}
TYPES={'wind':{'B18','B19'},'solar':{'B16'},'nuclear':{'B14'},'ror':{'B11'},'biomass':{'B01'}}

def array_stats(available,generated):
    good=np.isfinite(generated);a=available[good];g=generated[good]
    if not len(a):return dict(known_hours=0,status='unavailable_not_zero')
    excess=np.maximum(g-a,0)
    return dict(known_hours=int(good.sum()),available_on_known_hours_twh=float(a.sum()/1e6),
        generated_on_known_hours_twh=float(g.sum()/1e6),hours_generated_above_available_1mw=int((excess>1).sum()),
        excess_generation_twh=float(excess.sum()/1e6),
        shape_correlation=float(np.corrcoef(a,g)[0,1]) if a.std()>1e-9 and g.std()>1e-9 else None,
        status='scope_fleet_profile_consistency_flag_not_missing_capacity_estimate')

def aggregate_inputs(n,fixed,zones):
    labels=n.buses.bidding_zone.replace({'ES-IB-MA':'ES'})
    shape=(8760,len(zones));out={k:np.zeros(shape) for k in ['demand','fixed_hydro',*FAMILIES]}
    load=n.get_switchable_as_dense('Load','p_set');av=n.get_switchable_as_dense('Generator','p_max_pu')*n.generators.p_nom
    for name,row in n.loads.iterrows():out['demand'][:,zones.index(labels[row.bus])]+=load[name].values
    for bus in fixed:out['fixed_hydro'][:,zones.index(labels[bus])]+=fixed[bus].values
    for name,row in n.generators.iterrows():
        for family,carriers in FAMILIES.items():
            if row.carrier in carriers:out[family][:,zones.index(labels[row.bus])]+=av[name].values
    out['residual_vre']=out['demand']-out['wind']-out['solar']
    out['residual_low_cost']=out['residual_vre']-sum(out[k] for k in ['nuclear','ror','biomass','fixed_hydro'])
    return out

def read_generation(replay,zones):
    arrays={k:np.full((8760,len(zones)),np.nan) for k in TYPES};scopes={};coverage={}
    for area in replay['zones']:
        z=area['zone']
        if z not in zones:continue
        j=zones.index(z);scopes[z]=area['geographic_scope'];coverage[z]=area['verified_months']
        for month in area['monthly']:
            if month['status']!='raw_interval_energy_replayed':continue
            rows=json.loads((ROOT/f"data/carbon-pilot/map-2025/{z}/{month['month']:02d}.json").read_text())
            for row in rows:
                t=int((pd.Timestamp(row['start']).tz_localize(None)-pd.Timestamp('2025-01-01')).total_seconds()/3600)
                for family,kinds in TYPES.items():
                    named=kinds&set(row['reported_types'])
                    if named and named<=set(row['generation_mwh_by_type']):
                        arrays[family][t,j]=sum(row['generation_mwh_by_type'][k] for k in named)
    return arrays,scopes,coverage

def national_demand(n):
    p=ROOT/'data/pypsa-eur/ember-current-release/monthly.csv';receipt=json.loads(p.with_name('receipt.json').read_text());assert digest(p)==receipt['sha256']
    frame=pd.read_csv(p,usecols=['Date','ISO 3 code','Area type','Electricity source','Generation (TWh)'])
    frame=frame[frame.Date.str.startswith('2025')&frame['Area type'].str.lower().str.startswith('country')&frame['Electricity source'].eq('Demand')]
    load=n.get_switchable_as_dense('Load','p_set');country=n.loads.bus.map(n.buses.country);rows=[]
    for c in sorted(n.buses.country.unique()):
        x=load.loc[:,country.eq(c)].sum(axis=1);q=frame[frame['ISO 3 code'].eq(CODES.get(c))]
        months=[]
        for month in range(1,13):
            v=q[q.Date.str.startswith(f'2025-{month:02d}')];assert len(v)<=1,'Duplicate monthly national demand'
            ref=None if not len(v) else float(v['Generation (TWh)'].iloc[0])
            value=float(x[n.snapshots.month==month].sum()/1e6)
            months.append(dict(month=month,model_twh=value,ember_twh=ref))
        complete=all(r['ember_twh'] is not None for r in months);ref=sum(r['ember_twh'] for r in months) if complete else None
        model=float(x.sum()/1e6)
        rows.append(dict(country=c,iso3=CODES.get(c),model_twh=model,ember_twh=ref,
            relative_difference=None if ref is None or ref<=0 else model/ref-1,monthly=months,
            status='national_scope_unreconciled' if complete else 'incomplete_reference_not_annualised'))
    return rows,receipt

def produce(out):
    start=time.perf_counter()
    (out/'design.json').write_text(json.dumps(dict(year=2025,areas='All 48 retained clearing areas; no omitted adverse zones',
        thresholds='Generation above availability >1 MW; national demand difference >5% flags investigation, not acceptance',
        fitting='None; previously inspected 2025 prices are descriptive targets, not held-out validation',
        scope='No new solve, input substitution, acceptance or causal attribution; demand scope and availability vs generation stay distinct'),indent=2)+'\n')
    bs=json.loads((BASE/'summary.json').read_text());assert digest(BASE/'annual.npz')==bs['witness_sha256']
    zones=bs['cases']['bidding_zone']['zones']
    print('Replaying cached generation source intervals',flush=True)
    replay=generation_audit(ROOT/'data/carbon-pilot/map-2025',ROOT/'data/carbon-pilot/entsoe/raw')
    (out/'generation-replay.json').write_text(json.dumps(replay,indent=2)+'\n')
    print('Rebuilding unchanged retained network inputs',flush=True)
    n,cost,fixed,mapping,original,old,hp=build()
    np.testing.assert_array_equal(n.snapshots.values,np.datetime64('2025-01-01')+np.arange(8760).astype('timedelta64[h]'))
    for k in ['objective','generators','stores']:np.testing.assert_array_equal(n.snapshot_weightings[k],1.)
    arrays=aggregate_inputs(n,fixed,zones);gen,scopes,coverage=read_generation(replay,zones)
    demand,receipt=national_demand(n)
    with np.load(BASE/'annual.npz') as a:prices=a['bidding_zone_prices'].copy()
    obs=observed({'zones':zones},prices);priced={r['model_area']:r for r in obs if r['metrics']['known_hours']}
    rows=[]
    for j,z in enumerate(zones):
        resources={k:array_stats(arrays[k][:,j],gen[k][:,j]) for k in TYPES}
        p=priced.get(z);relationship={}
        if p:
            label=p['zone'];o=np.array(json.loads((ROOT/f'data/price-trace/dispatch-validation-2025-v2/{label}.json').read_text()),float)
            valid=np.isfinite(o);r=arrays['residual_vre'][valid,j]
            relationship=dict(observed_price_correlation=float(np.corrcoef(r,o[valid])[0,1]) if r.std()>1e-9 else None,
                observed_price_mae=p['metrics']['mae_eur_mwh'],model_price_correlation=p['metrics']['correlation'])
        rows.append(dict(zone=z,generation_scope=scopes.get(z,'unavailable'),verified_generation_months=coverage.get(z,0),
            annual_twh={k:float(v[:,j].sum()/1e6) for k,v in arrays.items()},
            negative_vre_residual_hours=int((arrays['residual_vre'][:,j]<-1e-6).sum()),
            minimum_vre_residual_mw=float(arrays['residual_vre'][:,j].min()),maximum_vre_residual_mw=float(arrays['residual_vre'][:,j].max()),
            low_cost_envelope_above_local_thermal_hours=int((arrays['residual_low_cost'][:,j]>arrays['thermal'][:,j]+1).sum()),
            resources=resources,price_association=relationship))
    np.savez_compressed(out/'hourly.npz',zones=np.array(zones),**arrays,**{'reported_'+k:v for k,v in gen.items()})
    deps={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    summary=dict(status='residual_demand_source_diagnostic_not_model_acceptance',zones=rows,national_demand=demand,
        ember_receipt=receipt,mapping=mapping,price_comparisons=obs,
        baseline_summary_sha256=digest(BASE/'summary.json'),baseline_witness_sha256=digest(BASE/'annual.npz'),
        witness_sha256=digest(out/'hourly.npz'),generation_replay_sha256=digest(out/'generation-replay.json'),
        producer_sha256=digest(__file__),dependencies=deps,design_sha256=digest(out/'design.json'),
        elapsed_seconds=time.perf_counter()-start,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        limits=['Generation below available supply can reflect curtailment; the difference is not a measured availability error.',
            'Generation above availability flags fleet, profile, units or reporting scope; not a causal error share.',
            'Unreported technologies and missing hours remain unknown, never zero-filled.',
            'Residual low-cost supply subtracts full available nuclear/ROR/biomass plus fixed hydro; not actual dispatch.',
            'Local supply deficits can be met by imports; this envelope ignores transmission deliverability and strategic bids.',
            'Demand is prepared model demand, not certified observed zonal demand; Ember national scope is unreconciled.',
            'DE generation excludes LU; other generation reporting-area and historical geographic boundaries retain proxies.',
            'Hydro is a fixed schedule; nuclear is a 2024 availability proxy; emergency supply and storage discharge excluded.',
            'No price fitting, source correction, fresh clearing, accepted baseline or browser integration.'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print('Completed all',len(zones),'areas',round(summary['elapsed_seconds'],2),'seconds',flush=True)

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1200);produce(a.out)
