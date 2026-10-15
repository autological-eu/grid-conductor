"""Rebuild source columns and independently replay saved mix quantities and cohorts."""
import argparse
import csv
import json
import logging
import resource
import signal
import time
from pathlib import Path
import numpy as np

from generation_mix_2025 import ROOT,FAMILIES,CARRIER,EMBER,PSR,MONTH,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from audit_nve_hydro_diagnostics_2025 import physics
from compare_native_exchange_reference import CODES


def audit(folder,output):
    start=time.perf_counter();s=json.loads((folder/'summary.json').read_text())
    assert s['producer_sha256']==digest(ROOT/'tools/compare_dispatch_mix_2025.py')
    assert s['helper_sha256']==digest(ROOT/'tools/generation_mix_2025.py')
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    for name,sha in s['source_hashes'].items():assert digest(ROOT/name)==sha
    for name,key in [('quantities.npz','witness_sha256'),('observations-replay.json','observations_replay_sha256'),('design.json','design_sha256')]:assert digest(folder/name)==s[key]
    replay=json.loads((folder/'observations-replay.json').read_text());rawbase=ROOT/'data/carbon-pilot/entsoe/raw'
    for area in replay['zones']:
        for row in area['monthly']:
            if row['status']!='raw_interval_energy_replayed':continue
            month=row['month'];startday=f'2025{month:02d}01';endday=f'2025{month+1:02d}01' if month<12 else '20260101'
            zone={'DK1':'DK-DK1','DK2':'DK-DK2'}.get(area['zone'],area['zone'])
            raw=rawbase/f'{zone}-{startday}-{endday}.xml'
            assert digest(raw)==row['raw_sha256']
            assert digest(raw.with_suffix('.metadata.json'))==row['raw_metadata_sha256']
            processed=ROOT/f"data/carbon-pilot/map-2025/{area['zone']}/{month:02d}.json"
            assert digest(processed)==row['processed_sha256']
            assert digest(processed.with_name(f'{month:02d}.receipt.json'))==row['receipt_sha256']
    print('Source fingerprints verified; rebuilding fleet',flush=True)
    n,cost,fixed,mapping,original,old,hp=build();m,off=compile_global(n,cost,fixed,'bidding_zone')
    np.testing.assert_array_equal(n.snapshots.values,np.datetime64('2025-01-01')+np.arange(8760).astype('timedelta64[h]'))
    for key in ['objective','generators','stores']:np.testing.assert_array_equal(n.snapshot_weightings[key],1.)
    countries=s['countries'];families=FAMILIES;fuels=list(EMBER);fmap={f:k for k,fs in EMBER.items() for f in fs}
    base=ROOT/'data/bidding-zone-network-2025/annual-v7';groups={};keys=[]
    for j,(_,g) in enumerate(n.generators.iterrows()):
        groups.setdefault((m['buszone'][g.bus],cost[:,j].tobytes(),g.carrier=='emergency'),[]).append(j)
        keys.append((n.buses.loc[g.bus,'country'],CARRIER[g.carrier]))
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    with np.load(base/'annual.npz') as b,np.load(folder/'quantities.npz') as packed:
        # NpzFile decompresses on every lookup; load each sealed array exactly once.
        q={key:packed[key] for key in packed.files}
        assert b['bidding_zone_optimal'].all()
        x=b['bidding_zone_values'];primal=physics(n,m,x,m['load'],off.reset_index(drop=True).copy(),0)
        assert q['countries'].tolist()==countries and q['families'].tolist()==FAMILIES and q['ember_types'].tolist()==fuels
        expected={key:np.zeros_like(q[key]) for key in ['point','lower','upper','available','ember_point','ember_lower','ember_upper','country_point','country_lower','country_upper']}
        for k,ids in enumerate(groups.values()):
            total=av[:,ids].sum(axis=1);dispatch=np.clip(x[:,k],0.,total)
            for c in {keys[i][0] for i in ids}:
                j=countries.index(c);source=[i for i in ids if keys[i][0]==c and keys[i][1]!='emergency']
                cap=av[:,source].sum(axis=1)
                for name,value in [('country_point',np.divide(dispatch*cap,total,out=np.zeros(8760),where=total>0)),('country_lower',np.maximum(dispatch-(total-cap),0.)),('country_upper',np.minimum(dispatch,cap))]:expected[name][:,j]+=value
            for c,f in {keys[i] for i in ids}:
                j=countries.index(c);findex=families.index(f);source=[i for i in ids if keys[i]==(c,f)];cap=av[:,source].sum(axis=1)
                for name,value in [('point',np.divide(dispatch*cap,total,out=np.zeros(8760),where=total>0)),('lower',np.maximum(dispatch-(total-cap),0.)),('upper',np.minimum(dispatch,cap)),('available',cap)]:expected[name][:,j,findex]+=value
            for c,fuel in {(keys[i][0],fmap[keys[i][1]]) for i in ids if keys[i][1]!='emergency'}:
                j=countries.index(c);findex=fuels.index(fuel);source=[i for i in ids if keys[i][0]==c and keys[i][1]!='emergency' and fmap[keys[i][1]]==fuel];cap=av[:,source].sum(axis=1)
                for name,value in [('ember_point',np.divide(dispatch*cap,total,out=np.zeros(8760),where=total>0)),('ember_lower',np.maximum(dispatch-(total-cap),0.)),('ember_upper',np.minimum(dispatch,cap))]:expected[name][:,j,findex]+=value
        load=n.get_switchable_as_dense('Load','p_set')
        for j,c in enumerate(countries):
            buses=n.buses.index[n.buses.country==c];water=fixed[buses].sum(axis=1).to_numpy()
            demand=load[n.loads.index[n.loads.bus.isin(buses)]].sum(axis=1).to_numpy()
            np.testing.assert_allclose(water,q['fixed_reservoir'][:,j],atol=1e-7,rtol=1e-12)
            np.testing.assert_allclose(demand,q['demand'][:,j],atol=1e-7,rtol=1e-12)
            for key in ['point','lower','upper']:expected[key][:,j,families.index('reservoir')]+=water
            for key in ['ember_point','ember_lower','ember_upper']:expected[key][:,j,fuels.index('Hydro')]+=water
            for key in ['country_point','country_lower','country_upper']:expected[key][:,j]+=water
        errors={key:float(abs(value-q[key]).max()) for key,value in expected.items()}
        assert max(errors.values())<1e-6
        print('Source allocations and bounds replayed',flush=True)
        # Re-read processed observations by type, requiring every constituent area.
        areas={r['zone']:r for r in replay['zones']};cache={}
        for country in s['observation_coverage']:
            c=country['country'];j=countries.index(c);refs=country['expected_areas'];vectors=[]
            for z in refs:
                if z not in cache:
                    v=np.full((8760,len(families)+3),np.nan)
                    for row in areas.get(z,{}).get('monthly',[]):
                        if row['status']!='raw_interval_energy_replayed':continue
                        records=json.loads((ROOT/f"data/carbon-pilot/map-2025/{z}/{row['month']:02d}.json").read_text())
                        offset=int(np.flatnonzero(MONTH==row['month'])[0])
                        for i,record in enumerate(records):
                            assert record['start']==str(np.datetime64('2025-01-01T00:00:00')+np.timedelta64(offset+i,'h'))+'Z'
                            for family,psr in PSR.items():
                                if psr in record['generation_mwh_by_type']:v[offset+i,families.index(family)]=record['generation_mwh_by_type'][psr]
                            for col,value in [(-3,record['primary_generation_mwh']),(-2,record['generation_mwh_by_type'].get('B10')),(-1,record['generation_mwh_by_type'].get('B25'))]:
                                if value is not None:v[offset+i,col]=value
                    cache[z]=v
                vectors.append(cache[z])
            expected_obs=np.sum(vectors,axis=0) if vectors else np.full((8760,len(families)+3),np.nan)
            np.testing.assert_allclose(expected_obs,q['observed'][:,j],atol=0,rtol=0,equal_nan=True)
        for row in s['hourly']:
            j=countries.index(row['country']);f=row['technology']
            if f=='reported_primary_total':p,lo,hi,obs=q['country_point'][:,j],q['country_lower'][:,j],q['country_upper'][:,j],q['observed'][:,j,-3]
            else:
                k=families.index(f);p,lo,hi,obs=[q[key][:,j,k] for key in ['point','lower','upper','observed']]
            for item,mask in [(row['year'],np.ones(8760,bool)),*[(v,MONTH==v['month']) for v in row['monthly']]]:
                known=mask&np.isfinite(obs);assert item['known_hours']==int(known.sum()) and item['expected_hours']==int(mask.sum())
                if not known.any():continue
                error=p[known]-obs[known]
                values=dict(model_twh=p[known].sum()/1e6,observed_twh=obs[known].sum()/1e6,lower_twh=lo[known].sum()/1e6,upper_twh=hi[known].sum()/1e6,bias_mw=error.mean(),mae_mw=abs(error).mean(),rmse_mw=np.sqrt((error**2).mean()))
                for key,value in values.items():assert abs(item[key]-value)<1e-7,(f,key)
                corr=float(np.corrcoef(p[known],obs[known])[0,1]) if known.sum()>1 and p[known].std()>1e-8 and obs[known].std()>1e-8 else None
                assert item['correlation']==corr
                assert item['outside_allocation_range_hours']==int(((obs[known]<lo[known]-1)|(obs[known]>hi[known]+1)).sum())
        # Independently parse the national reference, preserving missing and explicit zero.
        bank={}
        with (ROOT/'data/pypsa-eur/ember-current-release/monthly.csv').open() as f:
            for r in csv.DictReader(f):
                if r['Date'].startswith('2025-') and r['Area type'] in ['Country','Country or economy'] and r['Generation (TWh)'].strip():
                    bank[(r['ISO 3 code'],r['Electricity source'],int(r['Date'][5:7]))]=float(r['Generation (TWh)'])
        for row in s['annual']:
            j=countries.index(row['country']);k=fuels.index(row['technology']);refs=[]
            for item in row['monthly']:
                month=item['month'];mask=MONTH==month;ref=bank.get((CODES.get(row['country']),row['technology'],month));assert item['ember_twh']==ref;refs.append(ref)
                for name,key in [('model_twh','ember_point'),('lower_twh','ember_lower'),('upper_twh','ember_upper')]:assert abs(q[key][mask,j,k].sum()/1e6-item[name])<1e-8
                assert item['difference_twh']==(None if ref is None else item['model_twh']-ref)
                assert item['outside_range_twh']==(None if ref is None else max(item['lower_twh']-ref,ref-item['upper_twh'],0.))
            ref=sum(refs) if all(v is not None for v in refs) else None
            assert row['ember_twh']==ref and row['reference_months']==sum(v is not None for v in refs)
            for name,key in [('model_twh','ember_point'),('lower_twh','ember_lower'),('upper_twh','ember_upper')]:assert abs(q[key][:,j,k].sum()/1e6-row[name])<1e-8
            assert row['difference_twh']==(None if ref is None else row['model_twh']-ref)
            assert row['outside_range_twh']==(None if ref is None else max(row['lower_twh']-ref,ref-row['upper_twh'],0.))
        for row in s['energy']:
            j=countries.index(row['country']);code=CODES.get(row['country'])
            for item in row['monthly']:
                mask=MONTH==item['month'];d=q['demand'][mask,j].sum()/1e6;g=q['country_point'][mask,j].sum()/1e6
                assert abs(item['model_demand_twh']-d)<1e-8 and abs(item['model_implied_net_export_twh']-(g-d))<1e-8
                assert item['ember_demand_twh']==bank.get((code,'Demand',item['month']))
                net=bank.get((code,'Net imports',item['month']));assert item['ember_net_export_twh']==(None if net is None else -net)
                for name, key in [('lower_net_export_twh','country_lower'),('upper_net_export_twh','country_upper')]:assert abs(item[name]-(q[key][mask,j].sum()/1e6-d))<1e-8
            for key in ['model_demand_twh','ember_demand_twh','model_implied_net_export_twh','ember_net_export_twh','lower_net_export_twh','upper_net_export_twh']:
                vals=[m[key] for m in row['monthly']];expected_value=sum(vals) if all(v is not None for v in vals) else None;assert row[key]==expected_value
        for row in s['country_totals']:
            j=countries.index(row['country']);refs=[bank.get((CODES.get(row['country']),'Total generation',m)) for m in range(1,13)]
            ref=sum(refs) if all(v is not None for v in refs) else None;assert row['ember_total_twh']==ref
            for name,key in [('model_total_twh','country_point'),('lower_twh','country_lower'),('upper_twh','country_upper')]:assert abs(row[name]-q[key][:,j].sum()/1e6)<1e-8
            assert row['difference_twh']==(None if ref is None else row['model_total_twh']-ref)
        for row in s['annual']:
            country=next(r for r in s['country_totals'] if r['country']==row['country'])
            assert row['model_share_pct']==(100*row['model_twh']/country['model_total_twh'] if country['model_total_twh']>0 else None)
            ref=country['ember_total_twh'];assert row['ember_share_pct']==(100*row['ember_twh']/ref if row['ember_twh'] is not None and ref and ref>0 else None)
        for row in s['storage_observed']:
            j=countries.index(row['country']);pumped=q['observed'][:,j,-2];battery=q['observed'][:,j,-1]
            assert row['pumped_discharge_known_hours']==int(np.isfinite(pumped).sum())
            assert row['battery_discharge_known_hours']==int(np.isfinite(battery).sum())
            assert row['pumped_discharge_on_known_hours_twh']==(float(np.nansum(pumped)/1e6) if np.isfinite(pumped).any() else None)
        closure=float(abs(q['country_point'].sum(axis=1)-q['demand'].sum(axis=1)-x[:,m['ng']:m['ng']+m['nl']]@(1-n.links.efficiency.to_numpy())).max());assert closure<1e-4
    result=dict(status='source_dispatch_allocation_observation_and_energy_replay_passed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),
        countries=len(countries),annual_country_fuel_rows=len(s['annual']),maximum_allocation_error_mw=max(errors.values()),maximum_network_residual_mw=primal,
        maximum_global_energy_closure_mw=closure,elapsed_seconds=time.perf_counter()-start,
        limit='Tie allocations and national/reporting taxonomies remain conditional; no accepted mix accuracy or observed branch-flow validation')
    (output/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    output=a.out or a.folder/'verification-v2';output.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1500);audit(a.folder,output)
