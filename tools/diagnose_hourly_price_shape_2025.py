"""Saved-witness price/input diagnosis; no solve, fitting or input correction."""
import argparse
import json
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,digest
from hourly_offer_curves_2025 import FIT,SELECT,summarize,local_profile


def run(out):
    prior=ROOT/'data/bidding-zone-network-2025/zonal-bid-blocks-v2';s=json.loads((prior/'summary.json').read_text());a=json.loads((prior/'verification-v1/audit.json').read_text())
    assert a['summary_sha256']==digest(prior/'summary.json')
    residual=ROOT/'data/residual-demand-audit-2025/v1';r=json.loads((residual/'summary.json').read_text())
    assert json.loads((residual/'replay.json').read_text())['summary_sha256']==digest(residual/'summary.json')
    assert digest(residual/'hourly.npz')==r['witness_sha256']
    response=ROOT/'data/bidding-zone-network-2025/response-diagnostic-v1'
    inventory=json.loads((response/'summary.json').read_text())
    assert json.loads((response/'audit.json').read_text())['summary_sha256']==digest(response/'summary.json')
    # Input inventory already independently replayed; its receipt is rehashed.
    paths=[prior/'summary.json',prior/'verification-v1/audit.json',prior/'training-targets.npz',prior/'evaluation-targets.npz',residual/'summary.json',residual/'replay.json',residual/'hourly.npz',response/'summary.json',response/'audit.json']
    with np.load(prior/'training-targets.npz') as z:train=z['prices']
    with np.load(prior/'evaluation-targets.npz') as z:test=z['prices']
    observed=np.r_[train,test];models={}
    for name in ['control','zonal_blocks']:
        info=s['annuals'][name];path=prior/info['witness'];assert digest(path)==info['witness_sha256'];paths.append(path)
        with np.load(path) as z:models[name]=z['row_duals'][:,:len(s['zones'])]
    with np.load(residual/'hourly.npz') as z:inputs={k:z[k] for k in z.files}
    assert inputs['zones'].tolist()==s['zones']
    outcomes={}
    for name,p in models.items():
        outcomes[name]={period:summarize(p[start:stop],observed[start:stop],s['zones']) for period,start,stop in [('fit',0,FIT),('selection',FIT,SELECT),('evaluation',SELECT,8760)]}
    checks=[];profiles={};bands=[]
    for j,zone in enumerate(s['zones']):
        residual_curve=inputs['residual_vre'][:,j];edges=np.quantile(residual_curve[:FIT],[.2,.4,.6,.8]);which=np.searchsorted(edges,residual_curve[SELECT:],side='right')
        for k in range(5):
            mask=(which==k)&np.isfinite(observed[SELECT:,j]);count=int(mask.sum())
            bands.append(dict(zone=zone,band=k+1,hours=count,observed_mean=float(observed[SELECT:,j][mask].mean()) if count else None,
                              model_mean=float(models['control'][SELECT:,j][mask].mean()) if count else None))
        for technology in ['solar','wind']:
            available=inputs[technology][:,j];reported=inputs['reported_'+technology][:,j];known=np.isfinite(reported)
            lag=[]
            for shift in range(-3,4):
                # Compare A[t+shift] with reported[t], never modify either input.
                start=max(0,-shift);stop=min(8760,8760-shift);x=available[start+shift:stop+shift];y=reported[start:stop];ok=np.isfinite(y)
                cor=float(np.corrcoef(x[ok],y[ok])[0,1]) if ok.sum()>1 and x[ok].std()>1e-12 and y[ok].std()>1e-12 else None
                lag.append(dict(available_hour_shift=shift,known_hours=int(ok.sum()),correlation=cor))
            checks.append(dict(zone=zone,technology=technology,reported_hours=int(known.sum()),available_twh=float(available.sum()/1e6),
                               reported_twh=float(reported[known].sum()/1e6) if known.all() else None,lag_diagnostics=lag))
        if zone in ['ES','FR']:
            tz='Europe/Madrid' if zone=='ES' else 'Europe/Paris'
            profiles[zone]={name:local_profile(p[SELECT:,j],SELECT,tz) for name,p in models.items()}
            profiles[zone]['observed']=local_profile(observed[SELECT:,j],SELECT,tz)
    result=dict(status='saved_hourly_diagnosis_not_source_correction',zones=s['zones'],outcomes=outcomes,input_checks=checks,residual_bands=bands,local_profiles=profiles,
                inventory=inventory['inventory'],source_hashes={str(p.relative_to(ROOT)):digest(p) for p in paths},producer_sha256=digest(__file__),
                helper_sha256=digest(ROOT/'tools/hourly_offer_curves_2025.py'),
                limitations=['Timing lags are descriptive and can reflect dispatch/curtailment, not proven clock errors. No time shifting or generation-derived availability.',
                             'Available thermal/nuclear capacity is not audited operational availability; flat profiles flag missing outage/derating timing.',
                             '2025 already inspected; evaluation diagnostics do not make it untouched. No new market solve or acceptance.'])
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    for zone in ['ES','FR']:
        rows=[next(r for r in outcomes[name]['evaluation']['zones'] if r['zone']==zone) for name in models]
        print(zone,'observed/control/blocks daily ranges',rows[0]['observed_daily_range_mean'],*[v['model_daily_range_mean'] for v in rows],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);run(a.out)
