"""Publish compact, lazy country comparisons from the latest audited annual witness.

No model solve, bid fit, capacity change or observation interpolation. Exact
source rows stay distinct from rounded hourly comparison data.
"""
import argparse,csv,gzip,hashlib,json,logging,resource,signal,time
from pathlib import Path
import numpy as np
import pycountry
from generation_mix_2025 import ROOT,FAMILIES,CARRIER,PSR,EMBER,MONTH,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets
from bid_calibration_2025 import immutable_hashes
from compare_native_exchange_reference import CODES

LATEST=ROOT/'data/bidding-zone-network-2025/weekly-bids-v1'
ACCEPTED=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1'
CASE='inverse_joint-nordic_higher-w100'
MODEL_ID='joint-weekly-2025'
PUBLIC=ROOT/'public/research/country-explorer-2025'
TECH=FAMILIES[:-1]
NAMES=['Onshore wind','Offshore wind','Solar','Nuclear','Run-of-river hydro','Reservoir hydro','Gas','Hard coal','Lignite','Oil','Biomass','Waste','Geothermal']


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def encoded(values,scale):
    return [None if not np.isfinite(v) else int(round(float(v)*scale)) for v in values]


def price_zones(country,zones):
    # Shared commercial areas are shown in both countries, never summed as national prices.
    wanted=[z for z in zones if z[:2]==country]
    if country=='LU':wanted=['DE-LU']
    if country=='GB' and 'IE-SEM' in zones:wanted+=['IE-SEM']
    return list(dict.fromkeys(wanted))


def source_observations(replay,sources):
    result={};meta={}
    for area in replay['zones']:
        zone=area['zone'];cols={};records=[]
        for month in area['monthly']:
            if month['status']!='raw_interval_energy_replayed':continue
            path=ROOT/f"data/carbon-pilot/map-2025/{zone}/{month['month']:02d}.json"
            assert digest(path)==month['processed_sha256'];sources[str(path.relative_to(ROOT))]=digest(path)
            records.append(dict(month=month['month'],processed_sha256=month['processed_sha256']))
            for row in json.loads(path.read_text()):
                t=int((np.datetime64(row['start'].removesuffix('Z'))-np.datetime64('2025-01-01T00')).astype('timedelta64[h]').astype(int))
                assert 0<=t<8760
                for code,value in row['generation_mwh_by_type'].items():
                    if code not in cols:cols[code]=np.full(8760,np.nan)
                    assert np.isnan(cols[code][t]),('Duplicate hourly source cell',zone,code,t)
                    cols[code][t]=value
        result[zone]=cols;meta[zone]=dict(scope=area['geographic_scope'],months=records)
    return result,meta


def run(out):
    began=time.perf_counter();out.mkdir(parents=True,exist_ok=False);PUBLIC.mkdir(parents=True,exist_ok=True)
    assert not (PUBLIC/'manifest.json').exists(),'Preserve published explorer; use explicit regeneration after review'
    s=json.loads((LATEST/'summary.json').read_text());a=json.loads((LATEST/'verification-v1/audit.json').read_text())
    assert a['summary_sha256']==digest(LATEST/'summary.json') and len(a['certificates'])==2
    for name,sha in s['source_hashes'].items():assert digest(ROOT/name)==sha
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    info=s['annuals'][CASE];witness=LATEST/info['witness'];assert digest(witness)==info['witness_sha256']
    with np.load(witness) as z:
        values=z['values'];prices=z['row_duals'][:,:len(s['zones'])];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
    sources={str(p.relative_to(ROOT)):digest(p) for p in [LATEST/'summary.json',LATEST/'verification-v1/audit.json',witness,ACCEPTED/'summary.json',ACCEPTED/'layout.json',ACCEPTED/'development-targets.npz',ACCEPTED/'evaluation-targets.npz']}
    old=json.loads((ACCEPTED/'summary.json').read_text());layout=json.loads((ACCEPTED/'layout.json').read_text());zones=s['zones'];countries=s['countries']
    with np.load(ACCEPTED/'development-targets.npz') as z:observed_first=z['prices']
    with np.load(ACCEPTED/'evaluation-targets.npz') as z:observed_prices=np.r_[observed_first,z['prices']]
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    assert immutable_hashes(base,flow)==old['original_physical_inputs']
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    domains=['country:'+c for c in countries]+['zone:'+z for z in zones];shape=(8760,len(domains),len(TECH));point=np.zeros(shape);lower=np.zeros(shape);upper=np.zeros(shape)
    labels=[]
    for _,g in n.generators.iterrows():labels.append((str(n.buses.loc[g.bus,'country']),str(base['buszone'][g.bus]),CARRIER[g.carrier]))
    for j,(ids,fraction) in enumerate(zip(layout['members'],layout['fractions'],strict=True)):
        total=av[:,ids].sum(axis=1)*fraction;q=values[:,j]
        assert np.min(q)>=-1e-4 and np.max(q-total)<=1e-4
        q=np.clip(q,0,total)
        for mode,col in [('country',0),('zone',1)]:
            for d,fuel in {(labels[i][col],labels[i][2]) for i in ids if labels[i][2]!='emergency'}:
                selected=[i for i in ids if labels[i][col]==d and labels[i][2]==fuel]
                cap=av[:,selected].sum(axis=1)*fraction;di=domains.index(mode+':'+d);fi=TECH.index(fuel)
                point[:,di,fi]+=np.divide(q*cap,total,out=np.zeros(8760),where=total>0)
                lower[:,di,fi]+=np.maximum(q-total+cap,0);upper[:,di,fi]+=np.minimum(q,cap)
    for bus in n.buses.index:
        country=str(n.buses.loc[bus,'country']);zone=str(base['buszone'][bus]);v=fixed[bus].values
        for domain in ['country:'+country,'zone:'+zone]:
            for target in [point,lower,upper]:target[:,domains.index(domain),TECH.index('reservoir')]+=v
    mix=ROOT/'data/bidding-zone-network-2025/generation-mix-v1';replay=json.loads((mix/'observations-replay.json').read_text());ms=json.loads((mix/'summary.json').read_text())
    assert digest(mix/'observations-replay.json')==ms['observations_replay_sha256']
    ma=json.loads((mix/'verification-v2/audit.json').read_text());assert ma['summary_sha256']==digest(mix/'summary.json')
    for p in [mix/'summary.json',mix/'verification-v2/audit.json',mix/'observations-replay.json']:sources[str(p.relative_to(ROOT))]=digest(p)
    observed,source_meta=source_observations(replay,sources)
    irena_path=ROOT/'public/research/irena-capacity-2025/summary.json.gz';irena=json.loads(gzip.decompress(irena_path.read_bytes()))
    pdf=ROOT/'data/pypsa-eur/irena-capacity-2026/capacity.pdf';assert digest(pdf)==irena['irena_pdf_sha256']
    ember=ROOT/'data/pypsa-eur/ember-current-release/monthly.csv';er=ROOT/'data/pypsa-eur/ember-current-release/receipt.json';ember_receipt=json.loads(er.read_text());assert digest(ember)==ember_receipt['sha256']
    for p in [irena_path,pdf,ember,er]:sources[str(p.relative_to(ROOT))]=digest(p)
    raw_ember={c:[] for c in countries}
    with ember.open() as f:
        for row in csv.DictReader(f):
            if not row['Date'].startswith('2025-') or row['Area type'] not in ['Country','Country or economy'] or row['Electricity source'] not in EMBER:continue
            for c in countries:
                if row['ISO 3 code']==CODES[c]:raw_ember[c].append(row)
    country_areas={c:next(v['expected_areas'] for v in ms['observation_coverage'] if v['country']==c) for c in countries}
    # IE-SEM is shared with Ireland: never manufacture a UK national generation sum.
    country_areas['GB']=['GB']
    files={};entries=[];maximum_rounding_error=0.
    for country in countries:
        bank={};hashes={}
        def ref(v,scale=10):
            nonlocal maximum_rounding_error
            a=encoded(v,scale);rawbytes=json.dumps(a,separators=(',',':'),allow_nan=False).encode();h=hashlib.sha256(rawbytes).hexdigest()
            if h not in hashes:
                key='s'+str(len(bank));hashes[h]=key;bank[key]=a
            decoded=np.array([np.nan if q is None else q/scale for q in a]);good=np.isfinite(v)
            if good.any():maximum_rounding_error=max(maximum_rounding_error,float(abs(decoded[good]-v[good]).max()))
            return hashes[h]
        areas=[];wanted=['country:'+country]+['zone:'+z for z in zones if z[:2]==country]
        if country=='LU':wanted+=['zone:DE-LU']
        for domain in wanted:
            di=domains.index(domain);national=domain.startswith('country:');area=domain.split(':',1)[1]
            required=country_areas[country] if national else [area]
            scope_note='National model membership uses original source-country labels; zonal membership uses the retained geographical allocation.'
            # A44 DE-LU is a price zone; cached A75 is Germany-only. FR A75 is national.
            unavailable_zonal=(not national and area in ['DE-LU','FR'])
            observed_cols=[]
            for fuel in TECH:
                code=PSR[fuel]
                if not required or unavailable_zonal or any(code not in observed.get(z,{}) for z in required):v=np.full(8760,np.nan)
                else:v=np.stack([observed[z][code] for z in required]).sum(axis=0)
                observed_cols.append(v)
            observed_array=np.column_stack(observed_cols)
            areas.append(dict(id=domain,label='Country total' if national else area,source_areas=[] if unavailable_zonal else required,
                scope_note=scope_note+(' No comparable zonal generation series: the source is national.' if unavailable_zonal else ''),
                missing_source_areas=[z for z in required if not observed.get(z)],
                model=[ref(point[:,di,f]) for f in range(len(TECH))],lower=[ref(lower[:,di,f]) for f in range(len(TECH))],upper=[ref(upper[:,di,f]) for f in range(len(TECH))],observed=[ref(observed_array[:,f]) for f in range(len(TECH))],
                observed_hours=np.isfinite(observed_array).sum(axis=0).tolist()))
        source_areas=list(dict.fromkeys(country_areas[country]+[z for z in zones if z[:2]==country]))
        raw_sources=[dict(area=z,scope=source_meta.get(z,{}).get('scope','No cached generation source'),provenance=source_meta.get(z,{}).get('months',[]),psr={code:ref(v) for code,v in observed.get(z,{}).items()}) for z in source_areas]
        price_rows=[]
        for z in price_zones(country,zones):
            j=zones.index(z);p=prices[:,j];o=observed_prices[:,j];good=np.isfinite(o)
            price_rows.append(dict(zone=z,scope='Shared Germany–Luxembourg price area' if z=='DE-LU' else 'Shared Ireland–Northern Ireland price area' if z=='IE-SEM' else 'Modeled market area; retained provider geography',model=ref(p,1000),observed=ref(o,1000),known_hours=int(good.sum()),
                mae=float(abs(p[good]-o[good]).mean()) if good.any() else None,bias=float((p[good]-o[good]).mean()) if good.any() else None,
                correlation=float(np.corrcoef(p[good],o[good])[0,1]) if good.sum()>1 and p[good].std()>1e-8 and o[good].std()>1e-8 else None))
        name='Kosovo' if country=='XK' else pycountry.countries.get(alpha_2=country).name
        di=domains.index('country:'+country);monthly=[]
        for month in range(1,13):
            mask=MONTH==month
            for fuel,children in EMBER.items():
                ids=[TECH.index(f) for f in children];refs=[r for r in raw_ember[country] if int(r['Date'][5:7])==month and r['Electricity source']==fuel]
                assert len(refs)<=1
                observed_twh=None if not refs or not refs[0]['Generation (TWh)'].strip() else float(refs[0]['Generation (TWh)'])
                # Bounds must be computed for the whole fuel label, not summed child-label extrema.
                monthly.append(dict(month=month,fuel=fuel,observed_twh=observed_twh,model_twh=float(point[mask,di][:,ids].sum()/1e6)))
        payload=dict(schema_version=1,country=country,name=name,model_id=MODEL_ID,hours=8760,series=bank,generation=areas,source_generation=raw_sources,prices=price_rows,
            ember_rows=raw_ember[country],monthly=monthly,irena_rows=[r for r in irena['irena_rows'] if r['country']==country])
        data=gzip.compress(json.dumps(payload,separators=(',',':'),allow_nan=False).encode(),compresslevel=9,mtime=0);path=PUBLIC/(country+'.json.gz');path.write_bytes(data)
        files[path.name]=dict(sha256=digest(path),bytes=len(data),series=len(bank))
        entries.append(dict(code=country,name=name,file=path.name,sha256=digest(path),bytes=len(data),price_zones=[r['zone'] for r in price_rows],observed_price_zones=sum(r['known_hours']==8760 for r in price_rows),generation_source_areas=country_areas[country]))
        print('Country',country,'bytes',len(data),'series',len(bank),flush=True)
    assert sum(v['bytes'] for v in files.values())<=24*1024**2,'Review publication size before adding derived hourly data to Git'
    manifest=dict(schema_version=1,year=2025,hours=8760,start_utc='2025-01-01T00:00:00Z',generation_scale=10,price_scale=1000,default_country='DE',
        model=dict(id=MODEL_ID,label='Latest verified run: joint + weekly bids',case=CASE,mae_eur_mwh=next(r for r in s['results'] if r['anchor']==CASE)['metrics']['price'],accepted_baseline=False,summary_sha256=digest(LATEST/'summary.json'),audit_sha256=digest(LATEST/'verification-v1/audit.json'),witness_sha256=digest(witness)),
        technologies=[dict(id=t,label=name,psr=PSR[t]) for t,name in zip(TECH,NAMES)],ember_fuels=list(EMBER),countries=sorted(entries,key=lambda v:v['name']),
        sources=dict(irena=dict(url=irena['source_url'],sha256=irena['irena_pdf_sha256'],description='Original published end-2024/end-2025 capacity cells (MW), including source flags; renewable parent/child rows overlap and must not be added.'),ember=dict(url=ember_receipt['source_url'],sha256=ember_receipt['sha256'],description='Original 2025 monthly national generation rows, TWh; no hourly disaggregation.'),entsoe=dict(url='https://transparency.entsoe.eu/',description='Retained audited A44 hourly day-ahead prices and A75 hourly generation by PSR. Quarter-hour observations were energy/time-weight aggregated to UTC hours by the frozen source pipeline; no new interpolation.')),
        limitations=['2025 in-sample reconstruction; not independent forecast validation or recovered actual bids. Accepted baseline and browser scenario engine remain unchanged.',
        'Model generation is availability-proportional allocation within saved equal-offer blocks. Conditional per-technology lower/upper bounds are not simultaneous outcomes or confidence intervals.',
        'Hourly data is rounded to 0.1 MW generation / 0.001 EUR/MWh prices; hourly mean MW equals MWh in each one-hour bin. Summary price metrics use unrounded audited arrays.',
        'Missing source areas/types/hours remain null. A national hourly source total requires all constituent areas/types; partial zone sums are never presented as full-country generation.',
        'Germany A75 generation excludes Luxembourg, while DE-LU prices are shared. French national generation is distinct from the FR price area/model including Corsica; exact coverage is not certified.',
        'Pumped-storage output and other reported PSR types are preserved in raw source downloads but excluded from this fixed-hydro model taxonomy. Ember fuel and waste classifications remain proxies.'])
    write(PUBLIC/'manifest.json',manifest)
    np.savez_compressed(out/'aggregation.npz',model=point,lower=lower,upper=upper)
    write(out/'summary.json',dict(status='country_explorer_derived_no_new_market_solve',producer_sha256=digest(__file__),source_hashes=sources,model_summary_sha256=digest(LATEST/'summary.json'),model_audit_sha256=digest(LATEST/'verification-v1/audit.json'),witness_sha256=digest(witness),countries=countries,zones=zones,domains=domains,technologies=TECH,files=files,manifest_sha256=digest(PUBLIC/'manifest.json'),aggregation_sha256=digest(out/'aggregation.npz'),maximum_rounding_error_in_native_units=maximum_rounding_error,bytes=sum(v['bytes'] for v in files.values()),elapsed_seconds=time.perf_counter()-began))


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1200);run(a.out)
