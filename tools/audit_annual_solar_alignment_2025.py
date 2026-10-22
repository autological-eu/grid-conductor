"""Independent whole-year source-clock, native-component and primal/dual replay.

Does not import the new annual producer, source compiler or clearing driver.
Original oil/bid book is pinned by its previously independent audit and fresh
hashes; this audit reconstructs every changed input from original source cells.
"""
import datetime as dt
import gzip
import json
import logging
from pathlib import Path
import subprocess
import time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pypsa
import xarray as xr
from scipy.sparse import load_npz
from generation_mix_2025 import ROOT, digest
from audit_nve_hydro_diagnostics_2025 import physics

OUT=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'
JAN=ROOT/'data/bidding-zone-network-2025/january-supply-balance-v1'
MODEL=ROOT/'data/bidding-zone-network-2025/oil-chp-bids-v2'
TARGET=ROOT/'data/price-trace/sdac-hourly-2025-v1'
GRID=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025'


def noaa_altitudes(lat, lon, times):
    """Independent solar geometry, not atlite's Michalsky implementation."""
    clock=pd.DatetimeIndex(times)
    hour=clock.hour.to_numpy()+clock.minute.to_numpy()/60
    gamma=2*np.pi/365*(clock.dayofyear.to_numpy()-1+(hour-12)/24)
    eq=229.18*(.000075+.001868*np.cos(gamma)-.032077*np.sin(gamma)-.014615*np.cos(2*gamma)-.040849*np.sin(2*gamma))
    dec=(.006918-.399912*np.cos(gamma)+.070257*np.sin(gamma)-.006758*np.cos(2*gamma)+.000907*np.sin(2*gamma)-.002697*np.cos(3*gamma)+.00148*np.sin(3*gamma))[:,None,None]
    ha=np.deg2rad((hour[:,None,None]*60+eq[:,None,None]+4*lon)%1440/4-180)
    latitude=np.deg2rad(lat)
    return np.rad2deg(np.arcsin(np.sin(latitude)*np.sin(dec)+np.cos(latitude)*np.cos(dec)*np.cos(ha)))


def source_replay(p, source):
    prior=json.loads((MODEL/'summary.json').read_text())
    cert=json.loads((MODEL/'verification-v2/audit.json').read_text())
    assert cert['status']=='passed' and cert['summary_sha256']==digest(MODEL/'summary.json')
    # The original study used then-current explorer files only for validation.
    # The user later replaced the public explorer. Verify those exact historical
    # bytes from Git; never waive the old hashes or restore obsolete public data.
    archive='5e1fe632861f402029047e3d1ca0c384a2b6212f'
    historical={}
    import hashlib
    for file,sha in prior['source_hashes'].items():
        if file.startswith('public/research/country-explorer-2025/'):
            raw=subprocess.check_output(['git','show',archive+':'+file],cwd=ROOT)
            assert hashlib.sha256(raw).hexdigest()==sha
            historical[file]=sha
        else:assert digest(ROOT/file)==sha
    for file,sha in prior['dependencies'].items(): assert digest(ROOT/'tools'/file)==sha
    # Original complete physical book fingerprint, independently certified before
    # this study. Costs are also bound by its dual witness below.
    A=load_npz(OUT/'network.npz')
    fingerprints={k:hashlib.sha256(np.ascontiguousarray(source[k]).tobytes()).hexdigest() for k in ['availability','load','link_min','link_max','island_rhs','ratings']}
    fingerprints.update(offsets=hashlib.sha256(np.ascontiguousarray(source['flow']).tobytes()).hexdigest(),
        A_data=hashlib.sha256(A.data.tobytes()).hexdigest(),A_indices=hashlib.sha256(A.indices.tobytes()).hexdigest(),A_indptr=hashlib.sha256(A.indptr.tobytes()).hexdigest(),
        weights=hashlib.sha256(json.dumps(p['weights'],sort_keys=True).encode()).hexdigest())
    assert fingerprints==prior['outcomes']['chp25']['physical_inputs']
    with xr.open_dataset(ROOT/'data/pypsa-eur/monthly-weather/2025-12/profiles.nc') as weather:
        times=pd.date_range('2025-12-31T23:00','2026-01-01T00:00',freq='min')
        latitude=np.broadcast_to(weather.lat.values, (weather.y.size,weather.x.size)) if weather.lat.ndim==2 else np.broadcast_to(weather.lat.values[:,None],(weather.y.size,weather.x.size))
        longitude=np.broadcast_to(weather.lon.values,latitude.shape) if weather.lon.ndim==2 else np.broadcast_to(weather.lon.values[None,:],latitude.shape)
        solar=noaa_altitudes(latitude,longitude,times)
        independent_max=float(solar.max());assert independent_max+2<1
        assert abs(independent_max-p['endpoint']['maximum_sampled_altitude_degrees'])<1
        assert p['endpoint']['coefficient']==0 and p['endpoint']['grid_cells']==latitude.size
    # Original converter explicitly kills all irradiation below 1 degree,
    # regardless of missing meteorology; both retained PV panels map zero to zero.
    import atlite.pv.irradiation as irradiation
    import atlite.convert as convert
    import atlite.pv.solar_panel_model as panels
    from atlite.resource import get_solarpanelconfig
    text=Path(irradiation.__file__).read_text();assert 'altitude_threshold=1.0' in text and 'result.where(~(cap_alt | (direct + diffuse <= 0.01)), 0)' in text
    assert 'SolarPanelModel' in Path(convert.__file__).read_text()
    panel=get_solarpanelconfig('CSi')
    zero=panels.SolarPanelModel(xr.Dataset({'temperature':('time',[220.,270.,330.])}),xr.DataArray(np.zeros(3),dims=['time']),panel)
    np.testing.assert_array_equal(zero.values,np.zeros(3))
    allocation=json.loads((ROOT/'data/bidding-zone-network-2025/annual-v7/mapping.json').read_text())['allocation']
    layout=json.loads((ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json').read_text())
    records=json.loads(gzip.decompress((ROOT/'public/research/irena-capacity-2025/summary.json.gz').read_bytes()))['irena_rows']
    old=np.zeros((8760,p['ng']));new=old.copy();country_energy={}
    with xr.open_dataset(GRID/'networks/base_s_128_elec_.nc') as ds:
        names=list(ds.generators_i.values.astype(str));lookup={name:i for i,name in enumerate(names)}
        nom=ds.generators_p_nom.values;fuel=ds.generators_carrier.values.astype(str)
        cm=dict(zip(ds.buses_i.values,ds.buses_country.values));country=np.array([cm[b] for b in ds.generators_bus.values])
        refined=[]
        for row in allocation:
            if row['component']=='Generator': refined.extend((lookup.get(row['name']),w) for w in row['shares'].values() if w>0)
        pool=np.zeros((len(names),p['ng']))
        for col,members in enumerate(layout['members']):
            for member in members:
                if member<len(refined) and refined[member][0] is not None:
                    j,w=refined[member];pool[j,col]+=w*layout['fractions'][col]
        np.testing.assert_allclose(pool,load_npz(JAN/'pooling.npz').toarray(),rtol=0,atol=1e-12)
        clock=ds.snapshots_snapshot.values;assert len(clock)==8760
        np.testing.assert_array_equal(clock,pd.date_range('2025-01-01',periods=8760,freq='h').values)
        raw_names=list(ds.generators_t_p_max_pu_i.values)
        for tech in ['solar','solar-hsat']:
            with xr.open_dataset(GRID/f'profile_128_{tech}.nc') as profile:
                np.testing.assert_array_equal(profile.time.values,clock);assert profile.attrs['module']=='era5'
                for j in np.flatnonzero(fuel==tech):
                    bus,bin_id=names[j].removesuffix(' '+tech).rsplit(' ',1)
                    cf=profile.profile.sel(bus=bus,bin=int(bin_id)).isel(year=0).values
                    np.testing.assert_array_equal(cf,ds.generators_t_p_max_pu[:,raw_names.index(names[j])].values)
                    code=country[j];ids=np.flatnonzero((country==code)&np.isin(fuel,['solar','solar-hsat']))
                    r=next((r for r in records if r['country']==code and r['technology']=='Solar photovoltaic'),None)
                    factor=np.ones(8760) if r is None else (r['capacity_2024']['mw']+(r['capacity_2025']['mw']-r['capacity_2024']['mw'])*np.arange(8760)/8760)/nom[ids].sum()
                    native=cf*nom[j]*factor;corrected=np.r_[cf[1:],0.]*nom[j]*factor
                    # Sparse per-generator accumulation independently reproduces
                    # the producer's batched country/technology multiplication.
                    for col in np.flatnonzero(pool[j]):old[:,col]+=native*pool[j,col];new[:,col]+=corrected*pool[j,col]
                    c=country_energy.setdefault(code,[0.,0.]);c[0]+=native.sum()/1e6;c[1]+=corrected.sum()/1e6
        thermal=np.array([(nom*((country=='DE')&np.isin(fuel,types)))@pool for types in [['coal'],['lignite'],['CCGT','OCGT']]])
    np.testing.assert_allclose(old,source['solar_original'],rtol=0,atol=1e-7)
    np.testing.assert_allclose(new,source['solar_aligned'],rtol=0,atol=1e-7)
    np.testing.assert_allclose(thermal,source['thermal'],rtol=0,atol=1e-7)
    for code,energy in country_energy.items():
        row=p['countries'][code];assert abs(energy[0]-row['original_available_twh'])<1e-8 and abs(energy[1]-row['aligned_available_twh'])<1e-8
    for row,vector in zip(p['capacity'],thermal):
        src=json.loads((JAN/('installed_'+row['technology']+'.json')).read_text())
        values=[v for t,v in src['samples'] if dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).astimezone(ZoneInfo('Europe/Berlin')).year==2025]
        assert len(values)==1 and values[0]==row['reported_2025_mw']
        assert abs(vector.sum()-row['model_mw'])<1e-7 and abs(row['factor']-values[0]/vector.sum())<1e-12
    return A,old,new,thermal,dict(independent_solar_maximum_degrees=independent_max,source_countries=len(country_energy),
        converter_source_sha256={str(Path(module.__file__).relative_to(ROOT)):digest(module.__file__) for module in [irradiation,convert,panels]},
        panel_configuration=panel,historical_validation_archive_commit=archive,historical_validation_sha256=historical)


def audit():
    began=time.perf_counter();p=json.loads((OUT/'inputs.json').read_text());s=json.loads((OUT/'summary.json').read_text())
    assert p['producer_sha256']==s['producer_sha256']==digest(ROOT/'tools/annual_solar_alignment_2025.py')
    assert s['inputs_sha256']==digest(OUT/'inputs.json') and s['design']==json.loads((ROOT/'config/annual-solar-alignment-2025.json').read_text())
    for file,h in p['source_hashes'].items():assert digest(ROOT/file)==h
    for file,h in p['files'].items():assert digest(OUT/file)==h
    for file,h in p['dependencies'].items():assert digest(ROOT/'tools'/file)==h
    ta=json.loads((TARGET/'audit.json').read_text());assert ta['summary_sha256']==digest(TARGET/'summary.json')
    ts=json.loads((TARGET/'summary.json').read_text());assert ts['zones']==p['zones'] and ts['prices_sha256']==digest(TARGET/'prices.npz')
    for file,h in ts['source_hashes'].items():assert digest(ROOT/file)==h
    source=dict(np.load(OUT/'inputs.npz'));observed=np.load(TARGET/'prices.npz')['prices']
    A,old,new,thermal,endpoint=source_replay(p,source)
    n=pypsa.Network(OUT/'native.nc');n.determine_network_topology()
    # The joint anchor's unchanged native Nordic branch allowance.
    for _,row in n.sub_networks.iterrows():
        for component,name in row.obj.branches_i():
            branch=n.df(component).loc[name]
            if {n.buses.loc[branch[k],'country'] for k in ['bus0','bus1']}&{'NO','SE','FI','DK'}:n.df(component).loc[name,'s_max_pu']*=1.15
    native_arrays=dict(np.load(OUT/'native-base.npz'));ng,nl,nz=p['ng'],p['nl'],p['nz'];certs={};independent_metrics={}
    complete=np.isfinite(observed).all(axis=0);assert complete.sum()==41
    for name,record in s['cases'].items():
        path=ROOT/record['annual']['witness'];assert digest(path)==record['annual']['witness_sha256']
        with np.load(path) as z:
            x,y,obj=z['values'],z['row_duals'],z['objectives'];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
        delta=np.zeros_like(old)
        if name in ['solar_interval','solar_capacity']:delta+=new-old
        if name in ['de_capacity','solar_capacity']:
            for row,vector in zip(p['capacity'],thermal):delta+=(row['factor']-1)*vector
        av=source['availability']+delta;assert av.min()>-1e-7
        maxima=dict(primal=0.,objective=0.,stationarity=0.,duality_gap=0.,complementarity=0.);native_max=0.
        for start in range(0,8760,168):
            sl=slice(start,min(start+168,8760));v=x[sl];yd=y[sl];T=len(v)
            cost=np.c_[source['cost'][sl],np.zeros((T,nl+nz))];rc=cost-(A.T@yd.T).T;ax=(A@v.T).T
            lower=np.c_[np.zeros((T,ng)),source['link_min'][sl],np.full((T,nz),-np.inf)]
            upper=np.c_[av[sl],source['link_max'][sl],np.full((T,nz),np.inf)]
            lo=np.c_[source['load'][sl],source['island_rhs'][sl],-source['ratings']-source['flow'][sl]]
            hi=np.c_[source['load'][sl],source['island_rhs'][sl],source['ratings']-source['flow'][sl]]
            primal=max(np.maximum(lower-v,0).max(),np.maximum(v-upper,0).max(),np.maximum(lo-ax,0).max(),np.maximum(ax-hi,0).max())
            dual=np.zeros(T);comp=0.
            for bound,part,value in [(lo,np.maximum(yd,0),ax),(hi,np.minimum(yd,0),ax),(lower,np.maximum(rc,0),v),(upper,np.minimum(rc,0),v)]:
                finite=np.isfinite(bound);assert abs(part[~finite]).max(initial=0)<1e-5
                dual+=np.sum(np.where(finite,bound,0)*part,axis=1)
                comp=max(comp,float(abs(part[finite]*(value[finite]-bound[finite])).max(initial=0)))
            vals=dict(primal=float(primal),objective=float(abs((v*cost).sum(axis=1)-obj[sl]).max()),stationarity=float(abs(rc[:,ng+nl:]).max()),duality_gap=float(abs(obj[sl]-dual).max()),complementarity=comp)
            for k,value in vals.items():maxima[k]=max(maxima[k],value)
            assert vals['primal']<=1e-4 and vals['stationarity']<1e-5 and max(vals[k] for k in ['objective','duality_gap','complementarity'])<.05,(name,start,vals)
            collapsed=v[:,:p['reference_ng']].copy()
            for extra in p['extras']:collapsed[:,extra['parent']]+=v[:,extra['column']]
            native_values=np.zeros((T,p['base_ng']))
            native_av=native_arrays['availability'][sl].copy()
            for j,parent in enumerate(p['parents']):
                native_values[:,parent]+=collapsed[:,j];native_av[:,parent]+=delta[sl,j]
            native_values=np.c_[native_values,collapsed[:,p['original_ng']:p['reference_ng']],v[:,ng:]]
            added=np.tile([row['mw'] for row in p['additions']],(T,1))
            native=dict(ng=p['base_ng']+len(p['additions']),nl=nl,nz=nz,zones=p['zones'],weights=p['weights'],
                offer_zones=p['base_offer_zones']+[r['zone'] for r in p['additions']],availability=np.c_[native_av,added],
                link_min=source['link_min'][sl],link_max=source['link_max'][sl])
            off=pd.DataFrame(native_arrays['off'][sl],index=range(T),columns=p['native_off_columns'])
            native_max=max(native_max,physics(n,native,native_values,source['load'][sl],off,0))
        emergency=float(x[:,:ng][:,source['emergency_mask']].sum());assert abs(emergency-record['emergency_mwh'])<1e-7
        metrics=[]
        for j,zone in enumerate(p['zones']):
            valid=np.isfinite(observed[:,j]);assert valid.sum() in [0,8760]
            if not valid.any():metrics.append(dict(zone=zone,hours=0));continue
            a=y[:,j];b=observed[:,j];err=a-b
            row=dict(zone=zone,hours=8760,mae=float(abs(err).sum()/8760),bias=float(err.sum()/8760),rmse=float(np.sqrt(np.dot(err,err)/8760)),correlation=float(np.corrcoef(a,b)[0,1]),
                ramp_mae=float(abs(np.diff(a)-np.diff(b)).mean()),tail_mae=float(abs(err[b>=np.quantile(b,.95)]).mean()),
                monthly_mae=[float(abs(err[pd.date_range('2025-01-01',periods=8760,freq='h').month==month]).mean()) for month in range(1,13)])
            reported=record['metrics']['zones'][j];assert reported['zone']==zone
            for field,key in [('mae','mae_eur_mwh'),('bias','bias_eur_mwh'),('rmse','rmse_eur_mwh'),('correlation','correlation')]:assert abs(row[field]-reported[key])<1e-8
            metrics.append(row)
        eu_codes=set('AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE'.split())
        european=[r for r in metrics if r['hours']==8760];eu=[r for r in european if r['zone'][:2] in eu_codes]
        assert len(eu)==record['eu_zones'] and abs(np.mean([r['mae'] for r in european])-record['europe_mae'])<1e-9 and abs(np.mean([r['mae'] for r in eu])-record['eu_mae'])<1e-9
        certs[name]=dict(hours=8760,native_residual_mw=native_max,emergency_mwh=emergency,acceptable_supply=emergency<=1e-6,**maxima)
        independent_metrics[name]=metrics
        print('Independently replayed',name,certs[name],flush=True)
    result=dict(status='all_35040_hourly_source_native_and_optimality_replays_passed',auditor_sha256=digest(__file__),
        summary_sha256=digest(OUT/'summary.json'),inputs_sha256=digest(OUT/'inputs.json'),cases=certs,
        endpoint=endpoint,metrics=independent_metrics,seconds=time.perf_counter()-began)
    (OUT/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);audit()
