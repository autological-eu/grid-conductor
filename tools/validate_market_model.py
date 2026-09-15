"""Phase D starter validator for the FR–CH pilot.

Assembles the full August validation window from cache (no network), solves it
once, and evaluates the predeclared gates in docs/market-model-validation.md on
calibration vs held-out slices. Offline; needs scipy/numpy.
"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import math
import statistics
from carbon_pilot import ROOT, timestamp
from market_model import dispatch
from build_market_pilot import collect, THERMAL_COST

START=timestamp('2026-08-10T00:00:00Z');HOURS=504
CAL=240  # calibration 2026-08-10 → 2026-08-20; held-out 2026-08-20 → 2026-08-31
THERMAL_FREE=set(THERMAL_COST)
HYDRO_FREE={'B12'}
GATES=dict(P1='any zone held-out price MAE<=45 and <=naive mean-of-observed MAE',
    P2='held-out FR->CH flow MAE<=200MW',P3='per-zone held-out relMAD<=0.25 for thermal and hydro',
    P4='unserved_mwh==0 across the full window')


def rel_mad(window,obs_kind,gen_ids):
    total_mad=0.0;total_obs=0.0
    for i,r in enumerate(window):
        o=obs_kind[i]
        if o is None:continue
        total_mad+=abs(sum(r['generation_mw'][gid] for gid in gen_ids)-o);total_obs+=abs(o)
    return (total_mad/total_obs) if total_obs>1e-9 else None


def group_error(metrics, kinds):
    values=[v for k,v in metrics.items() if k in kinds]
    return statistics.mean(values) if values and all(v is not None and math.isfinite(v) for v in values) else None


def passes(value):
    return value is not None and math.isfinite(value) and value <= .25


def price_pairs(window, observations, zone):
    return [(row['price_eur_mwh'][zone], observed) for row, observed in zip(window, observations)
            if observed is not None and row['unserved_mwh'] <= 1e-6]


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
            pairs=price_pairs(window,obs,z)
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
                if g['zone']==z:gen[g['id'][len(z)+1:].split('-')[0]].append(g['id'])
            out['free_mad'][z]={}
            for kind,ids in gen.items():
                if kind not in THERMAL_FREE|HYDRO_FREE:continue
                out['free_mad'][z][kind]=rel_mad(window,data['observed_generation_mw'][z][kind][base:base+n],ids)
        return out
    metrics={k:window_metrics(k) for k in slices}
    benchmarks={}
    for z in data['zones']:
        obs=[o for r,o in zip(rows[CAL:],data['observed_price_eur_mwh'][z][CAL:]) if o is not None and r['unserved_mwh']<=1e-6]
        training=[v for v in data['observed_price_eur_mwh'][z][:CAL] if v is not None]
        mean=sum(training)/len(training) if training else None
        benchmarks[z]=dict(observed_count=len(obs),mean_eur_mwh=mean,
            mean_mae_eur_mwh=sum(abs(o-mean) for o in obs)/len(obs) if mean is not None and obs else None,
            persistence_mae_eur_mwh=None)  # No gap-compressed persistence benchmark.
    thermal=dict();hydro=dict()
    for z in data['zones']:
        km=metrics['held_out']['free_mad'][z]
        thermal[z]=group_error(km,THERMAL_FREE)
        hydro[z]=group_error(km,HYDRO_FREE)
    p1=any(metrics['held_out']['price_mae_eur_mwh'].get(z) is not None and benchmarks[z]['mean_mae_eur_mwh'] is not None and metrics['held_out']['price_mae_eur_mwh'][z]<=45
        and metrics['held_out']['price_mae_eur_mwh'][z]<=benchmarks[z]['mean_mae_eur_mwh'] for z in data['zones'])
    p2=metrics['held_out']['flow_mae_mw']['FR-CH']<=200
    p3=all(passes(thermal.get(z)) and passes(hydro.get(z)) for z in data['zones'])
    p4=result['unserved_mwh']==0
    gates=dict(P1=p1,P2=p2,P3=p3,P4=p4)
    decision='pilot_validated' if all(gates.values()) else 'experimental_not_validated'
    artifact=dict(price_source='ENTSO-E A44',validation_doc='docs/market-model-validation.md',window=dict(start='2026-08-10T00:00:00Z',
        hours=HOURS,calibration_hours=CAL,held_out_hours=HOURS-CAL),unserved_mwh=result['unserved_mwh'],
        metrics=metrics,benchmarks=benchmarks,thermal_relmad=thermal,hydro_relmad=hydro,
        gates=gates,decision=decision,note='annual rank attribution blocked unless decision==pilot_validated',
        generated_at=datetime.now(timezone.utc).isoformat())
    out=ROOT/'public/research/model-validation.json'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(artifact,allow_nan=False,indent=2),encoding='utf-8')
    print(f"unserved {result['unserved_mwh']} MWhe | 'decision' {decision}")
    for name in slices:
        m=metrics[name]
        print(name.upper(),' price MAE',{z:round(v,1) if v is not None else None for z,v in m['price_mae_eur_mwh'].items()},
            'bias',{z:round(v,1) if v is not None else None for z,v in m['price_bias_eur_mwh'].items()} if name=='calibration' else '',
            'flow MAE',{e:round(v,1) for e,v in m['flow_mae_mw'].items()},
            'thermal relMAD',{z:round(v,3) if v is not None else None for z,v in thermal.items()} if name=='held_out' else '')
    for z,v in benchmarks.items():print('bench',z,v)
    print('gates',gates)


if __name__=='__main__':main()
