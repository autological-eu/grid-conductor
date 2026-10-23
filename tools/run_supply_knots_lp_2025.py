"""Fit explicit supply-level nodes, evaluate through the original European LP."""
import fcntl
import json
import resource
import time
import traceback
import numpy as np
from sigmoid_month_pairs_2025 import ROOT,OUT as SOURCE,FAMILIES,EMBER,digest,write,split,metric
from differentiable_spline_clearing import BASIS
from spline_europe_2025 import backward
from run_differentiable_spline_2025 import atomic_json,targets,fixed_month,source_guesses
from supply_knot_splines_2025 import KNOTS,initial_parameters
from supply_knot_network_2025 import load,clear_hour,clear_lp,generation

PLAN=ROOT/'config/supply-knots-lp-2025.json'
OUT=ROOT/'data/bidding-zone-network-2025/supply-knots-lp-v1'
OLD=ROOT/'data/bidding-zone-network-2025/differentiable-spline-v1'


def warm_parameters(sealed,source_capacity,train,test):
    prior=np.array(json.loads((OLD/f'proposal-{train:02d}.json').read_text())['theta'])
    theta=initial_parameters(len(sealed['groups']));hours,_=split(train,test)
    for c in range(len(theta)):
        ids=np.flatnonzero(np.array(sealed['mapping'])==c);j=max(ids,key=lambda j:source_capacity[hours,j].sum())
        row=prior[sealed['original_groups'][j]['parameter']];theta[c,:5]=row[:5]
        weights=.001+20*np.logaddexp(0,row[5:]);prices=BASIS.evaluate(KNOTS)[0]@weights
        increments=np.diff(prices);theta[c,5:]=np.log(np.expm1(np.maximum(increments-.001,1e-10)/20))
    return theta


def joint_loss(sealed,data,source_capacity,design,theta,neutral,prices,values,hours,month_hours,target,fixed):
    mask=np.isfinite(target['prices']);error=prices-target['prices'];eps=design['price_smooth_absolute_epsilon'];scale=design['price_scale_eur_mwh']
    gp=np.zeros_like(prices);gp[mask]=error[mask]/np.sqrt(error[mask]**2+eps**2)/mask.sum()/scale
    pl=float((np.sqrt(error[mask]**2+eps**2)-eps).mean()/scale)
    monthly=fixed.copy();factor=month_hours/len(hours)/1000;shares=[]
    for j,g in enumerate(sealed['original_groups']):
        c=sealed['mapping'][j];share=np.divide(source_capacity[hours,j],data['capacity'][hours,c],out=np.zeros(len(hours)),where=data['capacity'][hours,c]>0);shares.append(share)
        monthly[g['country_id'],FAMILIES.index(g['family'])]+=(values[:,c]*share).sum()*factor
    known=np.isfinite(target['ember']);normal=np.maximum(target['ember'],design['generation_floor_twh']);err=(monthly[known]-target['ember'][known])/normal[known];eps=design['generation_smooth_absolute_epsilon']
    gl=float((np.sqrt(err**2+eps**2)-eps).mean());dm=np.zeros_like(monthly);dm[known]=err/np.sqrt(err**2+eps**2)/normal[known]/known.sum()
    gx=np.zeros_like(values)
    for j,g in enumerate(sealed['original_groups']):gx[:,sealed['mapping'][j]]+=shares[j]*factor*dm[g['country_id'],FAMILIES.index(g['family'])]
    delta=theta-neutral;ridge=design['ridge']*float(np.mean(delta**2));direct=2*design['ridge']*delta/delta.size
    return pl+gl+ridge,gx,gp,direct,dict(price_loss=pl,generation_loss=gl,ridge=ridge)


def guesses(sealed,month):
    old=source_guesses(json.loads((SOURCE/'inputs.json').read_text()),month);count=len(sealed['original_groups']);mapping=sealed['mapping'];out={}
    for hour,value in old.items():
        q=np.bincount(mapping,weights=value[:count],minlength=len(sealed['groups']));out[hour]=np.r_[q,value[count:]]
    return out


def fit(sealed,data,A,source_capacity,design,train,test):
    path=OUT/f'proposal-{train:02d}.json'
    if path.exists():return np.array(json.loads(path.read_text())['theta'])
    full,_=split(train,test);rng=np.random.default_rng(design['seed']+train);hours=np.sort(rng.choice(full,size=design['training_hours'],replace=False))
    target=targets(data,hours,train);fixed=fixed_month(sealed,data,full);initial=guesses(sealed,train)
    neutral=initial_parameters(len(sealed['groups']));theta=warm_parameters(sealed,source_capacity,train,test)
    best=theta.copy();best_loss=np.inf;history=[];m=np.zeros_like(theta);v=m.copy();began=time.perf_counter();checkpoint=OUT/f'fit-{train:02d}.npz';start=0
    if checkpoint.exists():
        with np.load(checkpoint) as z:theta=z['theta'];best=z['best'];best_loss=float(z['best_loss']);m=z['m'];v=z['v'];start=int(z['step'])
        history=json.loads((OUT/f'history-{train:02d}.json').read_text())
    for step in range(start,design['updates']+1):
        results=[clear_hour(sealed,data,A,theta,int(h),initial[int(h)]) for h in hours]
        pp=np.array([r['prices'] for r in results]);xx=np.array([r['full_x'] for r in results])
        loss,gx,gp,direct,parts=joint_loss(sealed,data,source_capacity,design,theta,neutral,pp,xx,hours,len(full),target,fixed)
        if loss<best_loss:best_loss=loss;best=theta.copy()
        row=dict(step=step,loss=loss,**parts,seconds=time.perf_counter()-began);history.append(row)
        atomic_json(OUT/f'history-{train:02d}.json',history);print('FIT',train,row,flush=True)
        if step==design['updates']:break
        gradient=direct.copy()
        for k,r in enumerate(results):gradient+=backward(r,gx[k],gp[k])
        if not np.isfinite(gradient).all():raise ValueError('Invalid gradient')
        m=.9*m+.1*gradient;v=.999*v+.001*gradient**2;t=step+1
        theta-=design['learning_rate']*(m/(1-.9**t))/(np.sqrt(v/(1-.999**t))+1e-8)
        np.savez_compressed(checkpoint,theta=theta,best=best,best_loss=best_loss,m=m,v=v,step=t)
    atomic_json(path,dict(train=train,test=test,training_hours=hours.tolist(),theta=best.tolist(),history=history,selected_training_loss=best_loss,
                          initialization_sha256=digest(OLD/f'proposal-{train:02d}.json'),config_sha256=digest(PLAN),selection='minimum sampled odd-month loss only; bounded budget, not converged optimum'))
    return best


def run():
    OUT.mkdir(exist_ok=True);lock=(OUT/'job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    design=json.loads(PLAN.read_text());paths=[PLAN,SOURCE/'inputs.json',SOURCE/'inputs.npz',SOURCE/'network.npz']+[ROOT/'tools'/n for n in ['supply_knot_splines_2025.py','supply_knot_network_2025.py','run_supply_knots_lp_2025.py','differentiable_spline_clearing.py','spline_europe_2025.py','run_differentiable_spline_2025.py']]+[OLD/f'proposal-{m:02d}.json' for m in range(1,13,2)]
    provenance={str(p.relative_to(ROOT)):digest(p) for p in paths};receipt=OUT/'provenance.json'
    if receipt.exists() and json.loads(receipt.read_text())!=provenance:raise ValueError('Changed sealed experiment; use fresh root')
    atomic_json(receipt,provenance);sealed,data,A,emergency,source_capacity=load();began=time.perf_counter();records=[]
    atomic_json(OUT/'layout.json',dict(groups=sealed['groups'],mapping=sealed['mapping'],source_groups=sealed['original_groups'],count=len(sealed['groups']),capacity_partition_error_mw=float(abs(data['capacity'].sum(axis=1)-source_capacity.sum(axis=1)).max())))
    for train,test in design['pairs']:
        record_path=OUT/f'pair-{train:02d}-{test:02d}.json'
        if record_path.exists():records.append(json.loads(record_path.read_text()));continue
        atomic_json(OUT/'progress.json',dict(stage='fit',train=train,test=test));theta=fit(sealed,data,A,source_capacity,design,train,test);frozen=digest(OUT/f'proposal-{train:02d}.json')
        _,hours=split(train,test);row=dict(train=train,test=test,hours=len(hours),proposal_sha256=frozen,cases={})
        for kind,state in [('learned',theta),('control',initial_parameters(len(theta)))]:
            atomic_json(OUT/'progress.json',dict(stage='LP-evaluation',train=train,test=test,kind=kind,hours=len(hours)))
            path=OUT/f'test-{test:02d}-{kind}.npz'
            if path.exists():
                with np.load(path) as z:w={k:z[k] for k in z.files}
                info=json.loads(path.with_suffix('.json').read_text())
            else:
                w,info=clear_lp(sealed,data,A,emergency,state,hours,design['lp_tranches_per_curve'])
                w['generation']=generation(sealed,data,source_capacity,w['quantities'],hours)
                np.savez_compressed(path,**w);atomic_json(path.with_suffix('.json'),info)
            metrics,monthly=metric(sealed,data,w['row_duals'][:,:sealed['nz']],w['generation'],hours,test)
            row['cases'][kind]=dict(metrics=metrics,monthly_generation_twh=monthly.tolist(),witness_sha256=digest(path),info=info)
        accepted,_=metric(sealed,data,data['accepted_prices'][hours],data['accepted_generation'][hours],hours,test);row['accepted_insample_context']=accepted
        if digest(OUT/f'proposal-{train:02d}.json')!=frozen:raise ValueError('Proposal changed during test')
        atomic_json(record_path,row);records.append(row);atomic_json(OUT/'summary.json',dict(status='complete' if len(records)==6 else 'partial',pairs=records,seconds=time.perf_counter()-began))
        print('PAIR',train,test,{k:v['metrics'] for k,v in row['cases'].items()},flush=True)
    atomic_json(OUT/'progress.json',dict(stage='complete',pairs=6,test_hours=4344))


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,)*2)
    try:run()
    except Exception:
        if OUT.exists():atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()))
        raise
