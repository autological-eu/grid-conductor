"""Four fixed source-reconciliation cases; no fitting or annual promotion."""
import datetime as dt
import gzip
import json
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import xarray as xr
from scipy.sparse import load_npz,coo_matrix,save_npz
from generation_mix_2025 import ROOT,digest
from january_supply_sources_2025 import OUT,write
from thermal_event_model_2025 import compile_day,solve
from run_thermal_event_2025 import check_lp

BASE=ROOT/'data/bidding-zone-network-2025/thermal-event-v1'
GRID=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025'
PLAN=ROOT/'config/january-supply-balance-2025.json'


def interval_indices(source_times,target_times):
    """Map ERA5 hour-ending coefficients onto hour-start model intervals."""
    source=np.asarray(source_times,dtype='datetime64[h]');target=np.asarray(target_times,dtype='datetime64[h]')+np.timedelta64(1,'h')
    if len(np.unique(source))!=len(source):raise ValueError('Duplicate source clock')
    lookup={t:i for i,t in enumerate(source)}
    if any(t not in lookup for t in target):raise ValueError('Missing right-edge weather endpoint; never wrap/fill')
    return np.array([lookup[t] for t in target])


def annual_capacity(samples,year):
    selected=[float(v) for t,v in samples if dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).astimezone(ZoneInfo('Europe/Berlin')).year==year and v is not None]
    if len(selected)!=1:raise ValueError('One explicit reported year required')
    return selected[0]


def prepare():
    dest=OUT/'reconciliation-inputs.npz';assert not dest.exists()
    collection=json.loads((OUT/'collection.json').read_text());assert not collection['failures'] and collection['producer_sha256']==digest(ROOT/'tools/january_supply_sources_2025.py')
    for receipts in collection['sources'].values():
        for receipt in receipts:assert digest(OUT/receipt['file'])==receipt['sha256']
    meta=json.loads((BASE/'inputs-protocol-v2.json').read_text());a,b=meta['start_hour'],meta['stop_hour'];T=b-a
    source=dict(np.load(BASE/'inputs.npz'));previous=json.loads((BASE/'runs-v7/audit.json').read_text());assert previous['summary_sha256']==digest(BASE/'runs-v7/summary.json')
    layout_path=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json';mapping_path=ROOT/'data/bidding-zone-network-2025/annual-v7/mapping.json';irena_path=ROOT/'public/research/irena-capacity-2025/summary.json.gz'
    layout=json.loads(layout_path.read_text());allocation=json.loads(mapping_path.read_text())['allocation'];records=json.loads(gzip.decompress(irena_path.read_bytes()))['irena_rows']
    network=GRID/'networks/base_s_128_elec_.nc'
    with xr.open_dataset(network) as ds:
        names=ds.generators_i.values.astype(str).tolist();name_to_index={v:i for i,v in enumerate(names)};fuel=ds.generators_carrier.values.astype(str);nom=ds.generators_p_nom.values;country_map=dict(zip(ds.buses_i.values,ds.buses_country.values));country=np.array([country_map[v] for v in ds.generators_bus.values]);clock=ds.snapshots_snapshot.values;targets=clock[a:b];indices=interval_indices(clock,targets)
        columns=ds.generators_t_p_max_pu_i.values.tolist();original=np.zeros((T,len(names)));aligned=original.copy();profile_checks={}
        for technology in ['solar','solar-hsat']:
            ids=np.flatnonzero(fuel==technology)
            with xr.open_dataset(GRID/f'profile_128_{technology}.nc') as profile:
                assert profile.attrs['module']=='era5' and profile.attrs['time shift']=='-1 days +23:30:00'
                assert np.array_equal(profile.time.values,clock)
                errors=[]
                for j in ids:
                    bus,bin=names[j].removesuffix(' '+technology).rsplit(' ',1);raw=profile.profile.sel(bus=bus,bin=int(bin)).isel(year=0).values
                    carried=ds.generators_t_p_max_pu.values[:,columns.index(names[j])];errors.append(float(abs(raw-carried).max()));original[:,j]=raw[a:b]*nom[j];aligned[:,j]=raw[indices]*nom[j]
                profile_checks[technology]=dict(generators=len(ids),maximum_network_difference=max(errors));assert max(errors)==0
        for c in sorted(set(country)):
            ids=np.flatnonzero((country==c)&np.isin(fuel,['solar','solar-hsat']));total=nom[ids].sum();r=next((r for r in records if r['country']==c and r['technology']=='Solar photovoltaic'),None)
            if total>0 and r:
                factor=(r['capacity_2024']['mw']+(r['capacity_2025']['mw']-r['capacity_2024']['mw'])*np.arange(a,b)/8760)/total
                original[:,ids]*=factor[:,None];aligned[:,ids]*=factor[:,None]
        refined=[]
        for record in allocation:
            if record['component']!='Generator':continue
            j=name_to_index.get(record['name'])
            for weight in record['shares'].values():
                if weight>0:refined.append((j,weight))
        rr=[];cc=[];vv=[]
        for col,(ids,fraction) in enumerate(zip(layout['members'],layout['fractions'],strict=True)):
            for member in ids:
                if member>=len(refined):continue
                j,weight=refined[member]
                if j is not None:rr.append(j);cc.append(col);vv.append(weight*fraction)
        pool=coo_matrix((vv,(rr,cc)),shape=(len(names),meta['ng'])).tocsc();old=original@pool;new=aligned@pool
        with np.load(BASE/'resource-components.npz') as z:np.testing.assert_allclose(old,z['solar'],rtol=1e-10,atol=1e-7)
        thermal=np.array([pool.T@(nom*((country=='DE')&np.isin(fuel,fuels))) for fuels in [['coal'],['lignite'],['CCGT','OCGT']]])
        for v in thermal:
            ids=np.flatnonzero(v>0);np.testing.assert_allclose(source['availability'][:,ids],np.broadcast_to(v[ids],(T,len(ids))),rtol=0,atol=1e-7)
        capacity=[]
        for label,vector in zip(['hard_coal','lignite','gas'],thermal):
            value=annual_capacity(json.loads((OUT/f'installed_{label}.json').read_text())['samples'],2025);existing=float(vector.sum());assert 0<value<=existing
            capacity.append(dict(technology=label,model_mw=existing,reported_2025_mw=value,factor=value/existing))
        de_solar=original[:,country=='DE'].sum(axis=1);de_solar_aligned=aligned[:,country=='DE'].sum(axis=1)
    save_npz(OUT/'pooling.npz',pool);np.savez_compressed(dest,solar_original=old,solar_aligned=new,thermal=thermal,de_solar=de_solar,de_solar_aligned=de_solar_aligned)
    era5=ROOT/'data/pypsa-eur/upstream/.pixi/envs/default/lib/python3.12/site-packages/atlite/datasets/era5.py';adapter=ROOT/'tools/monthly_weather.py';loader=ROOT/'data/pypsa-eur/upstream/scripts/add_electricity.py'
    assert '13:01 to 14:00 are labelled as "14:00"' in era5.read_text()
    sources=[PLAN,BASE/'inputs-protocol-v2.json',BASE/'inputs.npz',BASE/'network.npz',BASE/'resource-components.npz',BASE/'runs-v7/summary.json',BASE/'runs-v7/audit.json',layout_path,mapping_path,irena_path,network,era5,adapter,loader,GRID/'profile_128_solar.nc',GRID/'profile_128_solar-hsat.nc',OUT/'collection.json',OUT/'configuration.json']+[OUT/(name+'.json') for name in ['installed_hard_coal','installed_lignite','installed_gas']]
    write(OUT/'reconciliation-inputs.json',dict(status='source_reconciliation_prepared',producer_sha256=digest(Path(__file__)),plan_sha256=digest(PLAN),source_hashes={str(p.relative_to(ROOT)):digest(p) for p in sources},files={p:digest(OUT/p) for p in ['reconciliation-inputs.npz','pooling.npz']},capacity=capacity,profile_checks=profile_checks,source_hours=indices.tolist(),destination_hours=list(range(a,b)),year_boundary='Full-year start-labelled PV needs the 2026-01-01T00:00 endpoint; not filled or wrapped here.'))
    print('Prepared source reconstruction',capacity,flush=True)


def run():
    folder=OUT/'clearing-v1';folder.mkdir(exist_ok=False);meta=json.loads((BASE/'inputs-protocol-v2.json').read_text());source=dict(np.load(BASE/'inputs.npz'));p=json.loads((OUT/'reconciliation-inputs.json').read_text());assert p['producer_sha256']==digest(Path(__file__))
    for file,h in p['source_hashes'].items():assert digest(ROOT/file)==h
    rec=dict(np.load(OUT/'reconciliation-inputs.npz'));A=load_npz(BASE/'network.npz');design=json.loads(PLAN.read_text());assert len(design['cases'])==design['maximum_cases']==4
    results={};files={};started=time.perf_counter()
    for name in design['cases']:
        availability=source['availability'].copy()
        if name in ['solar_interval','solar_capacity']:availability+=rec['solar_aligned']-rec['solar_original']
        if name in ['de_capacity','solar_capacity']:
            for vector,row in zip(rec['thermal'],p['capacity'],strict=True):availability+=(row['factor']-1)*vector
        assert availability.min()>-1e-7;availability=np.maximum(availability,0);case=source|dict(availability=availability);h=None;values=[];duals=[];reduced=[];objectives=[];certs=[];seconds=0.
        for t in range(meta['hours']):
            lp=compile_day(A,case,meta,design,'control',t,{},horizon=1)
            if name=='control':
                x=source['baseline'][t];y=source['baseline_duals'][t];rc=lp['c']-A.T@y;obj=float(source['baseline_objectives'][t])
            else:
                before=time.perf_counter();h,x,y,rc,obj=solve(lp,h);seconds+=time.perf_counter()-before
            certs.append(check_lp(lp,x,y,rc,obj));values.append(x);duals.append(y);reduced.append(rc);objectives.append(obj)
        x=np.array(values);y=np.array(duals);observed=source['observed'];eligible=np.isfinite(observed).all(axis=0);period=slice(48,216);emergency=x[:,np.flatnonzero(source['emergency_mask'])].sum(axis=1);de=meta['zones'].index('DE-LU');t=184
        path=folder/(name+'.npz');np.savez_compressed(path,values=x,row_duals=y,col_duals=np.array(reduced),objectives=objectives,availability=availability);files[path.name]=digest(path)
        results[name]=dict(solver_seconds=seconds,hours=len(x),evaluated_hours=168,mae_eur_mwh=float(abs(y[period,:meta['nz']][:,eligible]-observed[period][:,eligible]).mean()),german_mae_eur_mwh=float(abs(y[period,de]-observed[period,de]).mean()),january20_16utc_eur_mwh=float(y[t,de]),january15_16utc_eur_mwh=float(y[64,de]),emergency_mwh=float(emergency.sum()),acceptable_supply=bool(emergency.sum()<1e-6),certificates=certs,control_reused=name=='control')
        print(name,{k:v for k,v in results[name].items() if k!='certificates'},flush=True)
    write(folder/'summary.json',dict(status='four_source_cases_computed',producer_sha256=digest(Path(__file__)),helper_sha256=digest(ROOT/'tools/thermal_event_model_2025.py'),validation_helper_sha256=digest(ROOT/'tools/run_thermal_event_2025.py'),input_summary_sha256=digest(OUT/'reconciliation-inputs.json'),design=design,cases=results,files=files,elapsed_seconds=time.perf_counter()-started))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['prepare','run']);args=parser.parse_args()
    prepare() if args.stage=='prepare' else run()
