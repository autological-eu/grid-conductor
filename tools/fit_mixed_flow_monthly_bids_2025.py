"""Pilot monthly bid fit with inferred transport on missing-A09 hours.

All zone-hours enter price/mix losses. A09 flow loss is masked to observed
commercial exchanges inside the model's declared corridor bounds. This is a
retrospective research proxy, not accepted physical or scenario clearing.
"""
import argparse
import json
import re
import time
import traceback

import numpy as np
from scipy.special import expit

from batched_transport_newton_recovery_2025 import RecoveredTransportMarket
from flow_adjusted_zonal_clearing_2025 import DEST,observed_exchanges
from monthly_diurnal_splines_2025 import labels
from run_batched_transport_2025 import setup
from supply_knot_splines_2025 import initial_parameters


def solve_with_neighbor_starts(market,theta,hours,p0=None,max_restarts=12):
    """Retry only stalled hours from adjacent *model-cleared* price vectors."""
    start=market.initial_prices(market.offers(theta,hours)) if p0 is None else p0.copy()
    seeded=[]
    for _ in range(max_restarts+1):
        try:
            result=market.solve(theta,hours,p0=start)
            result['neighbor_start_hours']=seeded
            return result
        except RuntimeError as error:
            match=re.search(r'hours=\[([0-9, ]+)\]',str(error))
            if not match:raise
            bad=[int(x) for x in match.group(1).split(',') if x.strip()]
            progressed=False
            for hour in bad:
                positions=np.flatnonzero(hours==hour)
                if len(positions)!=1:raise ValueError('Bad stalled-hour mapping')
                k=int(positions[0])
                for near in (k-1,k+1):
                    if not 0<=near<len(hours):continue
                    try:
                        adjacent=market.solve(theta[near:near+1],hours[near:near+1])
                    except RuntimeError:continue
                    start[k]=adjacent['prices'][0]
                    seeded.append(dict(hour=hour,from_hour=int(hours[near])))
                    progressed=True;break
            if not progressed:raise
    raise RuntimeError(f'Neighbor-start budget exhausted: {seeded}')


def data_loss(market,result,observed_prices,observed_generation,fixed,ci,ti,
              flow_target,flow_mask):
    """Price, absolute technology generation, mix shares and observed flow."""
    price=result['prices'];q=result['quantities_gw'];flow=result['flows_gw']
    p_mask=np.isfinite(observed_prices);p_error=np.where(p_mask,price-np.nan_to_num(observed_prices),0)
    p_scaled=p_error/40;eps=.01
    p_cells=max(1,int(p_mask.sum()))
    p_loss=float((np.sqrt(p_scaled[p_mask]**2+eps**2)-eps).sum()/p_cells)
    gp=np.where(p_mask,p_scaled/np.sqrt(p_scaled**2+eps**2)/40/p_cells,0)

    modeled=fixed.copy();ng=q.shape[1]
    for g in range(ng):modeled[:,ci[g],ti[g]]+=q[:,g]
    mask=np.isfinite(observed_generation)
    observed=np.nan_to_num(observed_generation)
    error=np.where(mask,modeled-observed,0);scaled=error/3
    cells=max(1,int(mask.sum()))
    volume_loss=float((np.sqrt(scaled[mask]**2+eps**2)-eps).sum()/cells)
    gc=np.where(mask,scaled/np.sqrt(scaled**2+eps**2)/3/cells,0)

    # Compare technology shares only over the same source-covered categories.
    mt=np.where(mask,modeled,0);ot=np.where(mask,observed,0)
    mt_total=mt.sum(axis=2,keepdims=True);ot_total=ot.sum(axis=2,keepdims=True)
    share_ok=mask&(mt_total>1e-6)&(ot_total>1e-6)
    ms=np.divide(mt,mt_total,out=np.zeros_like(mt),where=mt_total>1e-6)
    os=np.divide(ot,ot_total,out=np.zeros_like(ot),where=ot_total>1e-6)
    se=np.where(share_ok,ms-os,0);share_cells=max(1,int(share_ok.sum()))
    share_loss=float((np.sqrt(se[share_ok]**2+eps**2)-eps).sum()/share_cells)
    gs=np.where(share_ok,se/np.sqrt(se**2+eps**2)/share_cells,0)
    projection=(gs*ms).sum(axis=2,keepdims=True)
    gc+=np.where(share_ok,np.divide(gs-projection,mt_total,
                                   out=np.zeros_like(gs),where=mt_total>1e-6),0)
    gq=gc[:,ci,ti]

    f_mask=flow_mask;limit=np.maximum(np.maximum(abs(market.lower[result['hours']]),
                                    abs(market.upper[result['hours']])),.25)
    fe=np.where(f_mask,(flow-np.nan_to_num(flow_target))/limit,0)
    f_cells=max(1,int(f_mask.sum()))
    f_loss=float((np.sqrt(fe[f_mask]**2+eps**2)-eps).sum()/f_cells)
    gf=np.where(f_mask,fe/np.sqrt(fe**2+eps**2)/limit/f_cells,0)
    # The observed-flow term is diagnostic and downweighted where the physical
    # transport proxy differs from commercial schedules.
    f_weight=.2;f_loss*=f_weight;gf*=f_weight
    unconstrained=(price@market.M.T)/market.cost
    lo=market.lower[result['hours']];hi=market.upper[result['hours']]
    derivative=(expit((unconstrained-lo)/market.flow_tau)-
                expit((unconstrained-hi)/market.flow_tau))/market.cost
    gp+=(gf*derivative)@market.M
    metrics=dict(price_mae=float(abs(p_error[p_mask]).mean()) if p_mask.any() else None,
        generation_mae_gw=float(abs(error[mask]).mean()) if mask.any() else None,
        mix_share_mae=float(abs(se[share_ok]).mean()) if share_ok.any() else None,
        observed_flow_mae_gw=float(abs((flow-flow_target)[f_mask]).mean()) if f_mask.any() else None,
        price_cells=int(p_mask.sum()),generation_cells=int(mask.sum()),
        mix_cells=int(share_ok.sum()),observed_flow_cells=int(f_mask.sum()),
        price_loss=p_loss,volume_loss=volume_loss,mix_loss=share_loss,flow_loss=f_loss,
        total_loss=p_loss+volume_loss+share_loss+f_loss)
    return metrics,gq,gp


def fit(month,updates,rate,market,s,d,flow_target,flow_mask,missing_zone,path,
        allow_projected_gradient=False):
    stamps=np.arange('2025-01-01','2026-01-01',dtype='datetime64[h]')
    hours=np.flatnonzero(stamps.astype('datetime64[M]')==np.datetime64(f'2025-{month:02d}'))
    clock=labels(s['groups'],hours);ng=market.ng
    neutral=initial_parameters(ng)[:,[0,5,6,7,8,9]]
    weights=np.broadcast_to(neutral,(24,ng,6)).copy();initial=weights.copy()
    first=np.zeros_like(weights);second=np.zeros_like(weights)
    ci=np.array([g['country_id'] for g in s['groups']]);ti=np.array([s['technologies'].index(g['technology']) for g in s['groups']])
    observed=d['observed_generation'][hours]/1000;fixed=d['fixed_generation'][hours]/1000
    price_target=d['observed_prices'][hours]
    flow_target=flow_target[hours];flow_mask=flow_mask[hours]
    prior=None;history=[];began=time.perf_counter();previous=weights.copy()
    checkpoint=path/'resume.npz';journal=path/'history.json'
    start=0
    if checkpoint.exists():
        with np.load(checkpoint) as z:
            weights=z['weights'];previous=z['previous'];first=z['first'];second=z['second']
            prior=z['prior'] if bool(z['has_prior']) else None;start=int(z['step'])
        history=json.loads(journal.read_text())
        if len(history)!=start:raise ValueError('Checkpoint/history mismatch')
    for step in range(start,updates+1):
        attempts=[];result=None;factor_used=None;fallback=False
        for factor in (1.,.5,.25,.125,.0625,.03125):
            trial=previous+factor*(weights-previous)
            theta=trial[clock,np.arange(ng)]
            for label,p0 in [('warm',prior),('cold',None)] if prior is not None else [('cold',None)]:
                try:result=solve_with_neighbor_starts(market,theta,hours,p0=p0)
                except RuntimeError as error:
                    attempts.append(dict(factor=factor,start=label,error=str(error)))
                    continue
                factor_used=factor;fallback=label=='cold' and prior is not None;weights=trial
                break
            if result is not None:break
        if result is None:
            (path/f'rejected-update-{step:03d}.json').write_text(json.dumps(attempts,indent=2)+'\n')
            raise RuntimeError(f'No unchanged-tolerance root after guarded step at month {month}, update {step}')
        metrics,gq,gp=data_loss(market,result,price_target,observed,fixed,ci,ti,
                                flow_target,flow_mask)
        noflow=missing_zone[hours]&np.isfinite(price_target)
        metrics.update(step=step,missing_flow_price_cells=int(noflow.sum()),
            missing_flow_price_mae=float(abs(result['prices'][noflow]-price_target[noflow]).mean()) if noflow.any() else None,
            certificate=result['certificate'],solve_seconds=result['seconds'],
            root_recoveries=result['coordinate_recoveries'],fallback=fallback,
            neighbor_start_hours=result['neighbor_start_hours'],
            accepted_step_fraction=factor_used,rejected_attempts=attempts,
            elapsed_seconds=time.perf_counter()-began)
        history.append(metrics)
        print('FIT',month,step,metrics['price_mae'],metrics['generation_mae_gw'],
              metrics['mix_share_mae'],metrics['missing_flow_price_mae'],flush=True)
        if step==updates:
            journal.write_text(json.dumps(history,indent=2)+'\n')
            break
        hourly,info=market.backward(theta,result,gq,gp)
        metrics['gradient_identification']=info
        metrics['projected_unidentified_gradient']=info['unidentified_rhs_max']>1e-8
        if metrics['projected_unidentified_gradient'] and not allow_projected_gradient:
            (path/f'unidentified-gradient-{step:03d}.json').write_text(json.dumps(metrics,indent=2)+'\n')
            raise ValueError('Unidentified price-gradient direction; fit stopped')
        gradient=np.zeros_like(weights)
        for g in range(ng):np.add.at(gradient[:,g],clock[:,g],hourly[:,g])
        gradient+=.0002*(weights-initial)/weights.size
        if not np.isfinite(gradient).all():raise ValueError('Nonfinite gradient')
        first=.9*first+.1*gradient;second=.999*second+.001*gradient**2;t=step+1
        previous=weights.copy()
        weights-=rate*(first/(1-.9**t))/(np.sqrt(second/(1-.999**t))+1e-8)
        prior=result['prices']
        journal.write_text(json.dumps(history,indent=2)+'\n')
        np.savez_compressed(checkpoint,weights=weights,previous=previous,first=first,
                            second=second,prior=prior,has_prior=True,step=step+1)
    return dict(month=month,updates=updates,rate=rate,
                allow_projected_gradient=allow_projected_gradient,
                projected_gradient_updates=sum(bool(item.get('projected_unidentified_gradient')) for item in history),
                seconds=time.perf_counter()-began,
                initial=history[0],final=history[-1]),weights,history


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--months',type=int,nargs='+',default=[1])
    parser.add_argument('--updates',type=int,default=3);parser.add_argument('--rate',type=float,default=.05)
    parser.add_argument('--allow-projected-gradient',action='store_true',
                        help='Research-only: report and project unidentified price directions.')
    args=parser.parse_args()
    state,old,_,_=setup();s,d,*_=state
    market=RecoveredTransportMarket(old.zones,old.groups,old.lower,old.upper,
        old.edges,old.capacity,old.source,old.load,cost=old.cost,
        thermal_tau=old.thermal_tau,renewable_tau=old.renewable_tau,
        flow_tau=old.flow_tau)
    _,covered,_,observed_flow=observed_exchanges(s['zones'],market.edges,return_edges=True)
    known=np.isfinite(observed_flow)
    flow_mask=known&(observed_flow>=market.lower-1e-8)&(observed_flow<=market.upper+1e-8)
    out=DEST/f'mixed-flow-monthly-v1-u{args.updates}-r{args.rate:g}';out.mkdir(exist_ok=True)
    for month in args.months:
        path=out/f'month-{month:02d}';path.mkdir(exist_ok=True)
        if (path/'summary.json').exists():
            print('SKIP',month,'complete',flush=True);continue
        try:
            summary,weights,history=fit(month,args.updates,args.rate,market,s,d,
                                        observed_flow,flow_mask,~covered,path,
                                        allow_projected_gradient=args.allow_projected_gradient)
        except Exception:
            (path/'failure.json').write_text(json.dumps(dict(month=month,
                traceback=traceback.format_exc()),indent=2)+'\n')
            raise
        np.savez_compressed(path/'curves.npz',weights=weights)
        (path/'history.json').write_text(json.dumps(history,indent=2)+'\n')
        (path/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        print('MONTH',month,summary['seconds'],flush=True)


if __name__=='__main__':main()
