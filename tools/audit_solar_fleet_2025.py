"""Independent solar-source, hourly observations, native physics and KKT replay.

Does not import the new input compiler, allocation helper or clearing driver.
"""
import gzip
import json
import logging
import resource
import time
import numpy as np
import pandas as pd
import pypsa
import xarray as xr
from scipy.sparse import load_npz
from generation_mix_2025 import ROOT,digest
from audit_nve_hydro_diagnostics_2025 import physics

OUT=ROOT/'data/bidding-zone-network-2025/solar-fleet-audit-v1'
ANCHOR=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'
GRID=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025'
TZ=dict(zip('AL AT BA BE BG CH CZ DE DK EE ES FI FR GB GR HR HU IE IT LT LU LV ME MK NL NO PL PT RO RS SE SI SK XK'.split(),
 ['Tirane','Vienna','Sarajevo','Brussels','Sofia','Zurich','Prague','Berlin','Copenhagen','Tallinn','Madrid','Helsinki','Paris','London','Athens','Zagreb','Budapest','Dublin','Rome','Vilnius','Luxembourg','Riga','Podgorica','Skopje','Amsterdam','Oslo','Warsaw','Lisbon','Bucharest','Belgrade','Stockholm','Ljubljana','Bratislava','Belgrade']))


def diagnostics(c,available,point,lower,upper,obs,ember):
    good=np.isfinite(obs);clock=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC');local=clock.tz_convert('Europe/'+TZ[c])
    err=point[good]-obs[good];known=int(good.sum())
    result=dict(country=c,hours=known,available_twh=float(available.sum()/1e6),dispatch_twh=float(point.sum()/1e6),
        dispatch_lower_twh=float(lower.sum()/1e6),dispatch_upper_twh=float(upper.sum()/1e6),
        observed_covered_twh=float(np.nansum(obs)/1e6),observed_annual_twh=float(obs.sum()/1e6) if known==8760 else None,
        hourly_mae_mw=float(abs(err).mean()) if known else None,
        correlation=float(np.corrcoef(point[good],obs[good])[0,1]) if known and np.std(obs[good])>1e-8 and np.std(point[good])>1e-8 else None,
        outside_dispatch_bounds_mwh=float(np.maximum(lower[good]-obs[good],0).sum()+np.maximum(obs[good]-upper[good],0).sum()),
        source_during_zero_availability_mwh=float(obs[good&(available<1e-6)].sum()),
        source_peak_mw=float(obs[good].max()) if known else None,model_peak_mw=float(point[good].max()) if known else None)
    daily_obs=obs.reshape(365,24);daily_model=point.reshape(365,24);valid=np.isfinite(daily_obs).all(axis=1)
    result['complete_utc_days']=int(valid.sum())
    result['daily_energy_mae_mwh']=float(abs(daily_model[valid].sum(axis=1)-daily_obs[valid].sum(axis=1)).mean()) if valid.any() else None
    shape=valid&(np.nansum(daily_obs,axis=1)>1)&(daily_model.sum(axis=1)>1)
    result['daily_normalized_shape_l1']=float(abs(daily_model[shape]/daily_model[shape].sum(axis=1)[:,None]-daily_obs[shape]/daily_obs[shape].sum(axis=1)[:,None]).sum(axis=1).mean()) if shape.any() else None
    months=[];hours=[]
    for month in range(1,13):
        mask=clock.month==month;valid=mask&good;complete=int(valid.sum())==int(mask.sum())
        months.append(dict(country=c,month=month,known_hours=int(valid.sum()),expected_hours=int(mask.sum()),
            available_twh=float(available[mask].sum()/1e6),dispatch_twh=float(point[mask].sum()/1e6),lower_twh=float(lower[mask].sum()/1e6),upper_twh=float(upper[mask].sum()/1e6),
            observed_twh=float(obs[mask].sum()/1e6) if complete else None,ember_twh=ember.get(f'{c}_{month:02d}'),
            hourly_mae_mw=float(abs(point[valid]-obs[valid]).mean()) if valid.any() else None))
        for hour in range(24):
            # Civil-time/DST monthly/hourly groups; observations and model use
            # exactly the same covered UTC intervals. No seasonal pooling fit.
            mask=(local.month==month)&(local.hour==hour)&good
            hours.append(dict(country=c,month=month,hour=hour,samples=int(mask.sum()),
                observed_mw=float(obs[mask].mean()) if mask.any() else None,
                model_mw=float(point[mask].mean()) if mask.any() else None,
                lower_mw=float(lower[mask].mean()) if mask.any() else None,
                upper_mw=float(upper[mask].mean()) if mask.any() else None))
    known_ember=[r['ember_twh'] for r in months if r['ember_twh'] is not None]
    result['ember_months']=len(known_ember);result['ember_annual_twh']=float(sum(known_ember)) if len(known_ember)==12 else None
    return result,months,hours


def audit():
    began=time.perf_counter();sealed=json.loads((OUT/'inputs.json').read_text());s=json.loads((OUT/'summary.json').read_text())
    assert s['inputs_sha256']==digest(OUT/'inputs.json') and s['producer_sha256']==sealed['producer_sha256']==digest(ROOT/'tools/solar_fleet_audit_2025.py')
    assert sealed['design']==json.loads((ROOT/'config/solar-fleet-audit-2025.json').read_text())
    for f,h in sealed['source_hashes'].items():assert digest(ROOT/f)==h
    for f,h in sealed['anchor_files'].items():assert digest(ANCHOR/f)==h
    for f,h in sealed['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    assert sealed['components_sha256']==digest(OUT/'components.npz')
    p=json.loads((ANCHOR/'inputs.json').read_text());a=json.loads((ANCHOR/'audit.json').read_text())
    assert a['summary_sha256']==digest(ANCHOR/'summary.json') and a['inputs_sha256']==digest(ANCHOR/'inputs.json')
    assert a['auditor_sha256']==digest(ROOT/'tools/audit_annual_solar_alignment_2025.py')
    for f,h in p['source_hashes'].items():assert digest(ROOT/f)==h
    for f,h in p['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    source=dict(np.load(ANCHOR/'inputs.npz'));components=dict(np.load(OUT/'components.npz'));A=load_npz(ANCHOR/'network.npz')
    pool=load_npz(ROOT/'data/bidding-zone-network-2025/january-supply-balance-v1/pooling.npz').toarray()
    irena=json.loads(gzip.decompress((ROOT/'public/research/irena-capacity-2025/summary.json.gz').read_bytes()))
    assert digest(ROOT/'data/pypsa-eur/irena-capacity-2026/capacity.pdf')==irena['irena_pdf_sha256']
    pv=[];maps=[];names=[];codes=[]
    with xr.open_dataset(GRID/'networks/base_s_128_elec_.nc') as ds:
        cm=dict(zip(ds.buses_i.values,ds.buses_country.values));names_all=ds.generators_i.values.astype(str);nom=ds.generators_p_nom.values
        fuel=ds.generators_carrier.values.astype(str);country=np.array([cm[b] for b in ds.generators_bus.values]);columns=list(ds.generators_t_p_max_pu_i.values)
        for technology in ['solar','solar-hsat']:
            for j in np.flatnonzero((fuel==technology)&(nom>0)):
                c=str(country[j]);row=next((r for r in irena['irena_rows'] if r['country']==c and r['technology']=='Solar photovoltaic'),None)
                denominator=nom[(country==c)&np.isin(fuel,['solar','solar-hsat'])].sum()
                installed=np.full(8760,denominator) if row is None else np.linspace(row['capacity_2024']['mw'],row['capacity_2025']['mw'],8760,endpoint=False)
                coeff=ds.generators_t_p_max_pu[:,columns.index(names_all[j])].values
                bus,bin_id=names_all[j].removesuffix(' '+technology).rsplit(' ',1)
                with xr.open_dataset(GRID/f'profile_128_{technology}.nc') as profile:
                    np.testing.assert_array_equal(coeff,profile.profile.sel(bus=bus,bin=int(bin_id)).isel(year=0).values)
                pv.append(np.concatenate([coeff[1:],np.zeros(1)])*installed*nom[j]/denominator)
                maps.append(pool[j]);names.append(str(names_all[j]));codes.append(c)
    pv=np.array(pv).T;maps=np.array(maps);assert names==sealed['native_names'] and codes==sealed['native_countries']
    np.testing.assert_allclose(pv,components['pv'],rtol=0,atol=1e-7);np.testing.assert_array_equal(maps,components['mapping'])
    solar=pv@maps;np.testing.assert_allclose(solar,source['solar_aligned'],rtol=0,atol=1e-7)
    # The endpoint zero inherits the independently certified all-cell nighttime
    # proof in the unchanged annual anchor; never a missing daytime fill.
    assert p['endpoint']['coefficient']==0 and a['endpoint']['independent_solar_maximum_degrees']+2<1
    assert len(names)==123 and all('solar-hsat' not in name for name in names)
    html=(ROOT/'data/bidding-zone-network-2025/renewable-source-bids-v1/pvgis-methodology.html').read_text()
    assert '14%' in html
    panel=ROOT/'data/pypsa-eur/upstream/.pixi/envs/default/lib/python3.12/site-packages/atlite/resources/solarpanel/CSi.yaml'
    assert 'inverter_efficiency: 0.9' in panel.read_text()
    # Original observations reassembled with timestamp-indexed Series rather
    # than the producer's integer assignment. Missing constituents propagate.
    public=ROOT/'public/research/country-explorer-2025';manifest=json.loads((public/'manifest.json').read_text())
    solar_fi=next(i for i,t in enumerate(manifest['technologies']) if t['id']=='solar')
    clock=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC');obs=np.full_like(components['observed'],np.nan)
    for ci,c in enumerate(sealed['countries']):
        file=public/(c+'.json.gz')
        if not file.exists():continue
        d=json.loads(gzip.decompress(file.read_bytes()));group=next(r for r in d['generation'] if r['id']=='country:'+c)
        parts={}
        for area in d['source_generation']:
            records=[]
            for m in area['provenance']:
                path=ROOT/f"data/carbon-pilot/map-2025/{area['area']}/{m['month']:02d}.json";assert digest(path)==m['processed_sha256']
                records += [(pd.Timestamp(r['start']),r['generation_mwh_by_type']['B16']) for r in json.loads(path.read_text()) if 'B16' in r['generation_mwh_by_type']]
            if records:
                series=pd.Series([v for t,v in records],index=[t for t,v in records]);assert series.index.is_unique
                parts[area['area']]=series.reindex(clock).values
        required=group['source_areas']
        if required and all(k in parts for k in required):obs[:,ci]=np.sum([parts[k] for k in required],axis=0)
        rounded=np.array([np.nan if v is None else v/manifest['generation_scale'] for v in d['series'][group['observed'][solar_fi]]])
        np.testing.assert_array_equal(np.isnan(obs[:,ci]),np.isnan(rounded));good=np.isfinite(rounded)
        np.testing.assert_allclose(obs[good,ci],rounded[good],rtol=0,atol=.05000001)
        for r in d['ember_rows']:
            if r['Electricity source']=='Solar' and r['Date'].startswith('2025-'):
                expected=float(r['Generation (TWh)']) if r['Generation (TWh)'] else None
                assert sealed['ember'][f"{c}_{int(r['Date'][5:7]):02d}"]==expected
    np.testing.assert_array_equal(obs,components['observed'])
    control=source['availability']+solar-source['solar_original']
    for r,v in zip(p['capacity'],source['thermal'],strict=True):control+=(r['factor']-1)*v
    n=pypsa.Network(ANCHOR/'native.nc');n.determine_network_topology()
    for _,row in n.sub_networks.iterrows():
        for component,name in row.obj.branches_i():
            table=n.components[component].static;branch=table.loc[name]
            if {n.buses.loc[branch[k],'country'] for k in ['bus0','bus1']}&{'NO','SE','FI','DK'}:table.loc[name,'s_max_pu']*=1.15
    native_arrays=dict(np.load(ANCHOR/'native-base.npz'));ng,nl,nz=p['ng'],p['nl'],p['nz'];certs={};quantities={};monthly={};diurnal={};arrays={}
    for case,record in s['cases'].items():
        path=ROOT/record['annual']['witness'];assert digest(path)==record['annual']['witness_sha256']
        with np.load(path) as z:x,y,obj=z['values'],z['row_duals'],z['objectives'];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
        factor=1. if case=='control' else 86/90
        av=control+(factor-1)*solar
        maxima=dict(primal=0.,objective=0.,stationarity=0.,duality_gap=0.,complementarity=0.)
        for start in range(0,8760,168):
            sl=slice(start,min(start+168,8760));v=x[sl];yd=y[sl];T=len(v)
            cost=np.c_[source['cost'][sl],np.zeros((T,nl+nz))];rc=cost-(A.T@yd.T).T;ax=(A@v.T).T
            lower=np.c_[np.zeros((T,ng)),source['link_min'][sl],np.full((T,nz),-np.inf)];upper=np.c_[av[sl],source['link_max'][sl],np.full((T,nz),np.inf)]
            lo=np.c_[source['load'][sl],source['island_rhs'][sl],-source['ratings']-source['flow'][sl]];hi=np.c_[source['load'][sl],source['island_rhs'][sl],source['ratings']-source['flow'][sl]]
            primal=max(np.maximum(lower-v,0).max(),np.maximum(v-upper,0).max(),np.maximum(lo-ax,0).max(),np.maximum(ax-hi,0).max());dual=np.zeros(T);comp=0.
            for bound,part,value in [(lo,np.maximum(yd,0),ax),(hi,np.minimum(yd,0),ax),(lower,np.maximum(rc,0),v),(upper,np.minimum(rc,0),v)]:
                finite=np.isfinite(bound);assert abs(part[~finite]).max(initial=0)<1e-5;dual+=np.sum(np.where(finite,bound,0)*part,axis=1)
                comp=max(comp,float(abs(part[finite]*(value[finite]-bound[finite])).max(initial=0)))
            vals=dict(primal=float(primal),objective=float(abs((v*cost).sum(axis=1)-obj[sl]).max()),stationarity=float(abs(rc[:,ng+nl:]).max()),duality_gap=float(abs(obj[sl]-dual).max()),complementarity=comp)
            for k,val in vals.items():maxima[k]=max(maxima[k],val)
        assert maxima['primal']<=1e-4 and maxima['stationarity']<1e-5 and max(maxima[k] for k in ['objective','duality_gap','complementarity'])<.05
        collapsed=x[:,:p['reference_ng']].copy()
        for extra in p['extras']:collapsed[:,extra['parent']]+=x[:,extra['column']]
        native_values=np.zeros((8760,p['base_ng']));native_av=native_arrays['availability'].copy();delta=av-source['availability']
        for j,parent in enumerate(p['parents']):native_values[:,parent]+=collapsed[:,j];native_av[:,parent]+=delta[:,j]
        native_values=np.c_[native_values,collapsed[:,p['original_ng']:p['reference_ng']],x[:,ng:]]
        native=dict(ng=p['base_ng']+len(p['additions']),nl=nl,nz=nz,zones=p['zones'],weights=p['weights'],offer_zones=p['base_offer_zones']+[r['zone'] for r in p['additions']],
            availability=np.c_[native_av,np.tile([r['mw'] for r in p['additions']],(8760,1))],link_min=source['link_min'],link_max=source['link_max'])
        residual=physics(n,native,native_values,source['load'],pd.DataFrame(native_arrays['off'].copy(),columns=p['native_off_columns']),0)
        emergency=float(x[:,:ng][:,source['emergency_mask']].sum());assert emergency<=1e-6
        # Recompute price statistics directly from corrected original targets.
        target=np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz')['prices'];good=np.isfinite(target).all(axis=0)
        assert good.sum()==41
        mae=float(abs(y[:,:nz][:,good]-target[:,good]).mean());assert abs(mae-record['europe_mae'])<1e-9
        for j in np.flatnonzero(good):
            r=next(r for r in record['metrics']['zones'] if r['zone']==p['zones'][j]);assert abs(abs(y[:,j]-target[:,j]).mean()-r['mae_eur_mwh'])<1e-9
        certs[case]=dict(hours=8760,native_residual_mw=residual,emergency_mwh=emergency,europe_mae=mae,**maxima)
        quantities[case]=[];monthly[case]=[];diurnal[case]=[];q=np.clip(x[:,:ng],0,av)
        for ci,c in enumerate(sealed['countries']):
            ids=np.array(codes)==c;cap=(pv[:,ids]@maps[ids])*factor
            assert np.all(cap<=av+1e-5)
            point=np.divide(q*cap,av,out=np.zeros_like(q),where=av>0).sum(axis=1)
            lower=np.maximum(q-av+cap,0).sum(axis=1);upper=np.minimum(q,cap).sum(axis=1)
            assert np.all(lower<=point+1e-5) and np.all(point<=upper+1e-5)
            arrays[case+'_'+c]=np.stack([cap.sum(axis=1),point,lower,upper])
            row,m,h=diagnostics(c,cap.sum(axis=1),point,lower,upper,obs[:,ci],sealed['ember'])
            quantities[case].append(row);monthly[case]+=m;diurnal[case]+=h
        print(case,certs[case],flush=True)
    np.savez_compressed(OUT/'quantity-diagnostics.npz',**arrays)
    result=dict(status='all_17520_source_native_kkt_and_generation_replays_passed',auditor_sha256=digest(__file__),summary_sha256=digest(OUT/'summary.json'),inputs_sha256=digest(OUT/'inputs.json'),
        cases=certs,quantity_fields=['available_mw','illustrative_dispatch_mw','dispatch_lower_mw','dispatch_upper_mw'],quantities_sha256=digest(OUT/'quantity-diagnostics.npz'),
        quantities=quantities,monthly=monthly,diurnal=diurnal,seconds=time.perf_counter()-began)
    (OUT/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));audit()
