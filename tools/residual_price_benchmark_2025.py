"""Retrospective temporal price benchmark; never a dispatch bid or asset model."""
import argparse,json,resource,signal,time
from pathlib import Path
import numpy as np
from scipy.optimize import isotonic_regression
from nve_hydro_diagnostics import ROOT,digest
from compare_daily_dispatch_prices import metrics,audit_observations

def fit_curve(x,y):
    valid=np.isfinite(x)&np.isfinite(y);x=x[valid];y=y[valid]
    if len(x)<2:raise ValueError('Insufficient training observations')
    order=np.argsort(x,kind='stable');x=x[order];y=y[order]
    unique,first,counts=np.unique(x,return_index=True,return_counts=True)
    means=np.add.reduceat(y,first)/counts
    fitted=isotonic_regression(means,weights=counts.astype(float),increasing=True).x
    return unique,fitted

def run(folder):
    started=time.perf_counter();out=folder/'benchmark.json'
    if out.exists():raise ValueError('Preserve completed benchmark')
    design=dict(training='2025-01-01T00:00Z through 2025-06-30T23:00Z; 4344 hours',
        evaluation='2025-07-01T00:00Z through 2025-12-31T23:00Z; 4416 hours',
        feature='Retained area demand minus available wind and solar, MW; not generation-derived availability',
        method='Single univariate monotone isotonic curve; duplicate inputs weighted by counts; linear interpolation and endpoint clipping',
        tuning='No search, alternative split or refit after evaluation; no agreed empirical acceptance threshold',
        scope='Retrospective temporal reference: 2025 aggregates already inspected; not untouched validation, synthetic bids or investment effects')
    (folder/'benchmark-design.json').write_text(json.dumps(design,indent=2)+'\n')
    source=ROOT/'data/residual-demand-audit-2025/v1';rs=json.loads((source/'summary.json').read_text());ra=json.loads((source/'replay.json').read_text())
    assert ra['summary_sha256']==digest(source/'summary.json');assert digest(source/'hourly.npz')==rs['witness_sha256']
    ss=json.loads((folder/'summary.json').read_text());assert digest(folder/'coupled.npz')==ss['witnesses']['coupled.npz']
    base=ROOT/'data/bidding-zone-network-2025/annual-v7';bs=json.loads((base/'summary.json').read_text());assert digest(base/'annual.npz')==bs['witness_sha256']
    manifest=ROOT/'data/price-trace/dispatch-validation-2025-v2/manifest.json';meta=json.loads(manifest.read_text())
    hours=np.datetime64('2025-01-01')+np.arange(8760).astype('timedelta64[h]');train=hours<np.datetime64('2025-07-01');test=~train
    assert int(train.sum())==4344 and int(test.sum())==4416
    rows=[];saved={}
    with np.load(source/'hourly.npz') as r,np.load(folder/'coupled.npz') as c,np.load(base/'annual.npz') as b:
        areas=r['zones'].tolist();physical_areas=bs['cases']['bidding_zone']['zones']
        for z,info in sorted(meta['zones'].items()):
            area='IE-SEM' if z=='IE' else z
            if area not in areas:continue
            path=manifest.parent/(z+'.json');assert digest(path)==info['hourly_sha256'];o=np.array(json.loads(path.read_text()),float);audit_observations(z,info,o)
            known=train&np.isfinite(o)
            if known.sum()<2:
                rows.append(dict(zone=z,status='training_prices_unavailable_not_zero',training_hours=int(known.sum())));continue
            j=areas.index(area);feature=r['residual_vre'][:,j];cx,cy=fit_curve(feature[known],o[known]);pred=np.interp(feature,cx,cy)
            old=b['bidding_zone_prices'][:,physical_areas.index(area)];coupled=c['prices'][:,ss['metadata']['primary'][area]]
            cohort=test&np.isfinite(o)&np.isfinite(coupled)&np.isfinite(old)&np.isfinite(pred)
            rows.append(dict(zone=z,status='retrospective_temporal_evaluation',training_hours=int(known.sum()),evaluation_hours=int(cohort.sum()),
                benchmark=metrics(pred[cohort],o[cohort]),physical=metrics(old[cohort],o[cohort]),coupled=metrics(coupled[cohort],o[cohort]),
                train_mean_reference=metrics(np.full(int(cohort.sum()),o[known].mean()),o[cohort]),
                evaluation_below_training_feature_range_hours=int((cohort&(feature<cx.min())).sum()),
                evaluation_above_training_feature_range_hours=int((cohort&(feature>cx.max())).sum())))
            saved[z+'_curve_x']=cx;saved[z+'_curve_y']=cy;saved[z+'_prediction']=pred
    np.savez_compressed(folder/'benchmark.npz',**saved)
    valid=[r for r in rows if r['status']=='retrospective_temporal_evaluation' and r['evaluation_hours']]
    comparisons={}
    for case in ['physical','coupled','benchmark','train_mean_reference']:
        correlations=[r[case]['correlation'] for r in valid if r[case]['correlation'] is not None]
        comparisons[case]=dict(areas=len(valid),equal_zone_mae=float(np.mean([r[case]['mae_eur_mwh'] for r in valid])),
            correlation_areas=len(correlations),mean_zonal_r=float(np.mean(correlations)) if correlations else None)
    result=dict(status='retrospective_temporal_price_reference_not_dispatch_acceptance',design=design,zones=rows,comparisons=comparisons,
        residual_summary_sha256=digest(source/'summary.json'),residual_replay_sha256=digest(source/'replay.json'),
        transport_summary_sha256=digest(folder/'summary.json'),baseline_summary_sha256=digest(base/'summary.json'),
        observation_manifest_sha256=digest(manifest),producer_sha256=digest(__file__),design_sha256=digest(folder/'benchmark-design.json'),
        witness_sha256=digest(folder/'benchmark.npz'),elapsed_seconds=time.perf_counter()-started)
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(comparisons,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(600);run(a.folder)
