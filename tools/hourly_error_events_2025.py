"""Saved-witness hourly error inventory. No clearing, fitting or data replacement."""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from generation_mix_2025 import ROOT, digest
from intraday_offer_bids_2025 import TIMEZONES

JOINT=ROOT/'data/bidding-zone-network-2025/joint-network-calibration-v4'
ACCEPTED=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1'
ANCHORS=['accepted-unchanged-w100','inverse_joint-nordic_higher-w100']


def load():
    s=json.loads((JOINT/'summary.json').read_text())
    audit=json.loads((JOINT/'verification-v1/audit.json').read_text())
    assert audit['summary_sha256']==digest(JOINT/'summary.json')
    files=[JOINT/'summary.json',JOINT/'verification-v1/audit.json']
    targets=[]
    for f in ['development-targets.npz','evaluation-targets.npz']:
        p=ACCEPTED/f;files.append(p)
        with np.load(p) as z:targets.append(z['prices'])
    models={}
    for k in ANCHORS:
        info=s['annuals'][k];p=ROOT/info['witness'] if info.get('external') else JOINT/info['witness']
        assert digest(p)==info['witness_sha256'];files.append(p)
        with np.load(p) as z:
            assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
            models[k]=z['row_duals'][:,:len(s['zones'])]
    return s['zones'],np.concatenate(targets),models,{str(p.relative_to(ROOT)):digest(p) for p in files}


def describe(p,o,zones):
    assert p.shape==o.shape==(8760,len(zones)) and np.isfinite(p).all()
    clock=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC')
    good=np.isfinite(o);assert all(good[:,j].all() or not good[:,j].any() for j in range(len(zones)))
    assert good.sum()==8760*41
    e=p-o;a=abs(e);total=float(a[good].sum());rows=[];bands=[]
    for label,lo,hi in [('negative',-np.inf,-1e-6),('near-zero',-1e-6,20),('20–80',20,80),('80–150',80,150),('150–250',150,250),('250+',250,np.inf)]:
        mask=good&(o>=lo)&(o<hi)
        bands.append(dict(regime=label,zone_hours=int(mask.sum()),mae=float(a[mask].mean()),bias=float(e[mask].mean()),absolute_error_share=float(a[mask].sum()/total)))
    for j,zone in enumerate(zones):
        if not good[:,j].all():rows.append(dict(zone=zone,known_hours=0));continue
        local=clock.tz_convert(TIMEZONES[zone[:2]]);weekend=local.dayofweek>=5
        er=e[:,j];ab=a[:,j]
        rows.append(dict(zone=zone,known_hours=8760,mae=float(ab.mean()),bias=float(er.mean()),
            weekday_bias=float(er[~weekend].mean()),weekend_bias=float(er[weekend].mean()),
            weekday_mae=float(ab[~weekend].mean()),weekend_mae=float(ab[weekend].mean()),
            negative_observed_hours=int((o[:,j]<-1e-6).sum()),negative_model_hours=int((p[:,j]<-1e-6).sum()),
            monthly=[dict(month=m,mae=float(ab[clock.month==m].mean()),bias=float(er[clock.month==m].mean())) for m in range(1,13)],
            local_hour=[dict(hour=h,mae=float(ab[local.hour==h].mean()),bias=float(er[local.hour==h].mean())) for h in range(24)],
            top_hours=[dict(utc=clock[t].isoformat(),observed=float(o[t,j]),model=float(p[t,j]),error=float(er[t])) for t in np.argsort(ab)[-5:][::-1]]))
    daily=np.nanmean(a.reshape(365,24,len(zones)),axis=(1,2))
    # Hours with many jointly underpriced zones identify shared events, not causes.
    worst=[dict(utc_date=str(clock[d*24].date()),equal_zone_mae=float(daily[d]),
        mean_bias=float(np.nanmean(e[d*24:(d+1)*24]))) for d in np.argsort(daily)[-15:][::-1]]
    flat=a[good];n=int(np.ceil(.1*len(flat)))
    return dict(equal_zone_mae=float(flat.mean()),bias=float(e[good].mean()),
        top_decile_absolute_error_share=float(np.sort(flat)[-n:].sum()/total),
        regimes=bands,zones=rows,worst_utc_days=worst)


def run(out):
    zones,o,models,sources=load()
    result=dict(status='complete_2025_saved_witness_error_inventory',source_hashes=sources,
        producer_sha256=digest(__file__),zones=zones,models={k:describe(p,o,zones) for k,p in models.items()},
        limitations=['Observed-price regimes condition on the target, not features deployable in bids.',
        'Weekday/weekend and event associations are descriptive, not causal attribution.',
        'All 2025 was inspected/calibrated; no independent forecast accuracy.',
        'All 41 complete observed zones retained; seven modeled areas lack complete price targets.'])
    out.mkdir(parents=True,exist_ok=False)
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    for k,r in result['models'].items():print(k,r['equal_zone_mae'],r['worst_utc_days'][:3],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();run(a.out)
