"""Independent source-column aggregation and every published country-cell replay.

No exporter imports or solver calls. Source allocation uses the retained allocate
implementation independently of the exporter's direct label accumulation.
"""
import argparse,csv,datetime as dt,gzip,json,logging,resource,signal,subprocess,time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,FAMILIES,CARRIER,PSR,EMBER,MONTH,allocate,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from compare_native_exchange_reference import CODES
from irena_capacity_reconciliation import extract


def audit(folder):
    began=time.perf_counter();s=json.loads((folder/'summary.json').read_text());public=ROOT/'public/research/country-explorer-2025'
    assert s['producer_sha256']==digest(ROOT/'tools/export_country_explorer_2025.py')
    for name,sha in s['source_hashes'].items():assert digest(ROOT/name)==sha
    assert s['manifest_sha256']==digest(public/'manifest.json') and s['aggregation_sha256']==digest(folder/'aggregation.npz')
    manifest=json.loads((public/'manifest.json').read_text());assert manifest['model']['id']=='joint-weekly-2025' and manifest['model']['accepted_baseline'] is False
    latest=ROOT/'data/bidding-zone-network-2025/weekly-bids-v1';ms=json.loads((latest/'summary.json').read_text());ma=json.loads((latest/'verification-v1/audit.json').read_text())
    assert ma['summary_sha256']==digest(latest/'summary.json')==s['model_summary_sha256'];assert digest(latest/'verification-v1/audit.json')==s['model_audit_sha256']
    case='inverse_joint-nordic_higher-w100';info=ms['annuals'][case];witness=latest/info['witness'];assert digest(witness)==info['witness_sha256']==s['witness_sha256']
    with np.load(witness) as z:x=z['values'];prices=z['row_duals'][:,:len(s['zones'])];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
    accepted=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1';layout=json.loads((accepted/'layout.json').read_text())
    with np.load(accepted/'development-targets.npz') as z:first=z['prices']
    with np.load(accepted/'evaluation-targets.npz') as z:observed_prices=np.concatenate([first,z['prices']])
    n,raw,fixed,*_=build();base,_=compile_global(n,raw,fixed,'bidding_zone')
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    tech=FAMILIES[:-1];countries=ms['countries'];zones=ms['zones'];assert s['countries']==countries and s['zones']==zones and s['technologies']==tech
    origin=[];fractions=[];groups=[]
    for ids,f in zip(layout['members'],layout['fractions'],strict=True):groups.append(list(range(len(origin),len(origin)+len(ids))));origin+=ids;fractions.extend([f]*len(ids))
    virtual=av[:,origin]*np.array(fractions);country_keys=[];zone_keys=[]
    for i in origin:
        g=n.generators.iloc[i];fuel=CARRIER[g.carrier];c=n.buses.loc[g.bus,'country'];z=base['buszone'][g.bus]
        country_keys.append(None if fuel=='emergency' else (c,fuel));zone_keys.append(None if fuel=='emergency' else (z,fuel))
    cp=allocate(virtual,x[:,:len(groups)],groups,country_keys,[(c,f) for c in countries for f in tech])[:3]
    zp=allocate(virtual,x[:,:len(groups)],groups,zone_keys,[(z,f) for z in zones for f in tech])[:3]
    reconstructed=[]
    for c,z in zip(cp,zp,strict=True):reconstructed.append(np.concatenate([c.reshape(8760,len(countries),13),z.reshape(8760,len(zones),13)],axis=1))
    for bus in n.buses.index:
        ci=countries.index(n.buses.loc[bus,'country']);zi=len(countries)+zones.index(base['buszone'][bus]);water=fixed[bus].values
        for array in reconstructed:array[:,ci,tech.index('reservoir')]+=water;array[:,zi,tech.index('reservoir')]+=water
    with np.load(folder/'aggregation.npz') as z:
        residual=max(float(abs(z[key]-array).max()) for key,array in zip(['model','lower','upper'],reconstructed,strict=True))
    assert residual<1e-6,residual
    # The independently audited annual country generation totals agree too.
    for month in range(1,13):
        expected=ms['outcomes'][case]['monthly_quantities'][month-1]['generation_point_twh']
        actual=reconstructed[0][MONTH==month,:len(countries),:].sum(axis=(0,2))/1e6
        np.testing.assert_allclose(actual,expected,rtol=1e-10,atol=1e-8)
    replay=json.loads((ROOT/'data/bidding-zone-network-2025/generation-mix-v1/observations-replay.json').read_text());observations={};source_meta={};start=dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)
    for area in replay['zones']:
        cols={};months=[]
        for m in area['monthly']:
            if m['status']!='raw_interval_energy_replayed':continue
            path=ROOT/f"data/carbon-pilot/map-2025/{area['zone']}/{m['month']:02d}.json";assert digest(path)==m['processed_sha256']
            months.append(dict(month=m['month'],processed_sha256=m['processed_sha256']))
            for row in json.loads(path.read_text()):
                t=int((dt.datetime.fromisoformat(row['start'].replace('Z','+00:00'))-start).total_seconds()/3600)
                for code,value in row['generation_mwh_by_type'].items():
                    if code not in cols:cols[code]=np.full(8760,np.nan)
                    assert np.isnan(cols[code][t]);cols[code][t]=value
        observations[area['zone']]=cols;source_meta[area['zone']]=(area['geographic_scope'],months)
    irena=json.loads(gzip.decompress((ROOT/'public/research/irena-capacity-2025/summary.json.gz').read_bytes()));pdf=ROOT/'data/pypsa-eur/irena-capacity-2026/capacity.pdf';assert digest(pdf)==irena['irena_pdf_sha256']
    text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-']).decode();names={r['provider_area']:r['country'] for r in irena['irena_rows']};original_irena=extract(text,names)
    assert original_irena==irena['irena_rows']
    with (ROOT/'data/pypsa-eur/ember-current-release/monthly.csv').open() as f:ember=list(csv.DictReader(f))
    national_scope=json.loads((ROOT/'data/bidding-zone-network-2025/generation-mix-v1/summary.json').read_text())['observation_coverage']
    max_error_generation=max_error_price=0.;price_zone_instances=0;generation_areas=0;source_columns=0
    for entry in manifest['countries']:
        c=entry['code'];path=public/entry['file'];assert digest(path)==entry['sha256']==s['files'][path.name]['sha256']
        payload=json.loads(gzip.decompress(path.read_bytes()));assert payload['country']==c and payload['hours']==8760 and payload['model_id']==manifest['model']['id']
        series={key:np.array([np.nan if v is None else v for v in values],float) for key,values in payload['series'].items()}
        assert all(len(v)==8760 for v in series.values())
        def check(ref,expected,scale):
            nonlocal max_error_generation,max_error_price
            value=series[ref]/scale;np.testing.assert_array_equal(np.isfinite(value),np.isfinite(expected));good=np.isfinite(expected)
            delta=float(abs(value[good]-expected[good]).max()) if good.any() else 0.
            assert delta<=.5/scale+1e-8,(c,ref,delta)
            if scale==10:max_error_generation=max(max_error_generation,delta)
            else:max_error_price=max(max_error_price,delta)
        required=next(r['expected_areas'] for r in national_scope if r['country']==c)
        if c=='GB':required=['GB']
        for area in payload['generation']:
            assert area['id'] in s['domains'];di=s['domains'].index(area['id']);national=area['id'].startswith('country:');z=area['id'].split(':')[1]
            req=required if national else [z];unavailable=not national and z in ['DE-LU','FR'];assert area['source_areas']==([] if unavailable else req)
            assert area['missing_source_areas']==[a for a in req if not observations.get(a)]
            for fi,fuel in enumerate(tech):
                for field,array in zip(['model','lower','upper'],reconstructed,strict=True):check(area[field][fi],array[:,di,fi],10)
                code=PSR[fuel]
                if not req or unavailable or any(code not in observations.get(a,{}) for a in req):expected=np.full(8760,np.nan)
                else:expected=np.array([observations[a][code] for a in req]).sum(axis=0)
                check(area['observed'][fi],expected,10);assert area['observed_hours'][fi]==int(np.isfinite(expected).sum())
            generation_areas+=1
        for rawarea in payload['source_generation']:
            z=rawarea['area'];expected=observations.get(z,{})
            assert set(rawarea['psr'])==set(expected)
            if z in source_meta:assert (rawarea['scope'],rawarea['provenance'])==source_meta[z]
            for code,ref in rawarea['psr'].items():check(ref,expected[code],10);source_columns+=1
        expected_prices=[z for z in zones if z[:2]==c]
        if c=='LU':expected_prices=['DE-LU']
        if c=='GB' and 'IE-SEM' in zones:expected_prices.append('IE-SEM')
        assert [p['zone'] for p in payload['prices']]==list(dict.fromkeys(expected_prices))==entry['price_zones']
        for row in payload['prices']:
            j=zones.index(row['zone']);p=prices[:,j];o=observed_prices[:,j];good=np.isfinite(o);check(row['model'],p,1000);check(row['observed'],o,1000);assert row['known_hours']==int(good.sum())
            if good.any():assert abs(row['mae']-float(abs(p[good]-o[good]).mean()))<1e-10 and abs(row['bias']-float((p[good]-o[good]).mean()))<1e-10
            else:assert row['mae'] is None and row['bias'] is None
            price_zone_instances+=1
        original_ember=[row for row in ember if row['Date'].startswith('2025-') and row['Area type'] in ['Country','Country or economy'] and row['Electricity source'] in EMBER and row['ISO 3 code']==CODES[c]]
        assert payload['ember_rows']==original_ember and payload['irena_rows']==[row for row in original_irena if row['country']==c]
        for row in payload['monthly']:
            ref=[r for r in original_ember if int(r['Date'][5:7])==row['month'] and r['Electricity source']==row['fuel']]
            observed=None if not ref or not ref[0]['Generation (TWh)'].strip() else float(ref[0]['Generation (TWh)']);assert row['observed_twh']==observed
            ids=[tech.index(f) for f in EMBER[row['fuel']]];model=float(reconstructed[0][MONTH==row['month'],countries.index(c),:][:,ids].sum()/1e6);assert abs(row['model_twh']-model)<1e-8
        print('Replayed country',c,'price zones',len(payload['prices']),flush=True)
    result=dict(status='all_country_hourly_source_dispatch_prices_and_original_provider_rows_replayed',export_summary_sha256=digest(folder/'summary.json'),manifest_sha256=digest(public/'manifest.json'),producer_sha256=s['producer_sha256'],auditor_sha256=digest(__file__),model_summary_sha256=s['model_summary_sha256'],model_audit_sha256=s['model_audit_sha256'],witness_sha256=s['witness_sha256'],countries=len(manifest['countries']),generation_areas=generation_areas,price_zone_instances=price_zone_instances,source_psr_columns=source_columns,hours=8760,maximum_allocation_difference_mw=residual,maximum_generation_rounding_mw=max_error_generation,maximum_price_rounding_eur_mwh=max_error_price,bytes=s['bytes'],files=s['files'],elapsed_seconds=time.perf_counter()-began)
    write=folder/'audit.json';write.write_text(json.dumps(result,indent=2)+'\n');(public/'verification.json').write_bytes(write.read_bytes())
    print(result['status'],flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1500);audit(a.folder)
