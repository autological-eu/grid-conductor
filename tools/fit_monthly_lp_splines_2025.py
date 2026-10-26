"""Twelve separate month-local-hour bid fits on accepted annual physical inputs."""
import fcntl
import json
import os
import time
from pathlib import Path

import numpy as np

from monthly_lp_spline_inputs_2025 import aligned,SOLAR
from conditional_monotone_market_2025 import ConditionalMarket
from hour_table_conditioner_2025 import feature_rows,initialize,regularizer
from run_hour_table_learning_rates_2025 import audit as audit_splines
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json,targets,fixed_month
from run_supply_knots_lp_2025 import joint_loss
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from supply_knot_network_2025 import generation

OUT=ROOT/'data/bidding-zone-network-2025/monthly-lp-splines-v1'
RATE=1.
UPDATES=100


def save(path,**values):
    temporary=path.with_suffix('.tmp.npz')
    with temporary.open('wb') as f:np.savez_compressed(f,**values)
    os.replace(temporary,path)


def month_fit(base,state,market,month):
    s,d,A,_,sourcecap=state
    folder=OUT/f'month-{month:02d}';folder.mkdir(exist_ok=True)
    if (folder/'complete.json').exists():return
    hours=month_hours(month);reference=market.reference
    X,centers=feature_rows(s['groups'],d,hours,reference)
    weights=initialize(market.ng);initial=weights.copy()
    active=(d['capacity'][hours]>0).any(axis=0)&~market.zero
    target=targets(d,hours,month)
    target['prices'][:,~np.isfinite(d['observed_prices']).all(axis=0)]=np.nan
    fixed=fixed_month(s,d,hours)
    design=dict(price_smooth_absolute_epsilon=1,price_scale_eur_mwh=40,
        generation_floor_twh=.25,generation_smooth_absolute_epsilon=.01,ridge=0)
    moment=np.zeros_like(weights);variance=np.zeros_like(weights);p0=None
    history=[];resume=folder/'resume.npz';start=0
    if resume.exists():
        with np.load(resume) as z:
            weights=z['weights'];moment=z['moment'];variance=z['variance'];p0=z['prices'];start=int(z['step'])
        history=json.loads((folder/'history.json').read_text())
        if len(history) not in (start,start+1):raise ValueError('Inconsistent fit journal')
        history=history[:start]
    else:
        save(resume,weights=weights,moment=moment,variance=variance,
             prices=np.zeros((len(hours),market.nz)),step=np.array(0))
    for step in range(start,UPDATES+1):
        began=time.perf_counter()
        theta=np.einsum('tgf,gfk->tgk',X,weights)
        result=market.solve(theta,hours,p0=p0)
        quantities=np.zeros((len(hours),A.shape[1]))
        quantities[:,:market.ng]=result['quantities_gw']
        loss,gx,gp,_,parts=joint_loss(s,d,sourcecap,design,np.zeros((1,1)),
            np.zeros((1,1)),result['prices'],quantities,hours,len(hours),target,fixed)
        penalty,direct=regularizer(weights,initial,active)
        score,monthly=metric(s,d,result['prices'],
            generation(s,d,sourcecap,result['quantities_gw']*1000,hours),hours,month)
        record=dict(update=step,loss=float(loss+penalty),regularizer=float(penalty),
            price_mae=float(score['price_mae']),generation_mae_twh=float(score['generation_mae_twh']),
            price_loss=float(parts['price_loss']),generation_loss=float(parts['generation_loss']),
            seconds=float(time.perf_counter()-began))
        if step in (0,25,50,75,100):
            record['certificate']=audit_splines(market,theta,result)
            save(folder/f'state-{step:03d}.npz',weights=weights,prices=result['prices'],
                 quantities_gw=result['quantities_gw'],hours=hours,centers=centers)
        history.append(record);atomic_json(folder/'history.json',history)
        atomic_json(OUT/'progress.json',dict(month=month,update=step,price_mae=record['price_mae'],
                                              generation_mae_twh=record['generation_mae_twh']))
        print('FIT',month,step,record['price_mae'],record['generation_mae_twh'],flush=True)
        if step==UPDATES:break
        hourly,info=market.backward(theta,result,gx[:,:market.ng],gp)
        if info['unidentified_rhs_max']>1e-8:raise ValueError('Unidentified price gradient')
        gradient=np.einsum('tgf,tgk->gfk',X,hourly)+direct
        gradient[~active]=0
        if not np.isfinite(gradient).all():raise ValueError('Nonfinite gradient')
        moment=.9*moment+.1*gradient;variance=.999*variance+.001*gradient**2;t=step+1
        weights-=RATE*(moment/(1-.9**t))/(np.sqrt(variance/(1-.999**t))+1e-8)
        p0=result['prices']
        save(resume,weights=weights,moment=moment,variance=variance,prices=p0,step=np.array(step+1))
    atomic_json(folder/'complete.json',dict(status='month_100_updates_complete',month=month,
        points=len(history),final_price_mae=history[-1]['price_mae'],
        final_generation_mae_twh=history[-1]['generation_mae_twh'],
        final_state_sha256=digest(folder/'state-100.npz')))


def main():
    OUT.mkdir(exist_ok=True)
    lock=(OUT/'job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    base,state,market,network,design=aligned()
    market.__class__=ConditionalMarket
    market.reference=np.maximum(market.capacity.max(axis=0),.001)
    sources=base.provenance()
    for path in [Path(__file__),ROOT/'tools/monthly_lp_spline_inputs_2025.py',
                 ROOT/'tools/conditional_monotone_market_2025.py',
                 ROOT/'tools/hour_table_conditioner_2025.py',SOLAR,
                 ROOT/'config/active-research-baseline.json']:
        sources[str(path.relative_to(ROOT))]=digest(path)
    if (OUT/'sources.json').exists():
        if json.loads((OUT/'sources.json').read_text())!=sources:
            raise ValueError('Changed source during saved monthly fits')
    else:atomic_json(OUT/'sources.json',sources)
    for month in range(1,13):month_fit(base,state,market,month)
    if any(digest(ROOT/path)!=sha for path,sha in sources.items()):
        raise ValueError('Changed source during fit')
    atomic_json(OUT/'complete.json',dict(status='twelve_monthly_fits_completed',
        updates_per_month=UPDATES,rate=RATE,months=list(range(1,13)),
        source_sha256=digest(OUT/'sources.json'),
        caveat='In-sample price/generation fit in a differentiable market; annual LP replay separate'))


if __name__=='__main__':main()
