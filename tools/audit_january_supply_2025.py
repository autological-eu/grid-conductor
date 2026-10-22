"""Independent raw-source, solar-clock, country-capacity and LP witness replay.

Does not import the reconciliation producer or its LP validation helper.
"""
import datetime as dt
import gzip
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import xarray as xr
from scipy.sparse import load_npz
from generation_mix_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/january-supply-balance-v1'
BASE=ROOT/'data/bidding-zone-network-2025/thermal-event-v1'
GRID=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025'
RUN=OUT/'clearing-v1'


def audit():
    collection=json.loads((OUT/'collection.json').read_text());p=json.loads((OUT/'reconciliation-inputs.json').read_text());summary=json.loads((RUN/'summary.json').read_text());meta=json.loads((BASE/'inputs-protocol-v2.json').read_text());source=dict(np.load(BASE/'inputs.npz'));rec=dict(np.load(OUT/'reconciliation-inputs.npz'));A=load_npz(BASE/'network.npz')
    assert collection['producer_sha256']==digest(ROOT/'tools/january_supply_sources_2025.py')
    assert p['producer_sha256']==summary['producer_sha256']==digest(ROOT/'tools/january_supply_balance_2025.py') and summary['input_summary_sha256']==digest(OUT/'reconciliation-inputs.json')
    assert summary['helper_sha256']==digest(ROOT/'tools/thermal_event_model_2025.py') and summary['validation_helper_sha256']==digest(ROOT/'tools/run_thermal_event_2025.py')
    assert summary['design']==json.loads((ROOT/'config/january-supply-balance-2025.json').read_text())
    for file,h in p['source_hashes'].items():assert digest(ROOT/file)==h
    for file,h in p['files'].items():assert digest(OUT/file)==h
    for file,h in summary['files'].items():assert digest(RUN/file)==h
    normalized={};start=int(dt.datetime(2025,1,13,tzinfo=dt.timezone.utc).timestamp()*1000);end=start+240*3600000
    configuration=json.loads((OUT/'configuration.json').read_text());blocks=[]
    def walk(x):
        if isinstance(x,dict):
            if 'data_id' in x:blocks.append(x)
            for value in x.values():walk(value)
        elif isinstance(x,list):
            for value in x:walk(value)
    walk(configuration)
    cr=collection['configuration_receipt'];assert digest(OUT/cr['file'])==cr['sha256'] and json.loads((OUT/cr['file']).read_text())==configuration
    for name,receipts in collection['sources'].items():
        data=json.loads((OUT/(name+'.json')).read_text());observed={};is_capacity=name.startswith('installed_')
        for r in receipts:
            assert digest(OUT/r['file'])==r['sha256'];raw=json.loads((OUT/r['file']).read_text())
            if 'series' not in raw:continue
            for stamp,value in raw['series']:
                # Match normalization, then separately select reported-year capacity.
                lo=int(dt.datetime(2024,1,1,tzinfo=dt.timezone.utc).timestamp()*1000) if is_capacity else start
                hi=int(dt.datetime(2026,1,1,tzinfo=dt.timezone.utc).timestamp()*1000) if is_capacity else end
                if lo<=stamp<hi:assert stamp not in observed or observed[stamp]==value;observed[stamp]=value
        assert sorted(observed.items())==[tuple(v) for v in data['samples']]
        unit='VD-Einheit.MW' if is_capacity else 'VD-Einheit.MWh'
        assert any(b['data_id']==data['filter'] and b['unit']==unit and 'DE' in b['region'] for b in blocks)
        if not is_capacity:
            step=900000 if data['resolution']=='quarterhour' else 3600000;assert sorted(observed)==list(range(start,end,step)) and all(v is not None and v>=0 for v in observed.values())
        normalized[name]=observed
    unit_errors={}
    for name in ['forecast_solar','actual_load']:
        quarter=normalized[name+'-quarter'];hour=normalized[name];error=max(abs(hour[t]-sum(quarter[t+k*900000] for k in range(4))) for t in hour);assert error<=.051;unit_errors[name]=error
    combined=max(abs(normalized['forecast_wind_solar'][t]-sum(normalized[n][t] for n in ['forecast_solar','forecast_onshore','forecast_offshore'])) for t in normalized['forecast_wind_solar']);assert combined<=.051
    # Recover pooling coefficients independently from original member records.
    allocation=json.loads((ROOT/'data/bidding-zone-network-2025/annual-v7/mapping.json').read_text())['allocation'];layout=json.loads((ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json').read_text());irena=json.loads(gzip.decompress((ROOT/'public/research/irena-capacity-2025/summary.json.gz').read_bytes()))['irena_rows']
    with xr.open_dataset(GRID/'networks/base_s_128_elec_.nc') as ds:
        names=list(ds.generators_i.values.astype(str));nom=ds.generators_p_nom.values;fuel=ds.generators_carrier.values.astype(str);country_map=dict(zip(ds.buses_i.values,ds.buses_country.values));country=np.array([country_map[b] for b in ds.generators_bus.values]);lookup={name:i for i,name in enumerate(names)};refined=[]
        for row in allocation:
            if row['component']=='Generator':refined.extend((lookup.get(row['name']),v) for v in row['shares'].values() if v>0)
        expected=np.zeros((len(names),meta['ng']))
        for k,members in enumerate(layout['members']):
            for i in members:
                if i<len(refined) and refined[i][0] is not None:expected[refined[i][0],k]+=refined[i][1]*layout['fractions'][k]
        np.testing.assert_allclose(load_npz(OUT/'pooling.npz').toarray(),expected,rtol=0,atol=1e-12)
        a,b=meta['start_hour'],meta['stop_hour'];clock=ds.snapshots_snapshot.values;rows={t:i for i,t in enumerate(clock)};target=clock[a:b];right=[rows[t+np.timedelta64(1,'h')] for t in target];assert right==p['source_hours'] and list(range(a,b))==p['destination_hours']
        pv_ids=np.flatnonzero(np.isin(fuel,['solar','solar-hsat']));raw=ds.generators_t_p_max_pu.values;raw_names=list(ds.generators_t_p_max_pu_i.values);original=np.zeros((240,len(names)));aligned=original.copy()
        for technology in ['solar','solar-hsat']:
            with xr.open_dataset(GRID/f'profile_128_{technology}.nc') as profile:
                assert profile.attrs['module']=='era5' and np.array_equal(clock,profile.time.values)
                for j in np.flatnonzero(fuel==technology):
                    bus,bin=names[j].removesuffix(' '+technology).rsplit(' ',1);profile_values=profile.profile.sel(bus=bus,bin=int(bin)).isel(year=0).values;np.testing.assert_array_equal(profile_values,raw[:,raw_names.index(names[j])])
                    original[:,j]=profile_values[a:b]*nom[j];aligned[:,j]=profile_values[right]*nom[j]
        for c in np.unique(country[pv_ids]):
            ids=np.flatnonzero((country==c)&np.isin(fuel,['solar','solar-hsat']));r=next((v for v in irena if v['country']==c and v['technology']=='Solar photovoltaic'),None)
            if r:
                mw=r['capacity_2024']['mw']+(r['capacity_2025']['mw']-r['capacity_2024']['mw'])*np.arange(a,b)/8760
                original[:,ids]*=(mw/nom[ids].sum())[:,None];aligned[:,ids]*=(mw/nom[ids].sum())[:,None]
        old=original@expected;new=aligned@expected
        np.testing.assert_allclose(old,rec['solar_original'],rtol=0,atol=1e-7);np.testing.assert_allclose(new,rec['solar_aligned'],rtol=0,atol=1e-7)
        np.testing.assert_allclose(original[:,country=='DE'].sum(axis=1),rec['de_solar'],rtol=0,atol=1e-7);np.testing.assert_allclose(aligned[:,country=='DE'].sum(axis=1),rec['de_solar_aligned'],rtol=0,atol=1e-7)
        thermal=np.array([(nom*((country=='DE')&np.isin(fuel,fuels)))@expected for fuels in [['coal'],['lignite'],['CCGT','OCGT']]]);np.testing.assert_allclose(thermal,rec['thermal'],rtol=0,atol=1e-7)
        for row,vector in zip(p['capacity'],thermal):
            reported=[v for t,v in normalized['installed_'+row['technology']].items() if dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).astimezone(ZoneInfo('Europe/Berlin')).year==2025];assert len(reported)==1 and reported[0]==row['reported_2025_mw'];assert abs(vector.sum()-row['model_mw'])<1e-7 and abs(row['factor']-reported[0]/vector.sum())<1e-12
    wind_ids=np.flatnonzero((country=='DE')&np.isin(fuel,['onwind','offwind-ac','offwind-dc','offwind-float']))
    wind_row=next(r for r in irena if r['country']=='DE' and r['technology']=='Wind energy')
    wind_factor=(wind_row['capacity_2024']['mw']+(wind_row['capacity_2025']['mw']-wind_row['capacity_2024']['mw'])*np.arange(a,b)/8760)/nom[wind_ids].sum()
    diagnostics={}
    for key,fuels in [('onshore',['onwind']),('offshore',['offwind-ac','offwind-dc','offwind-float'])]:
        ids=np.flatnonzero((country=='DE')&np.isin(fuel,fuels));diagnostics[key]=np.sum(raw[a:b][:,[raw_names.index(names[i]) for i in ids]]*nom[ids],axis=1)*wind_factor
    with xr.open_dataset(GRID/'networks/base_s_128_elec_.nc') as ds:
        load_ids=[i for i,bus in enumerate(ds.loads_bus.values) if country_map[bus]=='DE'];diagnostics['model_load']=ds.loads_t_p_set.isel(snapshots=slice(a,b)).values[:,load_ids].sum(axis=1)
    np.savez_compressed(RUN/'source-diagnostics.npz',**diagnostics)
    certificates={};max_native=max_gap=max_comp=0.;ng,nz,nl=meta['ng'],meta['nz'],meta['nl'];cost=np.c_[source['cost'],np.zeros((240,nl+nz))];clo=np.c_[np.zeros((240,ng)),source['link_min'],np.full((240,nz),-np.inf)];rlo=np.c_[source['load'],source['island_rhs'],-source['ratings']-source['flow']];rhi=np.c_[source['load'],source['island_rhs'],source['ratings']-source['flow']];eligible=np.isfinite(source['observed']).all(axis=0)
    for name,record in summary['cases'].items():
        data=dict(np.load(RUN/(name+'.npz')));x,y,rc=data['values'],data['row_duals'],data['col_duals'];av=source['availability'].copy()
        if name in ['solar_interval','solar_capacity']:av+=new-old
        if name in ['de_capacity','solar_capacity']:
            for vector,row in zip(thermal,p['capacity']):av+=(row['factor']-1)*vector
        np.testing.assert_allclose(data['availability'],av,rtol=0,atol=1e-7);chi=np.c_[av,source['link_max'],np.full((240,nz),np.inf)];ax=(A@x.T).T;primal=max(np.maximum(clo-x,0).max(),np.maximum(x-chi,0).max(),np.maximum(rlo-ax,0).max(),np.maximum(ax-rhi,0).max());stationarity=abs(cost-(A.T@y.T).T-rc).max();dual=np.zeros(240);comp=0.
        for bound,part,value in [(rlo,np.maximum(y,0),ax),(rhi,np.minimum(y,0),ax),(clo,np.maximum(rc,0),x),(chi,np.minimum(rc,0),x)]:
            finite=np.isfinite(bound);assert abs(part[~finite]).max(initial=0)<1e-6;dual+=np.sum(np.where(finite,bound,0)*part,axis=1);comp=max(comp,float(abs(part[finite]*(value[finite]-bound[finite])).max(initial=0)))
        obj=data['objectives'];gap=abs(obj-dual).max();objective_error=abs(np.sum(x*cost,axis=1)-obj).max();assert primal<=1e-4 and stationarity<1e-5 and gap<.05 and comp<.05 and objective_error<.05,(name,primal,stationarity,gap,comp,objective_error)
        if name=='control':np.testing.assert_allclose(obj,source['baseline_objectives'],rtol=0,atol=.05)
        score=float(abs(y[48:216,:nz][:,eligible]-source['observed'][48:216][:,eligible]).mean());assert abs(score-record['mae_eur_mwh'])<1e-10;emergency=float(x[:,np.flatnonzero(source['emergency_mask'])].sum());assert abs(emergency-record['emergency_mwh'])<1e-7 and record['acceptable_supply']==bool(emergency<1e-6)
        certificates[name]=dict(hours=240,primal_mw=float(primal),stationarity_eur_mwh=float(stationarity),duality_gap_eur=float(gap),complementarity_eur=comp,emergency_mwh=emergency);max_native=max(max_native,float(primal));max_gap=max(max_gap,float(gap));max_comp=max(max_comp,comp)
    result=dict(normalized_sha256={name:digest(OUT/(name+'.json')) for name in normalized},collection_sha256=digest(OUT/'collection.json'),diagnostics_sha256=digest(RUN/'source-diagnostics.npz'),status='sources_and_all_four_network_cases_replayed',auditor_sha256=digest(Path(__file__)),summary_sha256=digest(RUN/'summary.json'),input_summary_sha256=digest(OUT/'reconciliation-inputs.json'),configuration_sha256=digest(OUT/'configuration.json'),unit_aggregation_errors_mwh=unit_errors,forecast_component_error_mwh=combined,cases=certificates,maximum_native_residual_mw=max_native,maximum_duality_gap_eur=max_gap,maximum_complementarity_eur=max_comp,forecast_asof_auction_verified=False,dated_outage_verification_available=False)
    (RUN/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':audit()
