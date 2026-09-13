"""Phase D starter validator for the FR–CH pilot.

Assembles the full August validation window from cache (no network), solves it
once, and evaluates the predeclared gates in docs/market-model-validation.md on
calibration vs held-out slices. Offline; needs scipy/numpy.
"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from carbon_pilot import ROOT, timestamp
from market_model import dispatch
from build_market_pilot import collect

START=timestamp('2026-08-10T00:00:00Z');HOURS=504
CAL=240  # calibration 2026-08-10 → 2026-08-20; held-out 2026-08-20 → 2026-08-31
THERMAL_FREE={'B02','B04','B05','B06','B11','B14','B16'}
HYDRO_FREE={'B12','B13','B19'}
GATES=dict(P1='any zone held-out price MAE<=45 and <=naive mean-of-observed MAE',
    P2='held-out FR->CH flow MAE<=200MW',P3='per-zone held-out relMAD<=0.25 for thermal and hydro',
    P4='unserved_mwh==0 across the full window')


def rel_mad(window,obs_kind,gen_ids):
    total_mad=0.0;total_obs=0.0
    for i,r in enumerate(window):
        for gid in gen_ids:
            o=obs_kind[i]
            if o is None:continue
            total_mad+=abs(r['generation_mw'][gid]-o);total_obs+=abs(o)
    return (total_mad/total_obs) if total_obs>1e-9 else None


def main():
    data=collect(START,HOURS)
    result=dispatch(data)
    rows=result['hourly'];H=len(rows)
    slices=dict(calibration=rows[:CAL],held_out=rows[CAL:])
    off=dict(calibration=0,held_out=CAL)
    def window_metrics(name):
        window=slices[name];base=off[name];n=len(window);out={}
        out['price_mae_eur_mwh']={};out['price_bias_eur_mwh']={};out['flow_mae_mw']={}
        for z in data['zones']:
            model=[r for r in window if r['unserved_mwh']<=1e-6]  # price is VoLL when unserved; P4 owns infeasibility
            obs=data['observed_price_eur_mwh'][z][base:base+n]
            pairs=[(m['price_eur_mwh'][z],o) for m,o in zip(model,obs[0:len(model)]) if o is not None]
            out['price_mae_eur_mwh'][z]=sum(abs(m-o) for m,o in pairs)/len(pairs) if pairs else None
            out['price_bias_eur_mwh'][z]=sum(m-o for m,o in pairs)/len(pairs) if pairs else None
        out['price_excluded_unserved']=sum(1 for r in window if r['unserved_mwh']>1e-6)
        model=[r['flow_mw']['FR-CH'] for r in window]
        obs=data['observed_flow_mw']['FR-CH'][base:base+n]
        out['flow_mae_mw']['FR-CH']=sum(abs(m-o) for m,o in zip(model,obs))/n
        out['free_mad']={}
        for z in data['zones']:
            gen=defaultdict(list)
            for g in data['generators']:
                if g['zone']==z:gen[g['id'].split('-',1)[1]].append(g['id'])
            out['free_mad'][z]={}
            for kind,ids in gen.items():
                if kind not in THERMAL_FREE|HYDRO_FREE:continue
                out['free_mad'][z][kind]=rel_mad(window,data['observed_generation_mw'][z][kind],ids)
        return out
    metrics={k:window_metrics(k) for k in slices}
    benchmarks={}
    for z in data['zones']:
        obs=[o for r,o in zip(rows[CAL:],data['observed_price_eur_mwh'][z][CAL:]) if o is not None and r['unserved_mwh']<=1e-6]
        mean=sum(obs)/len(obs) if obs else None
        benchmarks[z]=dict(observed_count=len(obs),mean_eur_mwh=mean,
            mean_mae_eur_mwh=sum(abs(o-mean) for o in obs)/len(obs) if mean else None,
            persistence_mae_eur_mwh=sum(abs(o-prev) for prev,o in zip(obs,obs[1:]) if o is not None and prev is not None)/sum(1 for prev,o in zip(obs,obs[1:]) if o is not None and prev is not None))
    thermal=dict();hydro=dict()
    for z in data['zones']:
        km=metrics['held_out']['free_mad'][z]
        thermal[z]=np.nanmean([km[k] for k in km if k in THERMAL_FREE]) if any(k in km for k in THERMAL_FREE) else None
    p1=any(z in metrics['held_out']['price_mae_eur_mwh'] and metrics['held_out']['price_mae_eur_mwh'][z]<=45
        and metrics['held_out']['price_mae_eur_mwh'][z]<=benchmarks[z]['mean_mae_eur_mwh'] for z in data['zones'])
    p2=metrics['held_out']['flow_mae_mw']['FR-CH']<=200
    p3=all((thermal.get(z) or 0)<=0.25 and (hydro.get(z) or 0)<=0.25 for z in data['zones'])
    p4=result['unserved_mwh']==0
    gates=dict(P1=p1,P2=p2,P3=p3,P4=p4)
    decision='pilot_validated' if all(gates.values()) else 'experimental_not_validated'
    artifact=dict(validation_doc='docs/market-model-validation.md',window=dict(start='2026-08-10T00:00:00Z',
        hours=HOURS,calibration_hours=CAL,held_out_hours=HOURS-CAL),unserved_mwh=result['unserved_mwh'],
        metrics=metrics,benchmarks=benchmarks,thermal_relmad=thermal,hydro_relmad=hydro,
        gates=gates,decision=decision,note='annual rank attribution blocked unless decision==pilot_validated',
        generated_at=datetime.now(timezone.utc).isoformat())
    out=ROOT/'public/research/model-validation.json'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(artifact,allow_nan=True,indent=2),encoding='utf-8')
    print(f"unserved {result['unserved_mwh']} MWhe | 'decision' {decision}")
    for name in slices:
        m=metrics[name]
        print(name.upper(),' price MAE',{z:round(v,1) for z,v in m['price_mae_eur_mwh'].items()},
            'bias',{z:round(v,1) for z,v in m['price_bias_eur_mwh'].items()} if name=='calibration' else '',
            'flow MAE',{e:round(v,1) for e,v in m['flow_mae_mw'].items()},
            'thermal relMAD',{z:round(v,3) for z,v in thermal.items()} if name=='held_out' else '')
    for z,v in benchmarks.items():print('bench',z,v)
    print('gates',gates)


if __name__=='__main__':main()