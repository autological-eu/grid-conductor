"""Checkpointed end-to-end spline fitting and complete even-month evaluation.

Targets are explicitly sliced before fitting. No test targets are supplied to the
optimizer; proposals are written and hashed before test targets are scored.
"""
import argparse
import json
import os
import resource
import time
import traceback
from pathlib import Path
import numpy as np
from sigmoid_month_pairs_2025 import ROOT, OUT as SOURCE, FAMILIES, EMBER, split, metric, digest, write
from differentiable_spline_clearing import initial_parameters
from spline_europe_2025 import load, clear_hour, backward, quantities

PLAN=ROOT/'config/differentiable-spline-2025.json'
OUT=ROOT/'data/bidding-zone-network-2025/differentiable-spline-v1'


def atomic_json(path,value):
    temporary=Path(str(path)+'.tmp');write(temporary,value);os.replace(temporary,path)


def targets(data,hours,month):
    # Deliberately no data reference retained in this target-only structure.
    return dict(prices=data['observed_prices'][hours].copy(),ember=data['ember'][month-1].copy())


def loss(sealed,design,theta,neutral,prices,values,fixed,target,month_hours):
    """Smooth price MAE + normalized monthly energy MAE + parameter ridge.

The energy estimate expands sampled hours; fixed hydro's exact monthly total
is supplied separately. No invented hourly Ember generation observations.
Returns derivatives with respect to GW dispatch and EUR/MWh cleared prices.
"""
    mask=np.isfinite(target['prices']);error=prices-target['prices'];eps=design['price_smooth_absolute_epsilon']
    denom=max(1,int(mask.sum()));scale=design['price_scale_eur_mwh']
    gp=np.zeros_like(prices);gp[mask]=error[mask]/np.sqrt(error[mask]**2+eps**2)/denom/scale
    pl=float((np.sqrt(error[mask]**2+eps**2)-eps).sum()/denom/scale)
    monthly=fixed.copy();factor=month_hours/len(prices)/1000
    for j,g in enumerate(sealed['groups']):
        monthly[g['country_id'],FAMILIES.index(g['family'])]+=values[:,j].sum()*factor
    observed=target['ember'];known=np.isfinite(observed);normal=np.maximum(observed,design['generation_floor_twh'])
    err=(monthly[known]-observed[known])/normal[known];geps=design['generation_smooth_absolute_epsilon']
    gl=float((np.sqrt(err**2+geps**2)-geps).mean())
    dm=np.zeros_like(monthly);dm[known]=err/np.sqrt(err**2+geps**2)/normal[known]/known.sum()
    gx=np.zeros_like(values)
    for j,g in enumerate(sealed['groups']):gx[:,j]=factor*dm[g['country_id'],FAMILIES.index(g['family'])]
    delta=theta-neutral;ridge=design['ridge']*float(np.mean(delta**2));direct=2*design['ridge']*delta/delta.size
    return pl+gl+ridge,gx,gp,direct,dict(price_loss=pl,generation_loss=gl,ridge=ridge)


def fixed_month(sealed,data,hours):
    out=np.zeros((len(sealed['countries']),len(FAMILIES)))
    for f,family in enumerate(FAMILIES):
        ids=[sealed['technologies'].index(t) for t in EMBER[family]]
        out[:,f]=data['fixed_generation'][hours][:,:,ids].sum(axis=(0,2))/1e6
    return out


def source_guesses(sealed,month):
    summary=json.loads((SOURCE/'summary.json').read_text());pair=summary['pairs'][(month-1)//2]
    record=pair['witnesses']['train_control' if month%2 else 'test_control']
    path=ROOT/record['path']
    if digest(path)!=record['sha256']:raise ValueError('Changed physical initial witness')
    with np.load(path) as z:
        hours=z['hours'];v=z['values'];ng=len(sealed['groups']);K=sealed['design']['segments']
        full=np.c_[v[:,:ng*K].reshape(len(hours),ng,K).sum(axis=2),v[:,sealed['ng']:]]/1000
    return {int(h):full[i] for i,h in enumerate(hours)}


def sample_forward(sealed,data,A,theta,hours,guesses):
    results=[clear_hour(sealed,data,A,theta,int(h),guesses[int(h)]) for h in hours]
    return results,np.array([r['prices'] for r in results]),np.array([r['full_x'] for r in results])


def fit(sealed,data,A,design,train,test):
    path=OUT/f'proposal-{train:02d}.json'
    if path.exists():return np.array(json.loads(path.read_text())['theta'])
    train_hours,_=split(train,test);rng=np.random.default_rng(design['random_seed']+train)
    hours=np.sort(rng.choice(train_hours,size=design['training_hours_per_month'],replace=False))
    target=targets(data,hours,train);fixed=fixed_month(sealed,data,train_hours)
    guesses=source_guesses(sealed,train);neutral=initial_parameters(len(sealed['parameters']))
    theta=neutral.copy();m=np.zeros_like(theta);v=np.zeros_like(theta);history=[];began=time.perf_counter()
    checkpoint=OUT/f'fit-{train:02d}.npz';start=0
    if checkpoint.exists():
        with np.load(checkpoint) as z:theta=z['theta'];m=z['m'];v=z['v'];start=int(z['step'])
        history=json.loads((OUT/f'history-{train:02d}.json').read_text())
    for step in range(start,design['gradient_updates']+1):
        results,prices,values=sample_forward(sealed,data,A,theta,hours,guesses)
        total,gx,gp,direct,parts=loss(sealed,design,theta,neutral,prices,values,fixed,target,len(train_hours))
        record=dict(step=step,loss=total,**parts,elapsed_seconds=time.perf_counter()-began)
        history.append(record);atomic_json(OUT/f'history-{train:02d}.json',history)
        print('fit',train,record,flush=True)
        if step==design['gradient_updates']:break
        gradient=direct.copy()
        for k,r in enumerate(results):gradient+=backward(r,gx[k],gp[k])
        if not np.isfinite(gradient).all():raise ValueError('Nonfinite training adjoint')
        record['gradient_norm']=float(np.linalg.norm(gradient))
        m=.9*m+.1*gradient;v=.999*v+.001*gradient**2;t=step+1
        theta-=design['adam_learning_rate']*(m/(1-.9**t))/(np.sqrt(v/(1-.999**t))+1e-8)
        temporary=Path(str(checkpoint)+'.tmp.npz');np.savez_compressed(temporary,theta=theta,m=m,v=v,step=t);os.replace(temporary,checkpoint)
        atomic_json(OUT/f'history-{train:02d}.json',history)
    atomic_json(path,dict(train=train,test=test,training_hours=hours.tolist(),theta=theta.tolist(),history=history,
                        status='bounded_gradient_budget_complete_not_convergence_proof',config_sha256=digest(PLAN)))
    return theta


def evaluate(sealed,data,A,design,theta,train,test,kind):
    _,hours=split(train,test);guesses=source_guesses(sealed,test);folder=OUT/f'test-{test:02d}-{kind}';folder.mkdir(exist_ok=True)
    began=time.perf_counter();batch=design['checkpoint_hours'];values=[];prices=[]
    for offset in range(0,len(hours),batch):
        path=folder/f'{offset:04d}.npz';chunk=hours[offset:offset+batch]
        if not path.exists():
            results,pp,xx=sample_forward(sealed,data,A,theta,chunk,guesses)
            # Retain dual witnesses for an independent KKT replay, not only receipts.
            lengths=np.array([len(r['lam']) for r in results]);width=int(lengths.max())
            lam=np.zeros((len(chunk),width));slack=lam.copy();nu=np.zeros((len(chunk),56))
            for k,r in enumerate(results):
                lam[k,:lengths[k]]=r['lam'];slack[k,:lengths[k]]=r['slack'];nu[k,r['problem']['equality_rows']]=r['nu']
            temporary=Path(str(path)+'.tmp.npz')
            np.savez_compressed(temporary,hours=chunk,values=xx,prices=pp,lam=lam,slack=slack,lengths=lengths,nu=nu,
                                seconds=np.array([r['seconds'] for r in results]),certificates=np.array([list(r['certificate'].values()) for r in results]))
            os.replace(temporary,path)
        with np.load(path) as z:
            np.testing.assert_array_equal(z['hours'],chunk);values.append(z['values']);prices.append(z['prices'])
        atomic_json(OUT/'progress.json',dict(stage='test',train=train,test=test,kind=kind,completed_hours=offset+len(chunk),total_hours=len(hours),elapsed_seconds=time.perf_counter()-began))
        print('test',test,kind,offset+len(chunk),flush=True)
    xx=np.concatenate(values);pp=np.concatenate(prices);gen=quantities(sealed,data,xx,hours)
    metrics,monthly=metric(sealed,data,pp,gen,hours,test)
    atomic_json(folder/'summary.json',dict(metrics=metrics,monthly_generation_twh=monthly.tolist(),hours=len(hours),
                    chunks={p.name:digest(p) for p in sorted(folder.glob('*.npz'))},proposal_sha256=digest(OUT/f'proposal-{train:02d}.json')))
    return metrics


def run(fit_only=False):
    OUT.mkdir(exist_ok=True);design=json.loads(PLAN.read_text())
    dependencies=[PLAN]+[ROOT/'tools'/n for n in ['differentiable_spline_clearing.py','spline_europe_2025.py','run_differentiable_spline_2025.py']]
    provenance={str(p.relative_to(ROOT)):digest(p) for p in dependencies+[SOURCE/'inputs.json',SOURCE/'inputs.npz',SOURCE/'network.npz']}
    receipt=OUT/'provenance.json'
    if receipt.exists() and json.loads(receipt.read_text())!=provenance:raise ValueError('Changed sealed experiment; use fresh root')
    atomic_json(receipt,provenance);sealed,data,A=load();records=[]
    # Complete training before the expensive all-hour test phase.
    for train,test in design['pairs']:
        atomic_json(OUT/'progress.json',dict(stage='fit',train=train,test=test))
        fit(sealed,data,A,design,train,test)
    if fit_only:return
    for train,test in design['pairs']:
        theta=np.array(json.loads((OUT/f'proposal-{train:02d}.json').read_text())['theta'])
        learned=evaluate(sealed,data,A,design,theta,train,test,'learned')
        control=evaluate(sealed,data,A,design,initial_parameters(len(theta)),train,test,'control')
        records.append(dict(train=train,test=test,learned=learned,control=control))
        atomic_json(OUT/'summary.json',dict(status='complete' if len(records)==6 else 'partial',pairs=records))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fit-only',action='store_true');args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,)*2)
    try:run(args.fit_only)
    except Exception:
        if OUT.exists():atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()))
        raise
