"""Derive zonal/national generation comparisons from the verified baseline and hourly-bid experiment."""
import argparse,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,FAMILIES,CARRIER,PSR,EMBER,allocate,digest,ember_rows
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from bid_calibration_2025 import prepare,immutable_hashes
from hourly_offer_curves_2025 import compile_curves

START=0
TECH=FAMILIES[:-1]
COUNTRIES=['NO','DE','ES','FR']


def domain(area):return {'DE-LU':'DE-national','FR':'FR-national'}.get(area,area)


def summarize(areas,point,lower,upper,observed):
    rows=[];detail=[]
    for j,area in enumerate(areas):
        known_fuels=0;den=err=outside=0.
        for k,fuel in enumerate(TECH):
            o=observed[:,j,k];good=np.isfinite(o);hours=int(good.sum())
            row=dict(area=area,technology=fuel,known_hours=hours)
            if hours:
                known_fuels+=1;p=point[good,j,k];lo=lower[good,j,k];hi=upper[good,j,k];ref=float(o[good].sum()/1e6);pred=float(p.sum()/1e6);l=float(lo.sum()/1e6);u=float(hi.sum()/1e6)
                den+=ref;err+=abs(pred-ref);outside+=max(l-ref,ref-u,0.)
                correlation=float(np.corrcoef(p,o[good])[0,1]) if p.std()>1e-8 and o[good].std()>1e-8 else None
                row.update(observed_twh=ref,model_twh=pred,lower_twh=l,upper_twh=u,hourly_mae_mw=float(abs(p-o[good]).mean()),correlation=correlation)
            detail.append(row)
        rows.append(dict(area=area,covered_fuels=known_fuels,covered_observed_twh=den,volume_error_percent=100*err/den if den>0 else None,outside_interval_percent=100*outside/den if den>0 else None))
    return rows,detail


def run(out):
    began=time.perf_counter();model=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1';s=json.loads((model/'summary.json').read_text());audit=json.loads((model/'verification-v1/audit.json').read_text())
    assert audit['summary_sha256']==digest(model/'summary.json')
    for name,sha in s['source_hashes'].items():assert digest(ROOT/name)==sha
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    sources=s['source_hashes'].copy()
    for p in [model/'summary.json',model/'verification-v1/audit.json',model/'layout.json']:sources[str(p.relative_to(ROOT))]=digest(p)
    prior=ROOT/'data/bidding-zone-network-2025/hourly-offer-curves-v1';old=json.loads((prior/'summary.json').read_text())
    sources[str((prior/'summary.json').relative_to(ROOT))]=digest(prior/'summary.json')
    mix=ROOT/'data/bidding-zone-network-2025/generation-mix-v1';ms=json.loads((mix/'summary.json').read_text());ma=json.loads((mix/'verification-v2/audit.json').read_text())
    assert ma['summary_sha256']==digest(mix/'summary.json') and digest(mix/'observations-replay.json')==ms['observations_replay_sha256']
    for p in [mix/'summary.json',mix/'verification-v2/audit.json',mix/'observations-replay.json']:sources[str(p.relative_to(ROOT))]=digest(p)
    replay=json.loads((mix/'observations-replay.json').read_text())
    print('Rebuilding source membership for saved-dispatch aggregation; no market solve',flush=True)
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone')
    from nve_hydro_diagnostics import branch_offsets
    assert immutable_hashes(base,branch_offsets(n,off))==s['original_physical_inputs']
    ctx=prepare(n,base,raw,fixed);m,c,layout=compile_curves(base,ctx)
    assert layout==json.loads((model/'layout.json').read_text())
    zones=s['zones'];domains=zones+['DE-national','FR-national'];countries=COUNTRIES;ember_fuels=list(EMBER)
    zone_keys=[];national_keys=[];country_keys=[];fmap={v:k for k,vs in EMBER.items() for v in vs}
    for members in layout['members']:
        for i in members:
            g=n.generators.iloc[i];fuel=CARRIER[g.carrier];country=n.buses.loc[g.bus,'country'];area=base['buszone'][g.bus]
            zone_keys.append(None if fuel=='emergency' else (area,fuel))
            national_keys.append((country+'-national',fuel) if country in ['DE','FR'] and fuel!='emergency' else None)
            country_keys.append((country,fmap[fuel]) if country in countries and fuel!='emergency' else None)
    available=c['availability'][START:];groups=c['groups'];shape=(8760,len(zones),len(TECH));national_shape=(8760,2,len(TECH));country_shape=(8760,len(countries),len(ember_fuels))
    water=np.zeros((8760,len(domains)));country_water=np.zeros((8760,len(countries)))
    for bus in n.buses.index:
        country=n.buses.loc[bus,'country'];area=base['buszone'][bus];v=fixed[bus].values[START:]
        water[:,domains.index(area)]+=v
        if country in ['DE','FR']:water[:,domains.index(country+'-national')]+=v
        if country in countries:country_water[:,countries.index(country)]+=v
    observed=np.full((8760,len(zones),len(TECH)),np.nan);coverage=[]
    for area in zones:
        record=next((r for r in replay['zones'] if r['zone']==area),None);coverage.append(dict(area=area,model_generation_domain=domain(area),source_scope=None if record is None else record['geographic_scope']))
        if record is None:continue
        j=zones.index(area)
        for month in record['monthly']:
            if month['status']!='raw_interval_energy_replayed':continue
            path=ROOT/f"data/carbon-pilot/map-2025/{area}/{month['month']:02d}.json";assert digest(path)==month['processed_sha256'];sources[str(path.relative_to(ROOT))]=digest(path)
            for row in json.loads(path.read_text()):
                t=int((np.datetime64(row['start'].removesuffix('Z'))-np.datetime64('2025-01-01T00')).astype('timedelta64[h]').astype(int))
                if not 0<=t<8760:raise ValueError('Observation outside declared evaluation period')
                for k,fuel in enumerate(TECH):
                    code=PSR[fuel]
                    if code in row['generation_mwh_by_type']:observed[t,j,k]=row['generation_mwh_by_type'][code]
    bank=ember_rows(ROOT/'data/pypsa-eur/ember-current-release/monthly.csv');reference=np.full((len(countries),len(ember_fuels)),np.nan)
    from compare_native_exchange_reference import CODES
    for j,country in enumerate(countries):
        for k,fuel in enumerate(ember_fuels):
            vals=[bank.get((CODES[country],fuel,month)) for month in range(1,13)]
            if all(v is not None for v in vals):reference[j,k]=sum(vals)
    arrays=dict(observed=observed,ember_reference_twh=reference);results={};prices={}
    for name in ['control','combined']:
        info=old['annuals']['control'] if name=='control' else s['annuals'][name];path=prior/info['witness'] if name=='control' else ROOT/info['witness'] if info.get('external') else model/info['witness'];assert digest(path)==info['witness_sha256'];sources[str(path.relative_to(ROOT))]=digest(path)
        with np.load(path) as z:assert z['optimal'].all();x=z['values'][START:];prices[name]=z['row_duals'][START:,:len(zones)]
        zvals=allocate(available,x[:,:m['ng']],groups,zone_keys,[(z,f) for z in zones for f in TECH])[:3]
        nvals=allocate(available,x[:,:m['ng']],groups,national_keys,[(z,f) for z in ['DE-national','FR-national'] for f in TECH])[:3]
        cvals=allocate(available,x[:,:m['ng']],groups,country_keys,[(z,f) for z in countries for f in ember_fuels])[:3]
        full=[]
        for which in range(3):
            v=np.concatenate([zvals[which].reshape(shape),nvals[which].reshape(national_shape)],axis=1);v[:,:,TECH.index('reservoir')]+=water
            cv=cvals[which].reshape(country_shape);cv[:,:,ember_fuels.index('Hydro')]+=country_water
            full.append(v);arrays[name+'_country_'+['point','lower','upper'][which]+'_twh']=cv.sum(axis=0)/1e6
        matched=[v[:,[domains.index(domain(z)) for z in zones],:] for v in full]
        for suffix,v in zip(['point','lower','upper'],matched):arrays[name+'_'+suffix]=v
        summary,detail=summarize(zones,*matched,observed);results[name]=dict(generation_summary=summary,generation_detail=detail,price_summary=s['outcomes'][name]['prices'])
        arrays[name+'_prices']=prices[name]
        print('Aggregated',name,'against',sum(r['volume_error_percent'] is not None for r in summary),'generation reporting areas',flush=True)
    np.savez_compressed(out/'comparison.npz',**arrays)
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    result=dict(model_folder=str(model.relative_to(ROOT)),producer_file='prepare_seasonal_dispatch_report_2025.py',period='Full 2025: 8760 UTC hours; out-of-fold seasonal interpolation, separate from the in-sample annual refit',zones=zones,technologies=TECH,countries=countries,ember_fuels=ember_fuels,coverage=coverage,results=results,
                original_model_summary_sha256=digest(model/'summary.json'),original_model_audit_sha256=digest(model/'verification-v1/audit.json'),source_hashes=sources,dependencies=dependencies,producer_sha256=digest(__file__),
                witness_sha256=digest(out/'comparison.npz'),elapsed_seconds=time.perf_counter()-began,limitations=['Country Ember and zonal A75 sources are separate. Germany generation excludes LU; France uses national model membership including FR-COR.',
                'Missing types/hours remain unknown; per-area error covers reported fuels only. Not certified total-fleet generation or exact commercial geography.',
                'Point allocations proportional to original availability within saved equal-price blocks; conditional bounds not jointly attainable or all primal optima. No new solve, input change or promotion.'])
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(900);run(a.out)
