"""Three predeclared annual oil controls; reuse the independently audited control."""
import argparse, fcntl, json, logging, resource, signal, sys, time
from pathlib import Path
import numpy as np
from oil_supply_2025 import anchor, inputs, compile_case as old_case, ROOT, CAPACITY, INPUTS
from oil_chp_bids_2025 import PLAN, EUA, PLANTS, PRIOR, source_inputs, compile_case, collapse, oil_quantities
from generation_mix_2025 import digest, MONTH
from bid_calibration_2025 import month_quantities, immutable_hashes
from run_seasonal_calendar_bids_2025 import summary_prices
from joint_network_clear_2025 import clear_or_reject


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=lambda a:a.tolist())+'\n')


def observations():
    import gzip
    root = ROOT/'public/research/country-explorer-2025'
    manifest = json.loads((root/'manifest.json').read_text())
    index = next(i for i,t in enumerate(manifest['technologies']) if t['id']=='oil')
    arrays, sources = {}, {str((root/'manifest.json').relative_to(ROOT)):digest(root/'manifest.json')}
    for country in ['DE','BE','PL','SK','SI']:
        record = next(r for r in manifest['countries'] if r['code']==country)
        path = root/record['file']; assert digest(path)==record['sha256']
        doc = json.loads(gzip.decompress(path.read_bytes()))
        area = next(r for r in doc['generation'] if r['id']=='country:'+country)
        arrays[country] = np.array([np.nan if v is None else v/manifest['generation_scale'] for v in doc['series'][area['observed'][index]]])
        sources[str(path.relative_to(ROOT))] = digest(path)
    return arrays, sources


def oil_metrics(q, observed, countries, prices, targets, zones):
    out = []
    for country, obs in observed.items():
        j = countries.index(country); model = q[:,j]; valid = np.isfinite(obs)
        zone = 'DE-LU' if country=='DE' else country; zi=zones.index(zone)
        a, b = model[valid], obs[valid]
        r = float(np.corrcoef(a,b)[0,1]) if np.std(a)>1e-10 and np.std(b)>1e-10 else None
        out.append(dict(country=country, known_hours=int(valid.sum()), observed_twh=float(b.sum()/1e6),
            model_known_hours_twh=float(a.sum()/1e6), model_all_hours_twh=float(model.sum()/1e6),
            annual_bias_twh=float((a-b).sum()/1e6), hourly_mae_mw=float(abs(a-b).mean()),
            hourly_rmse_mw=float(np.sqrt(np.mean((a-b)**2))), hourly_correlation=r,
            observed_active_hours=int((b>.1).sum()), model_active_hours=int((a>.1).sum()),
            model_oil_at_negative_observed_price_twh=float(model[valid&(targets[:,zi]<0)].sum()/1e6),
            model_oil_at_negative_model_price_twh=float(model[valid&(prices[:,zi]<0)].sum()/1e6),
            monthly=[dict(month=i, known_hours=int((valid&(MONTH==i)).sum()),
                         observed_twh=float(obs[valid&(MONTH==i)].sum()/1e6),
                         model_twh=float(model[valid&(MONTH==i)].sum()/1e6)) for i in range(1,13)]))
    return out


def run(out):
    began=time.perf_counter(); design=json.loads(PLAN.read_text());write(out/'design.json',design)
    n,base,off,m,ctx,layout,c,flow,target=anchor()
    monthly,daily,co2,assumption,additions,oil=inputs(n,m,layout)
    reference,context=old_case(m,ctx,c,monthly,daily,co2,assumption,additions,oil,'capacity_and_daily_oil')
    source=source_inputs(n,reference,layout,oil,additions)
    np.savez_compressed(out/'source-inputs.npz',carbon=source['carbon'],gas=source['gas'],daily_oil=daily)
    write(out/'source-columns.json',{k:v for k,v in source.items() if k not in ['carbon','gas']})
    observed, obs_sources=observations()
    old=json.loads((PRIOR/'summary.json').read_text());cert=json.loads((PRIOR/'verification-v1/audit.json').read_text())
    assert cert['status']=='passed' and cert['summary_sha256']==digest(PRIOR/'summary.json')
    prepared=time.perf_counter()-began; outcomes={}; annuals={}; splits={}
    for key in design['cases']:
        case,extras=compile_case(reference,source,daily,assumption,key);splits[key]=extras
        if key=='control':
            info=old['annuals']['capacity_and_daily_oil'];path=PRIOR/info['witness'];assert digest(path)==info['witness_sha256']
            with np.load(path) as z:
                x,y,obj=z['values'],z['row_duals'],z['objectives'];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
            info=info|dict(witness=str(path.relative_to(ROOT)),reused=True)
        else:
            x,y,obj,info=clear_or_reject(case,flow,case['cost'],out/(key+'.npz'));info['reused']=False
            if x is None:
                write(out/'failure.json',dict(case=key,info=info));raise RuntimeError('Incomplete year; no annual metrics')
        annuals[key]=info
        emergency=float(x[:,:case['ng']][:,case['emergency_mask']].sum());assert emergency<=1e-6
        original=collapse(x,reference['ng'],extras)
        q=oil_quantities(case,x,ctx['countries'],source['records'],extras)
        np.savez_compressed(out/(key+'-oil.npz'),generation_mwh=q)
        outcomes[key]=dict(prices=summary_prices(y[:,:case['nz']],target['prices'],case['zones']),
            oil=oil_metrics(q,observed,ctx['countries'],y[:,:case['nz']],target['prices'],case['zones']),
            oil_generation_twh=float(q.sum()/1e6),emergency_mwh=emergency,
            monthly_quantities=month_quantities(context,original,0),
            physical_inputs=immutable_hashes(case,flow),oil_arrays_sha256=digest(out/(key+'-oil.npz')))
        write(out/'progress.json',dict(annuals=annuals,outcomes=outcomes))
        print(key,'MAE',outcomes[key]['prices']['equal_zone_mae'],'total oil TWh',q.sum()/1e6,flush=True)
    write(out/'tranches.json',splits)
    sources={str(p.relative_to(ROOT)):digest(p) for p in [PLAN,EUA,PLANTS,CAPACITY,INPUTS/'summary.json',INPUTS/'inputs.npz',PRIOR/'summary.json',PRIOR/'verification-v1/audit.json']}
    sources.update(obs_sources);sources.update(source['geography_sources'])
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    write(out/'summary.json',dict(status='oil_chp_controls_computed_not_promoted',design=design,source_hashes=sources,
        dependencies=dependencies,producer_sha256=digest(__file__),zones=m['zones'],countries=ctx['countries'],
        annuals=annuals,outcomes=outcomes,preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began,
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        files={p.name:digest(p) for p in [out/'source-inputs.npz',out/'source-columns.json',out/'tranches.json']}))


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);out=p.parse_args().out.resolve();out.mkdir(parents=True,exist_ok=False)
    lock=(out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);run(out)
