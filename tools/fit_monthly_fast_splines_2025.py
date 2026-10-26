"""Fit month-local-hour six-node bids in the batched transport model only."""
import fcntl
import json
import os
import time
import traceback
import multiprocessing
from pathlib import Path

import numpy as np

from monthly_lp_spline_inputs_2025 import aligned,SOLAR
from hour_table_conditioner_2025 import feature_rows
from supply_knot_splines_2025 import initial_parameters
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json,targets,fixed_month
from run_supply_knots_lp_2025 import joint_loss
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from supply_knot_network_2025 import generation

OUT=ROOT/'data/bidding-zone-network-2025/monthly-fast-splines-v4'
RATE=1.
UPDATES=100


def initial_weights(groups):
    neutral=initial_parameters(groups)[:,[0,5,6,7,8,9]]
    weights=np.zeros((groups,26,6))
    weights[:,:24]=neutral[:,None]
    return weights


def penalty(weights,initial,active):
    delta=(weights-initial)*active[:,None,None]
    n=max(1,int(active.sum())*weights.shape[1]*weights.shape[2])
    ridge=.001*float((delta*delta).sum())/n
    grad=.002*delta/n
    difference=np.roll(weights[:,:24],-1,axis=1)-weights[:,:24]
    difference*=active[:,None,None]
    nn=max(1,int(active.sum())*24*6)
    smooth=.001*float((difference*difference).sum())/nn
    derivative=.002*difference/nn
    grad[:,:24]+=np.roll(derivative,1,axis=1)-derivative
    return ridge+smooth,grad


def audit_fast(market,result):
    q=result['quantities_gw'];f=result['flows_gw'];h=result['hours']
    residual=q@market.Z+f@market.M-market.load[h]
    maximum=float(abs(residual).max()*1000)
    if maximum>=1e-4 or result['certificate']['emergency_mwh']!=0:
        raise ValueError('Fast transport balance or emergency gate failed')
    return result['certificate'] | dict(balance_mw=maximum)


def pilot_gradient(schema,data,market):
    hours=np.array([15,111,318,567,700])
    reference=np.maximum(market.capacity.max(axis=0),.001)
    X,_=feature_rows(schema['groups'],data,hours,reference)
    weights=initial_weights(market.ng)
    theta=np.einsum('tgf,gfk->tgk',X,weights)
    result=market.solve(theta,hours,tolerance=1e-11)
    rng=np.random.default_rng(73)
    gq=rng.normal(size=result['quantities_gw'].shape)
    gp=rng.normal(size=result['prices'].shape)
    gp[:,~np.isfinite(data['observed_prices']).all(axis=0)]=0
    gradient,info=market.backward(theta,result,gq,gp)
    direction=rng.normal(size=weights.shape)
    displacement=np.einsum('tgf,gfk->tgk',X,direction)
    exact=float((gradient*displacement).sum())
    values=[]
    for sign in (1,-1):
        perturbed=market.solve(theta+sign*1e-6*displacement,hours,
            p0=result['prices'],tolerance=1e-11)
        values.append(float((perturbed['quantities_gw']*gq).sum()+
            (perturbed['prices']*gp).sum()))
    finite=(values[0]-values[1])/2e-6
    error=abs(finite-exact)/max(1,abs(finite),abs(exact))
    if error>.001 or info['unidentified_rhs_max']>1e-8:
        raise ValueError('Fast conditional gradient pilot failed '+str((error,info)))
    return dict(scaled_error=float(error),balance=audit_fast(market,result))


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
    weights=initial_weights(market.ng);initial=weights.copy()
    active=(d['capacity'][hours]>0).any(axis=0)&~market.zero
    target=targets(d,hours,month)
    target['prices'][:,~np.isfinite(d['observed_prices']).all(axis=0)]=np.nan
    fixed=fixed_month(s,d,hours)
    design=dict(price_smooth_absolute_epsilon=1,price_scale_eur_mwh=40,
        generation_floor_twh=.25,generation_smooth_absolute_epsilon=.01,ridge=0)
    moment=np.zeros_like(weights);variance=np.zeros_like(weights);p0=None
    previous_weights=weights.copy()
    history=[];resume=folder/'resume.npz';start=0
    if resume.exists():
        with np.load(resume) as z:
            weights=z['weights'];moment=z['moment'];variance=z['variance'];p0=z['prices'];start=int(z['step'])
            previous_weights=z['previous_weights']
        journal=folder/'history.json'
        if not journal.exists() and start!=0:
            raise ValueError('Missing nonempty fit journal')
        history=json.loads(journal.read_text()) if journal.exists() else []
        if len(history) not in (start,start+1):raise ValueError('Inconsistent fit journal')
        history=history[:start]
    else:
        save(resume,weights=weights,previous_weights=previous_weights,moment=moment,variance=variance,
             prices=np.zeros((len(hours),market.nz)),step=np.array(0))
    for step in range(start,UPDATES+1):
        began=time.perf_counter()
        proposal=weights.copy();accepted_factor=1.;rejected=[]
        for factor in (1.,.5,.25,.125,.0625):
            weights=previous_weights+factor*(proposal-previous_weights)
            theta=np.einsum('tgf,gfk->tgk',X,weights)
            try:
                result=market.solve(theta,hours,p0=p0)
                accepted_factor=factor
                break
            except RuntimeError as error:
                rejected.append(dict(factor=factor,reason=str(error)))
        else:
            atomic_json(folder/f'rejected-update-{step:03d}.json',rejected)
            raise RuntimeError('No unchanged-tolerance market solution after guarded Adam proposal')
        quantities=np.zeros((len(hours),A.shape[1]))
        quantities[:,:market.ng]=result['quantities_gw']
        loss,gx,gp,_,parts=joint_loss(s,d,sourcecap,design,np.zeros((1,1)),
            np.zeros((1,1)),result['prices'],quantities,hours,len(hours),target,fixed)
        penalty_value,direct=penalty(weights,initial,active)
        score,monthly=metric(s,d,result['prices'],
            generation(s,d,sourcecap,result['quantities_gw']*1000,hours),hours,month)
        record=dict(update=step,loss=float(loss+penalty_value),regularizer=float(penalty_value),
            price_mae=float(score['price_mae']),generation_mae_twh=float(score['generation_mae_twh']),
            price_loss=float(parts['price_loss']),generation_loss=float(parts['generation_loss']),
            solve_seconds=float(result['seconds']),seconds=float(time.perf_counter()-began),
            adam_proposal_factor=accepted_factor,rejected_proposals=rejected)
        if step in (0,25,50,75,UPDATES):
            record['certificate']=audit_fast(market,result)
            save(folder/f'state-{step:03d}.npz',weights=weights,prices=result['prices'],
                 quantities_gw=result['quantities_gw'],hours=hours,centers=centers)
        if step<UPDATES:
            hourly,info=market.backward(theta,result,gx[:,:market.ng],gp)
            # An hour with saturated supply and corridors can have no unique
            # price derivative. The Moore-Penrose adjoint omits only that
            # unsupported direction. Keep its price error in the full score.
            eigen,vectors=np.linalg.eigh(result['jacobian'])
            threshold=np.maximum(1e-12,eigen[:,-1]*1e-12)
            unidentified=eigen<=threshold[:,None]
            if info['unidentified_rhs_max']>1e-8:
                dq=market.supply(result['prices'],market.offers(theta,hours),derivative=True)[1]
                rhs=gp+(gx[:,:market.ng]*dq)@market.Z
                projected=np.einsum('tji,tj->ti',vectors,rhs)
                affected=unidentified&(abs(projected)>1e-8)
                record['excluded_gradient_hours']=hours[affected.any(axis=1)].tolist()
                record['excluded_gradient_directions']=int(affected.sum())
            else:
                record['excluded_gradient_hours']=[]
                record['excluded_gradient_directions']=0
            record['gradient_identification']=info
        history.append(record);atomic_json(folder/'history.json',history)
        atomic_json(OUT/f'progress-month-{month:02d}.json',dict(month=month,update=step,price_mae=record['price_mae'],
                                              generation_mae_twh=record['generation_mae_twh']))
        print('FIT',month,step,record['price_mae'],record['generation_mae_twh'],flush=True)
        if step==UPDATES:break
        gradient=np.einsum('tgf,tgk->gfk',X,hourly)+direct
        gradient[~active]=0
        if not np.isfinite(gradient).all():raise ValueError('Nonfinite gradient')
        moment=.9*moment+.1*gradient;variance=.999*variance+.001*gradient**2;t=step+1
        previous_weights=weights.copy()
        weights-=RATE*(moment/(1-.9**t))/(np.sqrt(variance/(1-.999**t))+1e-8)
        p0=result['prices']
        save(resume,weights=weights,previous_weights=previous_weights,moment=moment,
             variance=variance,prices=p0,step=np.array(step+1))
    atomic_json(folder/'complete.json',dict(status='month_100_updates_complete',month=month,
        points=len(history),final_price_mae=history[-1]['price_mae'],
        final_generation_mae_twh=history[-1]['generation_mae_twh'],
        final_state_sha256=digest(folder/f'state-{UPDATES:03d}.npz')))


def main():
    OUT.mkdir(exist_ok=True)
    lock=(OUT/'job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (OUT/'failure.json').exists() or (OUT/'complete.json').exists():
        raise ValueError('Inspect prior terminal fit receipt; no implicit restart')
    base,state,market,network,design=aligned()
    market.reference=np.maximum(market.capacity.max(axis=0),.001)
    sources=base.provenance()
    for path in [Path(__file__),ROOT/'tools/monthly_lp_spline_inputs_2025.py',
                 ROOT/'tools/batched_transport_dispatch_2025.py',
                 ROOT/'tools/hour_table_conditioner_2025.py',SOLAR,
                 ROOT/'tools/run_monthly_fast_baseline_2025.py',
                 ROOT/'tools/monthly_fast_lp_costs_2025.py',
                 ROOT/'tools/clear_monthly_fast_lp_2025.py',
                 ROOT/'tools/audit_monthly_fast_lp_2025.py',
                 ROOT/'tools/pilot_monthly_fast_lp_2025.py',
                 ROOT/'data/bidding-zone-network-2025/monthly-fast-lp-pilot-v3/summary.json',
                 ROOT/'data/bidding-zone-network-2025/supply-bid-review-v2/offers.json',
                 ROOT/'data/bidding-zone-network-2025/supply-bid-review-v2/audit.json',
                 ROOT/'data/bidding-zone-network-2025/supply-bid-review-v2/summary.json',
                 ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json']:
        sources[str(path.relative_to(ROOT))]=digest(path)
    if (OUT/'sources.json').exists():
        if json.loads((OUT/'sources.json').read_text())!=sources:
            raise ValueError('Changed source during saved monthly fits')
    else:atomic_json(OUT/'sources.json',sources)
    if not (OUT/'pilot.json').exists():
        atomic_json(OUT/'pilot.json',pilot_gradient(state[0],state[1],market))
    def worker(months):
        for month in months:
            try:month_fit(base,state,market,month)
            except Exception:
                atomic_json(OUT/f'failure-month-{month:02d}.json',
                    dict(month=month,traceback=traceback.format_exc()))
                raise
    workers=[]
    context=multiprocessing.get_context('fork')
    for months in (range(1,13,2),range(2,13,2)):
        process=context.Process(target=worker,args=(months,))
        process.start();workers.append(process)
    for process in workers:process.join()
    if any(process.exitcode!=0 for process in workers):
        raise RuntimeError('Monthly fit worker failed; inspect per-month failure receipts')
    if any(digest(ROOT/path)!=sha for path,sha in sources.items()):
        raise ValueError('Changed source during fit')
    atomic_json(OUT/'complete.json',dict(status='twelve_monthly_fits_completed',
        updates_per_month=UPDATES,rate=RATE,months=list(range(1,13)),
        source_sha256=digest(OUT/'sources.json'),
        caveat='In-sample price/generation fit in a differentiable market; annual LP replay separate'))


if __name__=='__main__':
    try:main()
    except Exception:
        OUT.mkdir(exist_ok=True)
        atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()))
        raise
