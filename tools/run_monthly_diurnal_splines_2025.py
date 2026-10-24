"""Full-month shared daily bids with a compiled differentiable dispatch trial."""
from concurrent.futures import ProcessPoolExecutor,as_completed
import fcntl,json,multiprocessing,os,time,traceback
from pathlib import Path
import numpy as np
import clarabel
import hourly_spline_reconstruction_2025 as base
import hourly_spline_numerical_recovery_2025 as recovery
import run_forward_hourly_splines_2025 as study
import condensed_spline_kkt_2025 as condensed
from clarabel_spline_dispatch_2025 import solve as compiled_solve,certificate,passed
from monthly_diurnal_splines_2025 import initialize,labels,expand,aggregate,penalties
from forward_hourly_splines_2025 import month_hours,polynomials,interval_bids
from run_differentiable_spline_2025 import atomic_json,targets,fixed_month
from sigmoid_month_pairs_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/monthly-diurnal-splines-v1'
PLAN=ROOT/'config/monthly-diurnal-splines-2025.json'
SEED=study.OUT/'month-01/iteration-000'


def provenance():
    paths=[PLAN,Path(__file__),ROOT/'config/differentiable-dispatch-requirements.txt']
    paths += [ROOT/'tools'/n for n in ['monthly_diurnal_splines_2025.py','clarabel_spline_dispatch_2025.py','pilot_monthly_diurnal_splines_2025.py','test_monthly_diurnal_splines_2025.py','report_monthly_diurnal_splines_2025.py','condensed_spline_kkt_2025.py']]
    paths += [SEED/'parameters.npy',SEED/'record.json',OUT/'pilot.json']
    pinned=study.provenance()
    pinned.update({str(p.relative_to(ROOT)):digest(p) for p in paths})
    return pinned


def forward(index,hour,statepath,stage,previous_stage):
    p=base.hour_problem(index,hour,statepath)
    path=Path(stage)/f'hour-{hour:04d}.npz'
    if path.exists():
        return recovery.replay_or_recover(index,hour,statepath,stage,previous_stage)+(dict(method='revalidated_cache'),)
    previous=None
    if previous_stage:
        with np.load(Path(previous_stage)/path.name) as z:previous={k:z[k] for k in ['x','nu','slack','lam']}
    began=time.perf_counter()
    try:
        r=compiled_solve(p['cost'],p,previous)
        info=dict(method=r.get('backend','compiled_qp'),qp_iterations=r.get('qp_iterations',0))
        if info['method']=='compiled_qp' and info['qp_iterations']==0:info['method']='certified_unchanged_optimum_reuse'
    except (RuntimeError,ValueError,FloatingPointError) as exc:
        r=study.safe_warm(p['cost'],p,previous)
        info=dict(method='original_newton_fallback',reason=str(exc))
    _,cert=certificate(p['cost'],p,r)
    if not passed(cert) or min(r['slack'].min(),r['lam'].min())<=0:raise ValueError('Unchanged nonlinear precision gates failed')
    s,_,A,_,_=base.STATE
    full=np.zeros(A.shape[1]);full[p['active']],full[p['fixed']]=r['x'],p['fixed_values']
    if abs(p['equality']@r['x']-p['full_b']).max(initial=0)*1000>1e-4:raise ValueError('Original physical equality failed')
    nu=np.zeros(len(p['full_b']));nu[p['equality_rows']]=r['nu']
    temp=path.with_suffix('.tmp.npz')
    np.savez(temp,**{k:r[k] for k in ['x','nu','slack','lam']});os.replace(temp,path)
    return index,-nu[:s['nz']],full,cert,r['iterations'],time.perf_counter()-began,None,info


def run():
    OUT.mkdir(exist_ok=True)
    lock=(OUT/'job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    pilot=json.loads((OUT/'pilot.json').read_text())
    if pilot['status']!='passed' or any(digest(ROOT/p)!=sha for p,sha in pilot['sources'].items()):raise ValueError('Current gradient/backend pilot required')
    pinned=provenance()
    if (OUT/'provenance.json').exists() and json.loads((OUT/'provenance.json').read_text())!=pinned:raise ValueError('Changed sealed experiment')
    atomic_json(OUT/'provenance.json',pinned)
    s,d,A,emergency,capacity=study.initialize();condensed.install()
    design=json.loads(PLAN.read_text());hours=month_hours(1);future=month_hours(2)
    clock=labels(s['groups'],hours);futureclock=labels(s['groups'],future)
    initial,active=initialize(s,d,hours)
    theta=initial.copy();m=np.zeros_like(theta);v=m.copy()
    np.testing.assert_array_equal(expand(theta,clock),np.load(SEED/'parameters.npy'))
    target=targets(d,hours,1);target['prices'][:,~np.isfinite(d['observed_prices']).all(axis=0)]=np.nan
    fixed=fixed_month(s,d,hours)
    zero=np.zeros((len(s['groups']),10));zero_bid=[g['technology'] in base.ZERO_TECH for g in s['groups']]
    history=json.loads((OUT/'history.json').read_text()) if (OUT/'history.json').exists() else []
    if history:
        with np.load(OUT/'resume.npz') as z:theta,m,v=z['theta'],z['m'],z['v']
    best_record=next((r for r in reversed(history) if r['improved']),None)
    best=best_record['forward']['metrics']['price_mae'] if best_record else float('inf');stale=history[-1]['stale'] if history else 0
    started=time.perf_counter()
    for step in range(len(history),design['maximum_updates']+1):
        stage=OUT/f'iteration-{step:03d}';stage.mkdir(exist_ok=True)
        checkpoint=stage/'optimizer-start.npz'
        if checkpoint.exists():
            with np.load(checkpoint) as z:theta,m,v=z['theta'],z['m'],z['v']
        else:study.atomic_npz(checkpoint,theta=theta,m=m,v=v)
        base.save_array(stage/'shared-parameters.npy',theta)
        hourly=expand(theta,clock);statepath=stage/'parameters.npy';base.save_array(statepath,hourly)
        if step==0:
            for h in hours:
                path=stage/f'hour-{h:04d}.npz'
                if not path.exists():os.link(SEED/path.name,path)
        previous=str(OUT/f'iteration-{step-1:03d}') if step else None
        prices=np.zeros((len(hours),s['nz']));values=np.zeros((len(hours),A.shape[1]));certs=[];methods={}
        began=time.perf_counter()
        with ProcessPoolExecutor(max_workers=2,initializer=base.worker_init,mp_context=multiprocessing.get_context('fork')) as pool:
            tasks=[pool.submit(forward,t,int(h),str(statepath),str(stage),previous) for t,h in enumerate(hours)]
            for done,f in enumerate(as_completed(tasks),1):
                t,p,x,cert,_,_,_,info=f.result();prices[t],values[t]=p,x;certs.append(cert)
                methods[info['method']]=methods.get(info['method'],0)+1
                if done%48==0 or done==len(hours):atomic_json(OUT/'progress.json',dict(stage='full-month-forward',iteration=step,completed_hours=done,total_hours=len(hours)))
            forward_seconds=time.perf_counter()-began
            loss,gx,gp,_,parts=base.joint_loss(s,d,capacity,design,zero,zero,prices,values,hours,len(hours),target,fixed)
            regularizer,direct,regparts=penalties(theta,initial,active,design)
            gradient_hourly=np.zeros_like(hourly);began=time.perf_counter()
            tasks=[pool.submit(base.backward_job,t,int(h),str(statepath),str(stage),gx[t],gp[t]) for t,h in enumerate(hours)]
            for done,f in enumerate(as_completed(tasks),1):
                t,g=f.result();gradient_hourly[t]=g
                if done%48==0 or done==len(hours):atomic_json(OUT/'progress.json',dict(stage='full-month-adjoint',iteration=step,completed_hours=done,total_hours=len(hours)))
            adjoint_seconds=time.perf_counter()-began
        gradient=(aggregate(gradient_hourly,clock)+direct)*active[:,:,None]
        if not np.isfinite(gradient).all():raise ValueError('Nonfinite shared gradient')
        frozen=digest(stage/'shared-parameters.npy')
        began=time.perf_counter()
        within=study.evaluate(s,d,A,emergency,capacity,hours,interval_bids(polynomials(hourly,zero_bid)),1,stage/'within.npz')
        prediction=expand(theta,futureclock)
        predicted=study.evaluate(s,d,A,emergency,capacity,future,interval_bids(polynomials(prediction,zero_bid)),2,stage/'forward.npz')
        if digest(stage/'shared-parameters.npy')!=frozen:raise ValueError('Model changed during inference')
        score=predicted['metrics']['price_mae'];improved=base.should_keep(score,best,design)
        if improved:best,stale=score,0
        else:stale+=1
        row=dict(iteration=step,loss=loss+regularizer,**parts,**regparts,gradient_norm=float(np.linalg.norm(gradient)),within=within,forward=predicted,
            improved=improved,stale=stale,forward_seconds=forward_seconds,adjoint_seconds=adjoint_seconds,lp_seconds=time.perf_counter()-began,
            methods=methods,smooth_certificate={k:max(c[k] for c in certs) for k in certs[0]},shared_parameter_sha256=frozen,
            hourly_parameter_sha256=digest(statepath),initial_witness_replay=step==0)
        m,v=.9*m+.1*gradient,.999*v+.001*gradient**2;t=step+1
        theta-=design['learning_rate']*(m/(1-.9**t))/(np.sqrt(v/(1-.999**t))+1e-8);theta[~active]=initial[~active]
        study.atomic_npz(OUT/'resume.npz',theta=theta,m=m,v=v,step=t)
        history.append(row);atomic_json(stage/'record.json',row)
        atomic_json(OUT/'history.json',history)
        print('ITERATION',step,'WITHIN',within['metrics'],'FORWARD',predicted['metrics'],'SECONDS',forward_seconds,adjoint_seconds,row['lp_seconds'],methods,flush=True)
        if stale>=design['patience']:break
    if provenance()!=pinned:raise ValueError('Producer changed during study')
    selected=min((r for r in history if r['improved']),key=lambda r:r['forward']['metrics']['price_mae'])
    atomic_json(OUT/'summary.json',dict(status='bounded_monthly_diurnal_test_complete',best_iteration=selected['iteration'],selected=selected,
        stop_reason='forward_patience' if stale>=3 else 'three_update_budget_not_convergence',shared_active_parameters=int(active.sum())*6,
        shared_nominal_parameters=initial.size,hourly_nominal_parameters=hourly.size,clarabel_version=clarabel.__version__,
        history_sha256=digest(OUT/'history.json'),seconds_this_session=time.perf_counter()-started,independent_audit='pending'))


if __name__=='__main__':
    try:run()
    except Exception:
        OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
