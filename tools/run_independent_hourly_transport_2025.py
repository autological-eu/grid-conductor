"""Neutral independent-hour fast fitting, forward patience, physical replay."""
import fcntl
import json
import time
import traceback
from pathlib import Path
import numpy as np
import run_fast_fit_physical_transfer_2025 as reference
from independent_hourly_transport_2025 import initialize, penalties, project, transferred, physical_clear, economic_nodes
from forward_hourly_splines_2025 import month_hours, clock_slots
from sigmoid_month_pairs_2025 import ROOT, digest, metric
from run_differentiable_spline_2025 import atomic_json, targets, fixed_month
from run_supply_knots_lp_2025 import joint_loss
from supply_knot_network_2025 import generation

OUT = ROOT/'data/bidding-zone-network-2025/independent-hourly-transport-v1'
PLAN = ROOT/'config/independent-hourly-transport-2025.json'


def setup():
    base = reference.setup_controller()
    return base, base.setup()


def provenance(base):
    result = base.provenance()
    paths = [PLAN, Path(__file__), ROOT/'tools/independent_hourly_transport_2025.py',
             ROOT/'tools/test_independent_hourly_transport_2025.py',
             ROOT/'tools/pilot_independent_hourly_transport_2025.py',OUT/'pilot.json',
             reference.OUT/'refined-physical/provenance.json',reference.OUT/'refined-physical/summary.json',
             reference.OUT/'refined-physical/february-000.npz',reference.OUT/'refined-physical/february-000.json']
    result.update({str(p.relative_to(ROOT)):digest(p) for p in paths})
    return result


def score(state, result, month):
    s,d,_,_,capacity = state
    generated = generation(s,d,capacity,result['quantities_gw']*1000,result['hours'])
    metrics, monthly = metric(s,d,result['prices'],generated,result['hours'],month)
    return dict(metrics=metrics,monthly_generation_twh=monthly.tolist(),certificate=result['certificate'],
                seconds=result['seconds']), generated


def fit(base, state, market, design):
    s,d,A,_,capacity = state; hours=month_hours(1); future=month_hours(2)
    initial,active=initialize(s,d,hours); theta=initial.copy();m=np.zeros_like(theta);v=m.copy()
    slots=clock_slots(s['groups'],hours); zero=np.zeros((market.ng,10))
    target=targets(d,hours,1);target['prices'][:,~np.isfinite(d['observed_prices']).all(axis=0)]=np.nan
    fixed=fixed_month(s,d,hours)
    history=json.loads((OUT/'history.json').read_text()) if (OUT/'history.json').exists() else []
    with np.load(reference.PARENT/'annual.npz') as annual:
        p0=annual['prices'][hours];fp0=annual['prices'][future]
    if history:
        with np.load(OUT/'resume.npz') as z:theta,m,v=z['theta'],z['m'],z['v']
        for name in ['within','forward']:
            with np.load(OUT/f"iteration-{len(history)-1:03d}/{name}.npz") as z:
                if name=='within':p0=z['prices']
                else:fp0=z['prices']
    best=min((r['forward']['metrics']['price_mae'] for r in history if r['improved']),default=float('inf'))
    stale=history[-1]['stale'] if history else 0
    step=len(history)
    while stale<design['patience']:
        started=time.perf_counter();folder=OUT/f'iteration-{step:03d}';folder.mkdir(exist_ok=True)
        checkpoint=folder/'optimizer-start.npz'
        if checkpoint.exists():
            with np.load(checkpoint) as z:theta,m,v=z['theta'],z['m'],z['v']
        else:base.save(checkpoint,theta=theta,m=m,v=v)
        base.save(folder/'parameters.npz',theta=theta)
        atomic_json(OUT/'progress.json',dict(stage='independent-hourly-fit',iteration=step,training_hours=744,prediction_hours=672,zones=48))
        began=time.perf_counter();r=market.solve(theta,hours,p0=p0);forward_seconds=time.perf_counter()-began
        values=np.zeros((len(hours),A.shape[1]));values[:,:market.ng]=r['quantities_gw']
        loss,gx,gp,_,parts=joint_loss(s,d,capacity,design,zero,zero,r['prices'],values,hours,len(hours),target,fixed)
        regularizer,direct,regparts=penalties(theta,initial,active,design)
        began=time.perf_counter();hourly,gradinfo=market.backward(theta,r,gx[:,:market.ng],gp)
        if gradinfo['unidentified_rhs_max']>1e-8:raise ValueError('Observed target projects onto unidentified prices')
        gradient=(hourly+direct)*active[:,:,None];backward_seconds=time.perf_counter()-began
        if not np.isfinite(gradient).all():raise ValueError('Invalid hourly gradient')
        within,gen=score(state,r,1)
        began=time.perf_counter();profile,support=project(theta,d['capacity'][hours],slots,initial[0])
        prediction_parameters=transferred(profile,s['groups'],future);projection_seconds=time.perf_counter()-began
        base.save(folder/'profile.npz',theta=profile,support=support)
        rr=market.solve(prediction_parameters,future,p0=fp0);forward,fg=score(state,rr,2)
        for name,result,generated in [('within',r,gen),('forward',rr,fg)]:
            base.save(folder/(name+'.npz'),hours=result['hours'],prices=result['prices'],quantities_gw=result['quantities_gw'],
                      flows_gw=result['flows_gw'],generation=generated)
        value=forward['metrics']['price_mae'];improved=value<best-design['minimum_price_improvement_eur_mwh']
        if improved:best,stale=value,0
        else:stale+=1
        record=dict(iteration=step,within=within,forward=forward,improved=improved,stale=stale,loss=loss+regularizer,
                    **parts,**regparts,gradient_identification=gradinfo,gradient_norm=float(np.linalg.norm(gradient)),
                    forward_seconds=forward_seconds,backward_seconds=backward_seconds,projection_seconds=projection_seconds,
                    prediction_seconds=rr['seconds'],initial_price_cache_reuse=step==0,
                    parameter_sha256=digest(folder/'parameters.npz'),profile_sha256=digest(folder/'profile.npz'),
                    within_sha256=digest(folder/'within.npz'),forward_sha256=digest(folder/'forward.npz'))
        m,v=.9*m+.1*gradient,.999*v+.001*gradient**2;t=step+1
        theta-=design['learning_rate']*(m/(1-.9**t))/(np.sqrt(v/(1-.999**t))+1e-8);theta[~active]=initial[~active]
        base.save(OUT/'resume.npz',theta=theta,m=m,v=v,step=t)
        record['iteration_wall_seconds']=time.perf_counter()-started
        history.append(record);atomic_json(folder/'record.json',record);atomic_json(OUT/'history.json',history)
        p0,fp0=r['prices'],rr['prices']
        print('FIT',step,'JAN',within['metrics'],'FEB',forward['metrics'],'STALE',stale,'WALL',record['iteration_wall_seconds'],flush=True)
        step+=1
    selected=min((r for r in history if r['improved']),key=lambda r:r['forward']['metrics']['price_mae'])
    best_within=min(history,key=lambda r:r['within']['metrics']['price_mae'])
    result=dict(status='independent_hourly_forward_patience_complete',selected_iteration=selected['iteration'],
                last_iteration=history[-1]['iteration'],best_within_iteration=best_within['iteration'],stop_reason='three_forward_nonimprovements',
                nominal_parameters=initial.size,active_parameters=int(active.sum()*6),history_sha256=digest(OUT/'history.json'))
    atomic_json(OUT/'fit-summary.json',result)
    return result


def physical(base,state,market,summary):
    s,d,_,_,capacity=state;cases=[]
    selected=summary['selected_iteration'];folder=OUT/f'iteration-{selected:03d}'
    with np.load(folder/'profile.npz') as z:averaged_parameters=transferred(z['theta'],s['groups'],month_hours(1))
    with np.load(folder/'within.npz') as z:p0=z['prices']
    averaged_result=market.solve(averaged_parameters,month_hours(1),p0=p0)
    averaged_score,averaged_generation=score(state,averaged_result,1)
    base.save(OUT/'fast-averaged-within.npz',hours=averaged_result['hours'],prices=averaged_result['prices'],
              quantities_gw=averaged_result['quantities_gw'],flows_gw=averaged_result['flows_gw'],generation=averaged_generation)
    # Best-within is a separate diagnostic at the stopping time, not selection by future physical scores.
    pairs={(0,1),(summary['selected_iteration'],1),(summary['selected_iteration'],2),(summary['best_within_iteration'],1)}
    for step,month in sorted(pairs):
        path=OUT/f'physical-{step:03d}-{month:02d}.npz'
        if path.exists():
            record=json.loads(path.with_suffix('.json').read_text());assert digest(path)==record['witness_sha256'];cases.append(record);continue
        folder=OUT/f'iteration-{step:03d}';hours=month_hours(month)
        if month==1:
            with np.load(folder/'parameters.npz') as z:theta=z['theta']
        else:
            with np.load(folder/'profile.npz') as z:theta=transferred(z['theta'],s['groups'],hours)
        def progress(done,total):
            atomic_json(OUT/'progress.json',dict(stage='original-physical-LP100',iteration=step,month=month,done=done,total=total))
        witness,info=physical_clear(state,market,theta,hours,bins=100,progress=progress)
        gen=generation(s,d,capacity,witness['quantities_gw']*1000,hours);metrics,monthly=metric(s,d,witness['prices'],gen,hours,month)
        witness['generation']=gen;base.save(path,**witness)
        record=dict(iteration=step,month=month,hours=len(hours),metrics=metrics,monthly_generation_twh=monthly.tolist(),info=info,
                    witness_sha256=digest(path),curve_sha256=digest(folder/('parameters.npz' if month==1 else 'profile.npz')))
        atomic_json(path.with_suffix('.json'),record);cases.append(record);print('PHYSICAL',step,month,metrics,info,flush=True)
    neutral=reference.OUT/'refined-physical/february-000.npz'
    neutral_record=json.loads(neutral.with_suffix('.json').read_text())
    assert digest(neutral)==neutral_record['witness_sha256']
    # Initial independent curves are neutral; weekly averaging preserves every neutral economic node.
    with np.load(OUT/'iteration-000/profile.npz') as z:profile=z['theta']
    shared=np.load(reference.OUT/'iteration-000/shared-parameters.npy')
    future=month_hours(2);slots=clock_slots(s['groups'],future)
    np.testing.assert_allclose(economic_nodes(transferred(profile,s['groups'],future)),
                               economic_nodes(shared[slots%24,np.arange(market.ng)]),atol=1e-12,rtol=0)
    inherited=dict(neutral_record);inherited.update(month=2,cache_reuse=True,cached_path=str(neutral.relative_to(ROOT)))
    cases.append(inherited)
    step=summary['selected_iteration'];folder=OUT/f'iteration-{step:03d}'
    with np.load(folder/'parameters.npz') as z:within=z['theta']
    with np.load(folder/'profile.npz') as z:forward=transferred(z['theta'],s['groups'],future)
    probe_hours=np.array([15,111,318,567,759,815,900])
    raw=np.stack([within[h] if h<744 else forward[h-744] for h in probe_hours])
    coarse,info=physical_clear(state,market,raw,probe_hours,bins=20)
    base.save(OUT/'physical-coarse-probe.npz',**coarse);comparisons=[]
    complete=np.isfinite(d['observed_prices']).all(axis=0)
    for t,h in enumerate(probe_hours):
        month=1 if h<744 else 2
        with np.load(OUT/f'physical-{step:03d}-{month:02d}.npz') as fine:
            k=int(np.flatnonzero(fine['hours']==h)[0])
            comparisons.append(dict(hour=int(h),price_max_difference=float(abs(coarse['prices'][t,complete]-fine['prices'][k,complete]).max()),
                                    quantity_max_difference_mw=float(abs(coarse['quantities_gw'][t]-fine['quantities_gw'][k]).max()*1000)))
    atomic_json(OUT/'summary.json',dict(status='independent_hourly_fit_and_physical_transfer_complete',fit=summary,cases=cases,
                averaged_within=dict(**averaged_score,witness_sha256=digest(OUT/'fast-averaged-within.npz')),
                discretization_probe=dict(bins=20,hours=probe_hours.tolist(),info=info,comparisons=comparisons,
                    witness_sha256=digest(OUT/'physical-coarse-probe.npz')),independent_audit='pending'))
    atomic_json(OUT/'progress.json',dict(stage='independent-fit-and-physical-transfer-awaiting-audit',selected_iteration=step))


def run():
    OUT.mkdir(exist_ok=True);lock=(OUT/'job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (OUT/'summary.json').exists():raise ValueError('Completed study; do not duplicate')
    if (OUT/'failure.json').exists():raise ValueError('Inspect failed study before resuming')
    pilot=json.loads((OUT/'pilot.json').read_text());assert pilot['status']=='passed'
    assert all(digest(ROOT/p)==sha for p,sha in pilot['sources'].items())
    base,(state,market,network,_)=setup();pinned=provenance(base)
    if (OUT/'provenance.json').exists():assert json.loads((OUT/'provenance.json').read_text())==pinned
    atomic_json(OUT/'provenance.json',pinned);atomic_json(OUT/'network.json',network)
    design=json.loads(PLAN.read_text())
    summary=json.loads((OUT/'fit-summary.json').read_text()) if (OUT/'fit-summary.json').exists() else fit(base,state,market,design)
    physical(base,state,market,summary)
    assert pinned==provenance(base)


if __name__=='__main__':
    try:run()
    except Exception:
        OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
