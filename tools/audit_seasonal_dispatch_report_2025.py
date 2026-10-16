"""Independent source-column replay of the concise report's derived quantities."""
import argparse,datetime as dt,json,logging,resource,signal,time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,FAMILIES,CARRIER,PSR,EMBER,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from audit_hourly_offer_curves_2025 import compare,price_summary


def audit(folder,out):
    began=time.perf_counter();s=json.loads((folder/'summary.json').read_text())
    assert digest(ROOT/'tools/prepare_seasonal_dispatch_report_2025.py')==s['producer_sha256']
    for name,sha in s['source_hashes'].items():assert digest(ROOT/name)==sha
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    assert digest(folder/'comparison.npz')==s['witness_sha256']
    model=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1';ms=json.loads((model/'summary.json').read_text());ma=json.loads((model/'verification-v1/audit.json').read_text())
    assert digest(model/'summary.json')==s['original_model_summary_sha256']==ma['summary_sha256']
    assert digest(model/'verification-v1/audit.json')==s['original_model_audit_sha256']
    prior=ROOT/'data/bidding-zone-network-2025/hourly-offer-curves-v1';old=json.loads((prior/'summary.json').read_text())
    n,raw,fixed,*_=build();base,_=compile_global(n,raw,fixed,'bidding_zone');zones=s['zones'];tech=s['technologies'];countries=s['countries'];fuels=s['ember_fuels']
    assert zones==base['zones'] and tech==FAMILIES[:-1] and countries==['NO','DE','ES','FR'] and fuels==list(EMBER)
    original_av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    groups={};fmap={v:f for f,vs in EMBER.items() for v in vs};source=[]
    for i,(_,g) in enumerate(n.generators.iterrows()):
        groups.setdefault((base['buszone'][g.bus],raw[:,i].tobytes(),g.carrier=='emergency'),[]).append(i)
        family=CARRIER[g.carrier];country=n.buses.loc[g.bus,'country'];area=base['buszone'][g.bus]
        k='renewable' if fmap.get(family) in ['Wind','Solar'] else {'Gas':'gas','Coal':'coal','Nuclear':'nuclear'}.get(fmap.get(family),'other')
        source.append((area,country,family,k))
    expected=dict(parent=[],fractions=[],kinds=[],ranks=[],members=[])
    for parent,ids in enumerate(groups.values()):
        for kind in sorted({source[i][3] for i in ids}):
            selected=[i for i in ids if source[i][3]==kind]
            for rank,fraction in enumerate([.5,.35,.15] if kind in ['gas','coal'] else [.5,.5] if kind=='renewable' else [1.]):
                for key,value in [('parent',parent),('fractions',fraction),('kinds',kind),('ranks',rank),('members',selected)]:expected[key].append(value)
    compare(expected,json.loads((model/'layout.json').read_text()))
    # Direct original-source aggregation, independently of the producer's virtual
    # availability/group keys and allocate() implementation.
    with np.load(folder/'comparison.npz') as z:saved={k:z[k] for k in z.files}
    errors=[];model_prices={}
    def area_of(z):return {'DE-LU':'DE-national','FR':'FR-national'}.get(z,z)
    for name in ['control','combined']:
        info=old['annuals']['control'] if name=='control' else ms['annuals'][name];path=prior/info['witness'] if name=='control' else ROOT/info['witness'] if info.get('external') else model/info['witness'];assert digest(path)==info['witness_sha256']
        with np.load(path) as z:assert z['optimal'].all();x=z['values'][0:];prices=z['row_duals'][0:,:len(zones)]
        np.testing.assert_array_equal(prices,saved[name+'_prices']);model_prices[name]=prices
        p=np.zeros_like(saved[name+'_point']);lo=np.zeros_like(p);hi=np.zeros_like(p)
        cp=np.zeros((8760,len(countries),len(fuels)));cl=np.zeros_like(cp);cu=np.zeros_like(cp)
        for k,(ids,fraction) in enumerate(zip(expected['members'],expected['fractions'])):
            a=original_av[0:,ids].sum(axis=1)*fraction;q=np.clip(x[:,k],0,a)
            def contribution(selected):
                cap=original_av[0:,selected].sum(axis=1)*fraction
                return np.divide(q*cap,a,out=np.zeros(8760),where=a>0),np.maximum(q-a+cap,0),np.minimum(q,cap)
            for j,area in enumerate(zones):
                domain=area_of(area)
                candidates=[i for i in ids if (source[i][1]==domain[:2] if domain in ['DE-national','FR-national'] else source[i][0]==domain) and source[i][2]!='emergency']
                if not candidates:continue
                for f in {source[i][2] for i in candidates}:
                    values=contribution([i for i in candidates if source[i][2]==f]);column=tech.index(f)
                    for target,v in zip([p,lo,hi],values):target[:,j,column]+=v
            for j,country in enumerate(countries):
                candidates=[i for i in ids if source[i][1]==country and source[i][2]!='emergency']
                for f in {fmap[source[i][2]] for i in candidates}:
                    values=contribution([i for i in candidates if fmap[source[i][2]]==f]);column=fuels.index(f)
                    for target,v in zip([cp,cl,cu],values):target[:,j,column]+=v
        for bus in n.buses.index:
            country=n.buses.loc[bus,'country'];area=base['buszone'][bus];v=fixed[bus].values[0:]
            for j,z in enumerate(zones):
                d=area_of(z)
                if (country==d[:2] if d in ['DE-national','FR-national'] else area==d):
                    for target in [p,lo,hi]:target[:,j,tech.index('reservoir')]+=v
            if country in countries:
                for target in [cp,cl,cu]:target[:,countries.index(country),fuels.index('Hydro')]+=v
        for key,values in [('point',p),('lower',lo),('upper',hi)]:
            delta=float(abs(saved[name+'_'+key]-values).max());assert delta<1e-6;errors.append(delta)
        for key,values in [('point',cp),('lower',cl),('upper',cu)]:np.testing.assert_allclose(saved[name+'_country_'+key+'_twh'],values.sum(axis=0)/1e6,rtol=1e-10,atol=1e-8)
    observed=np.full_like(saved['observed'],np.nan);mix=ROOT/'data/bidding-zone-network-2025/generation-mix-v1';replay=json.loads((mix/'observations-replay.json').read_text())
    coverage=[];t0=dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)
    for j,zone in enumerate(zones):
        area=next((r for r in replay['zones'] if r['zone']==zone),None);coverage.append(dict(area=zone,model_generation_domain=area_of(zone),source_scope=None if area is None else area['geographic_scope']))
        if area is None:continue
        for month in area['monthly']:
            if month['status']!='raw_interval_energy_replayed':continue
            path=ROOT/f"data/carbon-pilot/map-2025/{zone}/{month['month']:02d}.json";assert digest(path)==month['processed_sha256']
            for row in json.loads(path.read_text()):
                hour=int((dt.datetime.fromisoformat(row['start'].replace('Z','+00:00'))-t0).total_seconds()/3600)
                for k,f in enumerate(tech):
                    value=row['generation_mwh_by_type'].get(PSR[f])
                    if value is not None:observed[hour,j,k]=value
    np.testing.assert_array_equal(observed,saved['observed']);compare(coverage,s['coverage'])
    import csv
    refs={}
    with (ROOT/'data/pypsa-eur/ember-current-release/monthly.csv').open() as f:
        for row in csv.DictReader(f):
            if row['Date'].startswith('2025-') and row['Area type'] in ['Country','Country or economy'] and row['Generation (TWh)'].strip():refs[row['ISO 3 code'],row['Electricity source'],int(row['Date'][5:7])]=float(row['Generation (TWh)'])
    from compare_native_exchange_reference import CODES
    for j,country in enumerate(countries):
        for k,f in enumerate(fuels):
            values=[refs.get((CODES[country],f,month)) for month in range(1,13)]
            if all(v is not None for v in values):assert abs(sum(values)-saved['ember_reference_twh'][j,k])<1e-8
            else:assert np.isnan(saved['ember_reference_twh'][j,k])
    with np.load(model/'development-targets.npz') as z:half_prices=z['prices']
    with np.load(model/'evaluation-targets.npz') as z:price_observed=np.concatenate([half_prices,z['prices']])
    with np.load(model/'out-of-fold.npz') as z:owner=z['fold']
    for name in ['control','combined']:
        prices=price_summary(model_prices[name],price_observed,zones)
        for j,row in enumerate(prices['zones']):
            valid=np.isfinite(price_observed[:-1,j])&np.isfinite(price_observed[1:,j])&(owner[:-1]==owner[1:])
            row['ramp_mae']=float(abs(np.diff(model_prices[name][:,j])[valid]-np.diff(price_observed[:,j])[valid]).mean()) if valid.any() else None
        compare(prices,s['results'][name]['price_summary'])
        rows=[];details=[]
        for j,area in enumerate(zones):
            nf=0;den=error=outside=0.
            for k,fuel in enumerate(tech):
                good=np.isfinite(observed[:,j,k]);count=int(good.sum());r=dict(area=area,technology=fuel,known_hours=count)
                if count:
                    nf+=1;o=observed[good,j,k];p=saved[name+'_point'][good,j,k];lo=saved[name+'_lower'][good,j,k];hi=saved[name+'_upper'][good,j,k]
                    ref=float(o.sum()/1e6);pred=float(p.sum()/1e6);lower=float(lo.sum()/1e6);upper=float(hi.sum()/1e6);den+=ref;error+=abs(pred-ref);outside+=max(lower-ref,ref-upper,0)
                    corr=float(np.corrcoef(p,o)[0,1]) if p.std()>1e-8 and o.std()>1e-8 else None
                    r.update(observed_twh=ref,model_twh=pred,lower_twh=lower,upper_twh=upper,hourly_mae_mw=float(abs(p-o).mean()),correlation=corr)
                details.append(r)
            rows.append(dict(area=area,covered_fuels=nf,covered_observed_twh=den,volume_error_percent=100*error/den if den else None,outside_interval_percent=100*outside/den if den else None))
        compare(rows,s['results'][name]['generation_summary']);compare(details,s['results'][name]['generation_detail'])
    result=dict(auditor_file='audit_seasonal_dispatch_report_2025.py',status='concise_report_generation_geography_allocation_observations_and_metrics_replayed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),
                maximum_hourly_allocation_difference_mw=max(errors),generation_areas=sum(r['volume_error_percent'] is not None for r in s['results']['control']['generation_summary']),
                price_areas=sum(r['known_hours']>0 for r in s['results']['control']['price_summary']['zones']),elapsed_seconds=time.perf_counter()-began,
                scope='Reporting derivation only; original annual feasibility/cost/selection replay remains linked; no new solve or model acceptance')
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or a.folder/'verification-v1';out.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(900);audit(a.folder,out)
