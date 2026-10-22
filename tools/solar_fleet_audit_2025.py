"""Country solar-source diagnosis and one declared loss sensitivity; no fitting."""
import argparse
import fcntl
import gzip
import json
import resource
import time
import numpy as np
import pandas as pd
import xarray as xr
from scipy.sparse import load_npz
from generation_mix_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/solar-fleet-audit-v1'
ANCHOR=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'
GRID=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025'
PLAN=ROOT/'config/solar-fleet-audit-2025.json'
TARGET=ROOT/'data/price-trace/sdac-hourly-2025-v1'
PUBLIC=ROOT/'public/research/country-explorer-2025'
PVGIS=ROOT/'data/bidding-zone-network-2025/renewable-source-bids-v1/pvgis-methodology.html'
PANEL=ROOT/'data/pypsa-eur/upstream/.pixi/envs/default/lib/python3.12/site-packages/atlite/resources/solarpanel/CSi.yaml'


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def replace_losses(pv, inverter=.90, retention=.86):
    if not 0<retention<=inverter<=1:raise ValueError('Loss retention must replace existing inverter factor')
    return np.asarray(pv)*retention/inverter


def combine_regions(regions, required):
    """An unknown constituent cannot become a zero in a national total."""
    if not required or any(r not in regions for r in required):return np.full(8760,np.nan)
    return np.stack([regions[r] for r in required]).sum(axis=0)


def allocate(dispatch,total,part):
    """Marginal ranges for a resource in identical-price offer pools, not CIs."""
    if np.min(part)<-1e-7 or np.max(part-total)>1e-5:raise ValueError('Resource exceeds its offer pool')
    q=np.clip(dispatch,0,total)
    return (np.divide(q*part,total,out=np.zeros_like(q),where=total>0).sum(axis=1),
            np.maximum(q-total+part,0).sum(axis=1),np.minimum(q,part).sum(axis=1))


def prepare():
    OUT.mkdir(parents=True,exist_ok=False)
    p=json.loads((ANCHOR/'inputs.json').read_text());s=json.loads((ANCHOR/'summary.json').read_text())
    a=json.loads((ANCHOR/'audit.json').read_text())
    assert a['summary_sha256']==digest(ANCHOR/'summary.json') and a['inputs_sha256']==digest(ANCHOR/'inputs.json')
    assert a['status']=='all_35040_hourly_source_native_and_optimality_replays_passed'
    for f,h in p['files'].items():assert digest(ANCHOR/f)==h
    paths=[PLAN,ANCHOR/'inputs.json',ANCHOR/'summary.json',ANCHOR/'audit.json',PVGIS,PANEL,TARGET/'summary.json',TARGET/'audit.json',TARGET/'prices.npz',PUBLIC/'manifest.json']
    assert 'inverter_efficiency: 0.9' in PANEL.read_text() and '14%' in PVGIS.read_text()
    network=GRID/'networks/base_s_128_elec_.nc';pool_path=ROOT/'data/bidding-zone-network-2025/january-supply-balance-v1/pooling.npz'
    irena_path=ROOT/'public/research/irena-capacity-2025/summary.json.gz'
    irena=json.loads(gzip.decompress(irena_path.read_bytes()));records=irena['irena_rows']
    pool=load_npz(pool_path).toarray();paths += [network,pool_path,irena_path]
    source=dict(np.load(ANCHOR/'inputs.npz'));parts=[];maps=[];countries=[];names=[];inventory=[]
    with xr.open_dataset(network) as d:
        fuels=d.generators_carrier.values.astype(str);nom=d.generators_p_nom.values
        cm=dict(zip(d.buses_i.values,d.buses_country.values));codes=np.array([cm[b] for b in d.generators_bus.values]);all_names=d.generators_i.values.astype(str)
        for technology in ['solar','solar-hsat']:
            path=GRID/f'profile_128_{technology}.nc';paths.append(path)
            with xr.open_dataset(path) as prof:
                assert prof.attrs['module']=='era5' and prof.sizes['time']==8760
                for j in np.flatnonzero(fuels==technology):
                    if nom[j]==0:continue
                    c=str(codes[j]);bus,bin_id=all_names[j].removesuffix(' '+technology).rsplit(' ',1)
                    cf=prof.profile.sel(bus=bus,bin=int(bin_id)).isel(year=0).values
                    ids=(codes==c)&np.isin(fuels,['solar','solar-hsat']);existing=float(nom[ids].sum())
                    row=next((r for r in records if r['country']==c and r['technology']=='Solar photovoltaic'),None)
                    factor=np.ones(8760) if row is None else (row['capacity_2024']['mw']+(row['capacity_2025']['mw']-row['capacity_2024']['mw'])*np.arange(8760)/8760)/existing
                    parts.append(np.r_[cf[1:],0.]*nom[j]*factor);maps.append(pool[j]);countries.append(c);names.append(str(all_names[j]))
        for c in sorted(set(countries)):
            ids=(codes==c)&np.isin(fuels,['solar','solar-hsat']);row=next((r for r in records if r['country']==c and r['technology']=='Solar photovoltaic'),None)
            inventory.append(dict(country=c,source_nameplate_mw=float(nom[ids].sum()),fixed_mw=float(nom[(codes==c)&(fuels=='solar')].sum()),tracking_mw=float(nom[(codes==c)&(fuels=='solar-hsat')].sum()),
                source_profiles=int(ids.sum()),positive_source_profiles=int((nom[ids]>0).sum()),irena=row))
    native_pv=np.array(parts).T;mapping=np.array(maps)
    np.testing.assert_allclose(native_pv@mapping,source['solar_aligned'],rtol=0,atol=1e-7)
    manifest=json.loads((PUBLIC/'manifest.json').read_text());fi=next(i for i,t in enumerate(manifest['technologies']) if t['id']=='solar')
    observed={};scope={};ember={}
    for inv in inventory:
        c=inv['country'];file=PUBLIC/(c+'.json.gz')
        if not file.exists():observed[c]=np.full(8760,np.nan);scope[c]=dict(note='No public hourly source coverage');continue
        paths.append(file);country=json.loads(gzip.decompress(file.read_bytes()));regions={}
        for area in country['source_generation']:
            values=np.full(8760,np.nan)
            for receipt in area['provenance']:
                path=ROOT/f"data/carbon-pilot/map-2025/{area['area']}/{receipt['month']:02d}.json"
                assert digest(path)==receipt['processed_sha256'];paths.append(path)
                for r in json.loads(path.read_text()):
                    t=int((np.datetime64(r['start'].removesuffix('Z'))-np.datetime64('2025-01-01T00')).astype('timedelta64[h]').astype(int))
                    if 'B16' in r['generation_mwh_by_type']:
                        assert np.isnan(values[t]);values[t]=r['generation_mwh_by_type']['B16']
            regions[area['area']]=values
        national=next(g for g in country['generation'] if g['id']=='country:'+c)
        observed[c]=combine_regions(regions,national['source_areas'])
        decoded=np.array([np.nan if v is None else v/manifest['generation_scale'] for v in country['series'][national['observed'][fi]]])
        np.testing.assert_array_equal(np.isfinite(observed[c]),np.isfinite(decoded));good=np.isfinite(decoded)
        np.testing.assert_allclose(observed[c][good],decoded[good],rtol=0,atol=.05000001)
        scope[c]=dict(required_regions=national['source_areas'],missing_regions=national['missing_source_areas'],source_scopes=[dict(area=r['area'],scope=r['scope']) for r in country['source_generation'] if r['area'] in national['source_areas']])
        # Existing original Ember rows are source records, not old modeled totals.
        for r in country['ember_rows']:
            if r['Electricity source']=='Solar' and r['Date'].startswith('2025-'):
                key=f"{c}_{int(r['Date'][5:7]):02d}";assert key not in ember
                ember[key]=float(r['Generation (TWh)']) if r['Generation (TWh)']!='' else None
    path=OUT/'components.npz';np.savez_compressed(path,pv=native_pv,mapping=mapping,observed=np.column_stack([observed[c] for c in sorted(observed)]))
    paths.append(ROOT/s['cases']['solar_capacity']['annual']['witness'])
    weather=ROOT/'data/pypsa-eur/monthly-weather/2025-12/profiles.nc';paths.append(weather)
    with xr.open_dataset(weather) as w:weather_meta=dict(dx=float(w.x[1]-w.x[0]),dy=float(w.y[1]-w.y[0]),cells=int(w.x.size*w.y.size),converted_resources=json.loads(w.attrs['gridfix_resources']))
    paths += [ROOT/'tools/monthly_weather.py',ROOT/'tools/compact_cutout.py',ROOT/'data/pypsa-eur/upstream/scripts/build_renewable_profiles.py',ROOT/'data/pypsa-eur/irena-capacity-2026/capacity.pdf']
    write(OUT/'inputs.json',dict(status='sealed',producer_sha256=digest(__file__),design=json.loads(PLAN.read_text()),
        inventory=inventory,native_names=names,native_countries=countries,countries=sorted(observed),scope=scope,ember=ember,weather=weather_meta,
        components_sha256=digest(path),source_hashes={str(f.relative_to(ROOT)):digest(f) for f in paths},anchor_files=p['files'],
        dependencies={f:digest(ROOT/'tools'/f) for f in ['joint_network_clear_2025.py','nve_hydro_diagnostics.py','run_regional_water_candidate_2025.py','run_seasonal_calendar_bids_2025.py','generation_mix_2025.py']}))
    print('Prepared',len(names),'positive PV source profiles;',len(observed),'countries',flush=True)


def load():
    sealed=json.loads((OUT/'inputs.json').read_text());assert sealed['producer_sha256']==digest(__file__)
    for f,h in sealed['source_hashes'].items():assert digest(ROOT/f)==h
    for f,h in sealed['anchor_files'].items():assert digest(ANCHOR/f)==h
    for f,h in sealed['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    assert digest(OUT/'components.npz')==sealed['components_sha256']
    p=json.loads((ANCHOR/'inputs.json').read_text());source=dict(np.load(ANCHOR/'inputs.npz'))
    av=source['availability']+source['solar_aligned']-source['solar_original']
    for r,v in zip(p['capacity'],source['thermal'],strict=True):av+=(r['factor']-1)*v
    return sealed,p,source,av


def run():
    from joint_network_clear_2025 import clear_or_reject
    from run_seasonal_calendar_bids_2025 import summary_prices
    sealed,p,source,control=load();outcomes={}
    observed=np.load(TARGET/'prices.npz')['prices'];base={k:source[k] for k in ['cost','load','island_rhs','link_min','link_max','ratings','emergency_mask','offer_zones']}
    base.update(A=load_npz(ANCHOR/'network.npz'),ng=p['ng'],nl=p['nl'],nz=p['nz'],zones=p['zones'],islands=[None]*p['islands'])
    for name in sealed['design']['cases']:
        av=control if name=='control' else control+replace_losses(source['solar_aligned'])-source['solar_aligned']
        assert av.min()>-1e-7
        if name=='control':
            previous=json.loads((ANCHOR/'summary.json').read_text())['cases']['solar_capacity']['annual'];path=ROOT/previous['witness'];info=previous|dict(reused=True)
            with np.load(path) as z:x,y=z['values'],z['row_duals']
        else:
            path=OUT/(name+'.npz');assert not path.exists(),'No implicit resume'
            x,y,_,info=clear_or_reject(base|dict(availability=av),source['flow'],source['cost'],path)
            info |= dict(witness=str(path.relative_to(ROOT)),reused=False)
            if x is None:write(OUT/'failure.json',dict(case=name,info=info));raise RuntimeError('Incomplete year')
        emergency=float(x[:,:p['ng']][:,source['emergency_mask']].sum());metrics=summary_prices(y[:,:p['nz']],observed,p['zones'])
        known=[r for r in metrics['zones'] if r['known_hours']==8760];assert len(known)==41
        outcomes[name]=dict(annual=info,metrics=metrics,europe_mae=float(np.mean([r['mae_eur_mwh'] for r in known])),emergency_mwh=emergency,acceptable_supply=emergency<=1e-6)
        write(OUT/'progress.json',outcomes);print(name,outcomes[name]['europe_mae'],'emergency',emergency,flush=True)
    write(OUT/'summary.json',dict(status='two_annual_cases_complete',producer_sha256=digest(__file__),inputs_sha256=digest(OUT/'inputs.json'),cases=outcomes))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['prepare','run']);args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3))
    lock=(OUT.parent/'solar-fleet-audit-v1.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    prepare() if args.stage=='prepare' else run()
