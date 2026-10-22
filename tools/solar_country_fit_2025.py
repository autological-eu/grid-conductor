"""One-pass monthly country PV regression, with guarded full-year clearing."""
import argparse
import fcntl
import gzip
import json
import resource
import numpy as np
import pandas as pd
from scipy.sparse import load_npz
from generation_mix_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/solar-country-fit-v1'
SOLAR=ROOT/'data/bidding-zone-network-2025/solar-fleet-audit-v1'
ANCHOR=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'
PLAN=ROOT/'config/solar-country-fit-2025.json'
TARGET=ROOT/'data/price-trace/sdac-hourly-2025-v1'


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def monthly_factor(x,y,minimum=.5,maximum=1.):
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
    if x.shape!=(12,) or y.shape!=(12,) or not np.isfinite(x).all() or not np.isfinite(y).all() or min(x.min(),y.min())<0 or x.sum()<=0 or y.sum()<=0:
        return dict(factor=1.,raw_factor=None,status='missing_or_invalid_twelve_month_inputs')
    raw=float(np.dot(x,y)/np.dot(x,x))
    return dict(factor=raw if minimum<=raw<=maximum else 1.,raw_factor=raw,
                status='fitted' if minimum<=raw<=maximum else 'outside_reduction_guard_unchanged')


def prepare():
    from solar_fleet_audit_2025 import load
    prior,p,source,_=load();a=json.loads((SOLAR/'audit.json').read_text());s=json.loads((SOLAR/'summary.json').read_text())
    assert a['status']=='all_17520_source_native_kkt_and_generation_replays_passed'
    assert a['summary_sha256']==digest(SOLAR/'summary.json') and a['inputs_sha256']==digest(SOLAR/'inputs.json')
    assert a['auditor_sha256']==digest(ROOT/'tools/audit_solar_fleet_2025.py')
    OUT.mkdir(parents=True,exist_ok=False)
    design=json.loads(PLAN.read_text());guard=design['factor_guard'];components=dict(np.load(SOLAR/'components.npz'))
    irena_path=ROOT/'public/research/irena-capacity-2025/summary.json.gz';irena=json.loads(gzip.decompress(irena_path.read_bytes()))['irena_rows']
    month=pd.date_range('2025-01-01',periods=8760,freq='h').month.to_numpy();countries=prior['countries'];rows=[]
    for c in countries:
        ids=np.array(prior['native_countries'])==c;potential=components['pv'][:,ids].sum(axis=1)*86/90
        x=np.array([potential[month==m].sum()/1e6 for m in range(1,13)])
        y=np.array([prior['ember'].get(f'{c}_{m:02d}',np.nan) if prior['ember'].get(f'{c}_{m:02d}') is not None else np.nan for m in range(1,13)])
        result=monthly_factor(x,y,guard['minimum'],guard['maximum'])
        caps={t:next((r for r in irena if r['country']==c and r['technology']==t),None) for t in ['Solar energy','Solar photovoltaic']}
        if any(v is None for v in caps.values()):result.update(factor=1.,status='missing_parent_pv_capacity_scope')
        elif any(abs(caps['Solar energy'][year]['mw']-caps['Solar photovoltaic'][year]['mw'])>2 for year in ['capacity_2024','capacity_2025']):result.update(factor=1.,status='solar_thermal_scope_unchanged')
        if c=='NL':result.update(factor=1.,status='national_generation_source_conflict_unchanged')
        rows.append(dict(country=c,**result,weather_monthly_twh=x.tolist(),target_monthly_twh=[float(v) if np.isfinite(v) else None for v in y],
            input_monthly_sse=float(np.dot(x-y,x-y)) if np.isfinite(y).all() else None,
            scaled_weather_monthly_sse=float(np.dot(result['factor']*x-y,result['factor']*x-y)) if np.isfinite(y).all() else None))
    factors={r['country']:r['factor'] for r in rows};alphas=np.array([factors[c] for c in prior['native_countries']])
    # Factors act on source PV, so mixed equal-price solar/wind pools retain wind.
    delta=(components['pv']*((alphas-1)*86/90))@components['mapping']
    np.savez_compressed(OUT/'delta.npz',delta=delta)
    paths=[PLAN,SOLAR/'inputs.json',SOLAR/'summary.json',SOLAR/'audit.json',SOLAR/'components.npz',SOLAR/'system_losses.npz',irena_path,TARGET/'prices.npz',TARGET/'summary.json',TARGET/'audit.json']
    deps=['solar_fleet_audit_2025.py','audit_solar_fleet_2025.py','joint_network_clear_2025.py','nve_hydro_diagnostics.py','run_regional_water_candidate_2025.py','run_seasonal_calendar_bids_2025.py','generation_mix_2025.py']
    write(OUT/'inputs.json',dict(status='sealed',producer_sha256=digest(__file__),design=design,countries=countries,factors=rows,
        delta_sha256=digest(OUT/'delta.npz'),source_hashes={str(f.relative_to(ROOT)):digest(f) for f in paths},
        dependencies={f:digest(ROOT/'tools'/f) for f in deps},fitted_countries=[r['country'] for r in rows if r['status']=='fitted']))
    print('Fitted',[(r['country'],round(r['factor'],4)) for r in rows if r['status']=='fitted'],flush=True)


def run():
    from solar_fleet_audit_2025 import load
    from joint_network_clear_2025 import clear_or_reject
    from run_seasonal_calendar_bids_2025 import summary_prices
    sealed=json.loads((OUT/'inputs.json').read_text());assert sealed['producer_sha256']==digest(__file__)
    for f,h in sealed['source_hashes'].items():assert digest(ROOT/f)==h
    for f,h in sealed['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    assert sealed['delta_sha256']==digest(OUT/'delta.npz')
    _,p,source,av=load();av+=source['solar_aligned']*(86/90-1)
    base={k:source[k] for k in ['cost','load','island_rhs','link_min','link_max','ratings','emergency_mask','offer_zones']}
    base.update(A=load_npz(ANCHOR/'network.npz'),ng=p['ng'],nl=p['nl'],nz=p['nz'],zones=p['zones'],islands=[None]*p['islands'])
    delta=np.load(OUT/'delta.npz')['delta'];assert delta.max()<1e-7 and (av+delta).min()>-1e-7
    observed=np.load(TARGET/'prices.npz')['prices'];results={}
    for name in sealed['design']['cases']:
        if name=='control':
            prior=json.loads((SOLAR/'summary.json').read_text())['cases']['system_losses']['annual'];info=prior|dict(reused=True);path=ROOT/info['witness']
            with np.load(path) as z:x,y=z['values'],z['row_duals']
        else:
            path=OUT/(name+'.npz');assert not path.exists(),'No implicit resume'
            x,y,_,info=clear_or_reject(base|dict(availability=av+delta),source['flow'],source['cost'],path)
            info |= dict(witness=str(path.relative_to(ROOT)),reused=False)
            if x is None:write(OUT/'failure.json',dict(case=name,info=info));raise RuntimeError('Incomplete annual clear')
        metrics=summary_prices(y[:,:p['nz']],observed,p['zones']);known=[r for r in metrics['zones'] if r['known_hours']==8760]
        assert len(known)==41
        emergency=float(x[:,:p['ng']][:,source['emergency_mask']].sum())
        results[name]=dict(annual=info,metrics=metrics,europe_mae=float(np.mean([r['mae_eur_mwh'] for r in known])),emergency_mwh=emergency,acceptable_supply=emergency<=1e-6)
        write(OUT/'progress.json',results);print(name,results[name]['europe_mae'],'emergency',emergency,flush=True)
    write(OUT/'summary.json',dict(status='two_annual_cases_complete',producer_sha256=digest(__file__),inputs_sha256=digest(OUT/'inputs.json'),cases=results))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['prepare','run']);args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3))
    lock=(OUT.parent/'solar-country-fit-v1.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    prepare() if args.stage=='prepare' else run()
