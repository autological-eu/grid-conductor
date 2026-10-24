"""Full-resolution annual transport screen and January/February gradient trial."""
import fcntl,json,os,time,traceback
from pathlib import Path
import numpy as np
from batched_transport_dispatch_2025 import TransportMarket
from compile_transport_corridors_2025 import compile_corridors
from supply_knot_network_2025 import load,generation
from supply_knot_splines_2025 import initial_parameters
from monthly_diurnal_splines_2025 import initialize,labels,expand,aggregate,penalties
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json,targets,fixed_month
from run_supply_knots_lp_2025 import joint_loss
from sigmoid_month_pairs_2025 import ROOT,digest,metric
import run_forward_hourly_splines_2025 as old

OUT=ROOT/'data/bidding-zone-network-2025/batched-transport-dispatch-v1'
PLAN=ROOT/'config/batched-transport-dispatch-2025.json'


def setup():
    state=load();s,d,A,emergency,capacity=state
    design=json.loads(PLAN.read_text())
    edges,lo,hi,info=compile_corridors(s,d)
    if len(s['zones'])!=design['zones'] or len(d['load'])!=design['annual_hours']:raise ValueError('No zone/hour reduction permitted')
    market=TransportMarket(s['zones'],s['groups'],lo,hi,edges,d['capacity']/1000,d['source_cost'],d['load']/1000,
        cost=design['transport_cost_eur_mwh_per_gw'],thermal_tau=design['thermal_smoothing_eur_mwh'],renewable_tau=design['renewable_smoothing_eur_mwh'],flow_tau=design['flow_smoothing_gw'])
    return state,market,info,design


def provenance():
    paths=[PLAN,Path(__file__),OUT/'pilot.json']+[ROOT/'tools'/n for n in ['batched_transport_dispatch_2025.py','compile_transport_corridors_2025.py','test_batched_transport_dispatch_2025.py','pilot_batched_transport_2025.py','report_batched_transport_2025.py','monthly_diurnal_splines_2025.py']]
    result=old.provenance()
    result.update({str(p.relative_to(ROOT)):digest(p) for p in paths})
    return result


def save(path,**values):
    temp=path.with_suffix('.tmp.npz');np.savez_compressed(temp,**values);os.replace(temp,path)


def result_metrics(state,result,month):
    s,d,_,_,capacity=state
    gen=generation(s,d,capacity,result['quantities_gw']*1000,result['hours'])
    score,monthly=metric(s,d,result['prices'],gen,result['hours'],month)
    return dict(metrics=score,monthly_generation_twh=monthly.tolist(),certificate=result['certificate'],seconds=result['seconds']),gen


def annual(state,market,design):
    if (OUT/'annual.json').exists():
        record=json.loads((OUT/'annual.json').read_text())
        if digest(OUT/'annual.npz')!=record['witness_sha256']:raise ValueError('Annual witness changed')
        with np.load(OUT/'annual.npz') as z:return record,{k:z[k] for k in z.files}
    s,d,_,_,_=state;theta=initial_parameters(len(s['groups']))[:,[0,5,6,7,8,9]]
    prices=[];q=[];flows=[];chunks=[];warm=None
    for month in range(1,13):
        hours=month_hours(month)
        atomic_json(OUT/'progress.json',dict(stage='annual-neutral-forward',month=month,hours=len(hours),total_hours=8760,zones=48))
        p0=None
        if warm is not None:
            clock=labels([dict(zone=z) for z in s['zones']],hours)
            p0=warm[clock,np.arange(market.nz)]
        r=market.solve(theta,hours,p0=p0)
        info,_=result_metrics(state,r,month);info.update(month=month,hours=len(hours),max_iterations=int(r['iterations'].max()))
        chunks.append(info);prices.append(r['prices']);q.append(r['quantities_gw']);flows.append(r['flows_gw'])
        previous=labels([dict(zone=z) for z in s['zones']],hours);warm=np.zeros((24,market.nz))
        for j in range(market.nz):
            for h in range(24):warm[h,j]=r['prices'][previous[:,j]==h,j].mean()
        print('ANNUAL_MONTH',month,r['seconds'],info['metrics'],flush=True)
    witness=dict(prices=np.concatenate(prices),quantities_gw=np.concatenate(q),flows_gw=np.concatenate(flows),hours=np.arange(8760))
    save(OUT/'annual.npz',**witness)
    mask=np.isfinite(d['observed_prices']).all(axis=0)
    cells=sum(r['metrics']['generation_cells'] for r in chunks)
    record=dict(status='annual_neutral_transport_forward_complete',hours=8760,zones=48,price_zones=int(mask.sum()),
        price_mae=float(abs(witness['prices'][:,mask]-d['observed_prices'][:,mask]).mean()),
        generation_mae_twh=sum(r['metrics']['generation_mae_twh']*r['metrics']['generation_cells'] for r in chunks)/cells,
        seconds=sum(r['seconds'] for r in chunks),months=chunks,witness_sha256=digest(OUT/'annual.npz'),
        scope='Full-year neutral forward screen only, not fitted annual forward validation or original-PTDF feasibility')
    atomic_json(OUT/'annual.json',record)
    return record,witness


def run():
    OUT.mkdir(exist_ok=True)
    lock=(OUT/'job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (OUT/'summary.json').exists():raise ValueError('Already complete; inspect saved results')
    pilot=json.loads((OUT/'pilot.json').read_text())
    if pilot['status']!='passed' or any(digest(ROOT/p)!=sha for p,sha in pilot['sources'].items()):raise ValueError('Current gradient pilot required')
    pinned=provenance()
    if (OUT/'provenance.json').exists() and json.loads((OUT/'provenance.json').read_text())!=pinned:raise ValueError('Changed sealed study')
    atomic_json(OUT/'provenance.json',pinned)
    state,market,network,design=setup();atomic_json(OUT/'network.json',network)
    year,y=annual(state,market,design)
    s,d,A,_,capacity=state;hours=month_hours(1);future=month_hours(2)
    theta,active=initialize(s,d,hours);initial=theta.copy();m=np.zeros_like(theta);v=m.copy()
    clock=labels(s['groups'],hours);fc=labels(s['groups'],future)
    target=targets(d,hours,1);target['prices'][:,~np.isfinite(d['observed_prices']).all(axis=0)]=np.nan
    fixed=fixed_month(s,d,hours);zero=np.zeros((len(s['groups']),10))
    history=json.loads((OUT/'history.json').read_text()) if (OUT/'history.json').exists() else []
    if history:
        with np.load(OUT/'resume.npz') as z:theta,m,v=z['theta'],z['m'],z['v']
    best_record=next((r for r in reversed(history) if r['improved']),None)
    best=best_record['forward']['metrics']['price_mae'] if best_record else float('inf');stale=history[-1]['stale'] if history else 0
    p0=y['prices'][hours];fp0=y['prices'][future]
    if history:
        with np.load(OUT/f"iteration-{len(history)-1:03d}/within.npz") as z:p0=z['prices']
        with np.load(OUT/f"iteration-{len(history)-1:03d}/forward.npz") as z:fp0=z['prices']
    for step in range(len(history),design['maximum_updates']+1):
        folder=OUT/f'iteration-{step:03d}';folder.mkdir(exist_ok=True)
        checkpoint=folder/'optimizer-start.npz'
        if checkpoint.exists():
            with np.load(checkpoint) as z:theta,m,v=z['theta'],z['m'],z['v']
        else:save(checkpoint,theta=theta,m=m,v=v)
        old.save_array(folder/'shared-parameters.npy',theta)
        atomic_json(OUT/'progress.json',dict(stage='full-month-gradient',iteration=step,training_hours=744,prediction_hours=672,zones=48))
        train=expand(theta,clock);began=time.perf_counter();r=market.solve(train,hours,p0=p0);forward_seconds=time.perf_counter()-began
        values=np.zeros((len(hours),A.shape[1]));values[:,:market.ng]=r['quantities_gw']
        loss,gx,gp,_,parts=joint_loss(s,d,capacity,design,zero,zero,r['prices'],values,hours,len(hours),target,fixed)
        regularizer,direct,regparts=penalties(theta,initial,active,design)
        began=time.perf_counter();hourly,gradinfo=market.backward(train,r,gx[:,:market.ng],gp)
        if gradinfo['unidentified_rhs_max']>1e-8:raise ValueError('Training target projects onto an unidentified price direction; no silent gradient masking')
        gradient=(aggregate(hourly,clock)+direct)*active[:,:,None];backward_seconds=time.perf_counter()-began
        if not np.isfinite(gradient).all():raise ValueError('Nonfinite gradient')
        within,gen=result_metrics(state,r,1)
        frozen=digest(folder/'shared-parameters.npy');rr=market.solve(expand(theta,fc),future,p0=fp0)
        prediction,fg=result_metrics(state,rr,2)
        if digest(folder/'shared-parameters.npy')!=frozen:raise ValueError('Parameters changed during evaluation')
        for name,result,generation_values in [('within',r,gen),('forward',rr,fg)]:
            save(folder/(name+'.npz'),prices=result['prices'],quantities_gw=result['quantities_gw'],flows_gw=result['flows_gw'],hours=result['hours'],generation=generation_values)
        score=prediction['metrics']['price_mae'];improved=old.base.should_keep(score,best,design)
        if improved:best,stale=score,0
        else:stale+=1
        record=dict(iteration=step,loss=loss+regularizer,**parts,**regparts,within=within,forward=prediction,improved=improved,stale=stale,
            forward_seconds=forward_seconds,backward_seconds=backward_seconds,prediction_seconds=rr['seconds'],gradient_norm=float(np.linalg.norm(gradient)),
            gradient_identification=gradinfo,initial_price_cache_reuse=step==0,parameter_sha256=frozen,
            within_sha256=digest(folder/'within.npz'),forward_sha256=digest(folder/'forward.npz'))
        m,v=.9*m+.1*gradient,.999*v+.001*gradient**2;t=step+1
        theta-=design['learning_rate']*(m/(1-.9**t))/(np.sqrt(v/(1-.999**t))+1e-8);theta[~active]=initial[~active]
        save(OUT/'resume.npz',theta=theta,m=m,v=v,step=t)
        history.append(record);atomic_json(folder/'record.json',record);atomic_json(OUT/'history.json',history)
        p0,fp0=r['prices'],rr['prices']
        print('FIT',step,'JAN',within['metrics'],'FEB',prediction['metrics'],'TIMES',forward_seconds,backward_seconds,rr['seconds'],flush=True)
        if stale>=design['patience']:break
    if provenance()!=pinned:raise ValueError('Producer changed while running')
    selected=min((r for r in history if r['improved']),key=lambda r:r['forward']['metrics']['price_mae'])
    atomic_json(OUT/'summary.json',dict(status='annual_neutral_and_bounded_monthly_transport_test_complete',annual=year,best_iteration=selected['iteration'],selected=selected,
        stop_reason='forward_patience' if stale>=3 else 'three_update_budget_not_convergence',history_sha256=digest(OUT/'history.json'),independent_audit='pending'))


if __name__=='__main__':
    try:run()
    except Exception:
        OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
