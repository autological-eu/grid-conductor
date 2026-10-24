"""Twelve full-month fits and eleven strictly forward original-LP validations.

Restartable common epochs; monthly gradients never read adjacent-month targets.
Validation chooses the common epoch and patience only. Raw witnesses stay local.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import fcntl
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import hourly_spline_reconstruction_2025 as base
from hourly_spline_numerical_recovery_2025 import damped_solve
from supply_knot_splines_2025 import initial_parameters
from supply_knot_network_2025 import load, generation
from run_differentiable_spline_2025 import targets, fixed_month, atomic_json
from sigmoid_month_pairs_2025 import ROOT, OUT as SOURCE, digest, metric
from forward_hourly_splines_2025 import CachedKnotCost, month_hours, clock_slots, polynomials, project, interval_bids, clear_lp

OUT = ROOT/'data/bidding-zone-network-2025/forward-hourly-splines-v1'
PLAN = ROOT/'config/forward-hourly-splines-2025.json'
ORIGINAL_COST = base.cost_for
ORIGINAL_WARM = base.warm_solve


def cached_cost(*args, **kwargs):
    c = ORIGINAL_COST(*args, **kwargs)
    return CachedKnotCost(**{k:getattr(c,k) for k in c.__dataclass_fields__})


def safe_warm(cost, p, previous):
    try:
        return ORIGINAL_WARM(cost,p,previous)
    except (RuntimeError, ValueError, FloatingPointError):
        return damped_solve(cost,p,previous)


def initialize():
    base.STATE = load()
    base.cost_for = cached_cost
    base.warm_solve = safe_warm
    return base.STATE


def atomic_npz(path, **values):
    temporary = path.with_suffix('.tmp.npz')
    np.savez_compressed(temporary,**values)
    os.replace(temporary,path)


def provenance():
    files = [PLAN,Path(__file__),ROOT/'tools/forward_hourly_splines_2025.py']
    files += [ROOT/'tools'/n for n in ['hourly_spline_reconstruction_2025.py','hourly_spline_numerical_recovery_2025.py','supply_knot_network_2025.py','supply_knot_splines_2025.py','spline_europe_2025.py','differentiable_spline_clearing.py','run_supply_knots_lp_2025.py','run_differentiable_spline_2025.py','sigmoid_month_pairs_2025.py','intraday_offer_bids_2025.py','nve_hydro_diagnostics.py','run_regional_water_candidate_2025.py']]
    files += [ROOT/'tools'/n for n in ['pilot_forward_hourly_splines_2025.py','test_forward_hourly_splines_2025.py','audit_forward_hourly_splines_2025.py','report_forward_hourly_splines_2025.py','finish_forward_hourly_splines_2025.py','launch_forward_hourly_splines_2025.py']]
    files += [SOURCE/n for n in ['inputs.json','inputs.npz','network.npz']]
    return {str(p.relative_to(ROOT)):digest(p) for p in files}


def neutral_state(sealed,data,hours):
    shared = initial_parameters(len(sealed['groups']))
    theta,active = base.initialize(sealed,data,hours,shared)
    return theta,active,shared[:,base.FIELDS]


def evaluate(sealed,data,A,emergency,source_capacity,hours,bids,month,path):
    w,certificate = clear_lp(sealed,data,A,emergency,hours,bids)
    gen = generation(sealed,data,source_capacity,w['quantities'],hours)
    score,monthly = metric(sealed,data,w['row_duals'][:,:sealed['nz']],gen,hours,month)
    atomic_npz(path,**w,generation=gen)
    return dict(metrics=score,monthly_generation_twh=monthly.tolist(),certificate=certificate,witness_sha256=digest(path),hours=len(hours))


def fit_month(month,step,design,pool):
    sealed,data,A,emergency,source_capacity = base.STATE
    hours = month_hours(month)
    folder = OUT/f'month-{month:02d}'
    folder.mkdir(exist_ok=True)
    stage = folder/f'iteration-{step:03d}'
    stage.mkdir(exist_ok=True)
    recordpath = stage/'record.json'
    if recordpath.exists():
        record = json.loads(recordpath.read_text())
        if digest(folder/'resume.npz') != record['next_optimizer_sha256']:
            raise ValueError('Completed month checkpoint changed')
        return record
    initial,active,neutral = neutral_state(sealed,data,hours)
    theta,m,v = initial.copy(),np.zeros_like(initial),np.zeros_like(initial)
    if (folder/'resume.npz').exists():
        with np.load(folder/'resume.npz') as z:
            if int(z['step']) not in [step,step+1]:
                raise ValueError('Monthly epoch mismatch')
            # Crash after writing next optimizer, before record: replay this
            # epoch from its frozen parameters and previous optimizer below.
            if int(z['step']) == step:
                theta,m,v = z['theta'],z['m'],z['v']
    startpath = stage/'optimizer-start.npz'
    if startpath.exists():
        with np.load(startpath) as z: theta,m,v = z['theta'],z['m'],z['v']
    else:
        atomic_npz(startpath,theta=theta,m=m,v=v,step=step)
    statepath = stage/'parameters.npy'
    base.save_array(statepath,theta)
    previous = str(folder/f'iteration-{step-1:03d}') if step else None
    began = time.perf_counter()
    prices,values = np.zeros((len(hours),sealed['nz'])),np.zeros((len(hours),A.shape[1]))
    certificates = []
    futures = [pool.submit(base.forward_job,t,int(h),str(statepath),str(stage),previous) for t,h in enumerate(hours)]
    for done,future in enumerate(as_completed(futures),1):
        t,p,x,cert,_,_,_ = future.result()
        prices[t],values[t] = p,x
        certificates.append(cert)
        if done%48 == 0 or done==len(hours):
            atomic_json(OUT/'progress.json',dict(stage='monthly-full-batch-forward',iteration=step,month=month,completed_hours=done,total_hours=len(hours)))
    forward_seconds = time.perf_counter()-began
    target = targets(data,hours,month)
    target['prices'][:,~np.isfinite(data['observed_prices']).all(axis=0)] = np.nan
    zero = np.zeros((len(sealed['groups']),10))
    loss,gx,gp,_,parts = base.joint_loss(sealed,data,source_capacity,design,zero,zero,prices,values,hours,len(hours),target,fixed_month(sealed,data,hours))
    penalty,gradient,penalty_parts = base.penalties(theta,initial,active,design)
    began = time.perf_counter()
    futures = [pool.submit(base.backward_job,t,int(h),str(statepath),str(stage),gx[t],gp[t]) for t,h in enumerate(hours)]
    for done,future in enumerate(as_completed(futures),1):
        t,g = future.result()
        gradient[t] += g
        if done%48 == 0 or done==len(hours):
            atomic_json(OUT/'progress.json',dict(stage='monthly-full-batch-adjoint',iteration=step,month=month,completed_hours=done,total_hours=len(hours)))
    gradient *= active[:,:,None]
    if not np.isfinite(gradient).all(): raise ValueError('Nonfinite monthly gradient')
    adjoint_seconds = time.perf_counter()-began
    # All inference curves freeze BEFORE any next-month observations are scored.
    zero_bid = [g['technology'] in base.ZERO_TECH for g in sealed['groups']]
    profile,support = project(theta,data['capacity'][hours],clock_slots(sealed['groups'],hours),zero_bid,neutral)
    atomic_npz(stage/'frozen-profile.npz',coefficients=profile,support=support)
    frozen = digest(stage/'frozen-profile.npz')
    began = time.perf_counter()
    result = dict(month=month,iteration=step,training_hours=len(hours),loss=loss+penalty,**parts,**penalty_parts,
        gradient_norm=float(np.linalg.norm(gradient)),smooth_certificate={k:max(c[k] for c in certificates) for k in certificates[0]},
        profile_sha256=frozen,parameter_sha256=digest(statepath),forward_seconds=forward_seconds,adjoint_seconds=adjoint_seconds)
    result['within'] = evaluate(sealed,data,A,emergency,source_capacity,hours,interval_bids(polynomials(theta,zero_bid)),month,stage/'within.npz')
    ids = np.arange(len(sealed['groups']))
    projected_bids = interval_bids(profile)
    result['within_averaged'] = evaluate(sealed,data,A,emergency,source_capacity,hours,projected_bids[clock_slots(sealed['groups'],hours),ids],month,stage/'within-averaged.npz')
    if month<12:
        future = month_hours(month+1)
        result['forward'] = evaluate(sealed,data,A,emergency,source_capacity,future,projected_bids[clock_slots(sealed['groups'],future),ids],month+1,stage/'forward.npz')
    if digest(stage/'frozen-profile.npz')!=frozen: raise ValueError('Profile changed during validation')
    result['lp_seconds'] = time.perf_counter()-began
    m,v = .9*m+.1*gradient,.999*v+.001*gradient**2
    t = step+1
    nexttheta = theta-design['learning_rate']*(m/(1-.9**t))/(np.sqrt(v/(1-.999**t))+1e-8)
    nexttheta[~active] = initial[~active]
    atomic_npz(folder/'resume.npz',theta=nexttheta,m=m,v=v,step=t)
    result['next_optimizer_sha256'] = digest(folder/'resume.npz')
    atomic_json(recordpath,result)
    print('MONTH',step,month,'within',result['within']['metrics']['price_mae'],'forward',result.get('forward',{}).get('metrics',{}).get('price_mae'),flush=True)
    return result


def aggregate(records,kind,matched=False):
    rows = [r[kind] for r in records if kind in r and (not matched or r['month']>=2)]
    hours = sum(r['hours'] for r in rows)
    cells = sum(r['metrics']['generation_cells'] for r in rows)
    return dict(hours=hours,price_mae=sum(r['metrics']['price_mae']*r['hours'] for r in rows)/hours,
        generation_mae_twh=sum(r['metrics']['generation_mae_twh']*r['metrics']['generation_cells'] for r in rows)/cells,
        generation_normalized_mae=sum(r['metrics']['generation_normalized_mae']*r['metrics']['generation_cells'] for r in rows)/cells,generation_cells=cells)


def run():
    OUT.mkdir(exist_ok=True)
    lock = (OUT/'job.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    design = json.loads(PLAN.read_text())
    pinned = provenance()
    receipt = OUT/'provenance.json'
    if receipt.exists() and json.loads(receipt.read_text())!=pinned: raise ValueError('Changed sealed experiment')
    atomic_json(receipt,pinned)
    pilot = json.loads((OUT/'pilot.json').read_text())
    if pilot['status']!='passed' or pilot['provenance']!=pinned: raise ValueError('Current pilot required')
    if (OUT/'summary.json').exists(): raise ValueError('Already completed')
    initialize()
    history = json.loads((OUT/'history.json').read_text()) if (OUT/'history.json').exists() else []
    step = len(history)
    best = min((r['forward']['price_mae'] for r in history),default=float('inf'))
    stale = history[-1]['stale'] if history else 0
    while True:
        if stale>=design['patience']:
            atomic_json(OUT/'summary.json',dict(status='stopped_after_three_forward_price_nonimprovements',best=json.loads((OUT/'best/selection.json').read_text()),epochs=len(history),last=history[-1],independent_audit='pending'))
            atomic_json(OUT/'progress.json',dict(stage='fit-complete-audit-pending',iterations=len(history)))
            return
        if shutil.disk_usage(OUT).free<1.5*1024**3: raise RuntimeError('Disk reserve reached; not convergence')
        records = []
        for month in range(1,13):
            # Bound physical-matrix caches to one month on the8GiB machine.
            with ProcessPoolExecutor(max_workers=design['workers'],initializer=base.worker_init,mp_context=multiprocessing.get_context('fork')) as pool:
                records.append(fit_month(month,step,design,pool))
        if provenance()!=pinned: raise ValueError('Source changed during fitting')
        score = aggregate(records,'forward')['price_mae']
        improved = base.should_keep(score,best,design)
        if improved:
            best,stale = score,0
            destination = OUT/'best'
            temporary = OUT/'best-next'
            if temporary.exists(): shutil.rmtree(temporary)
            temporary.mkdir()
            for month in range(1,13):
                stage = OUT/f'month-{month:02d}'/f'iteration-{step:03d}'
                dest = temporary/f'month-{month:02d}'
                dest.mkdir()
                for name in ['parameters.npy','frozen-profile.npz','record.json','within.npz','within-averaged.npz','forward.npz']:
                    if (stage/name).exists(): os.link(stage/name,dest/name)
            atomic_json(temporary/'selection.json',dict(iteration=step,forward_price_mae=best))
            if destination.exists(): shutil.rmtree(destination)
            os.rename(temporary,destination)
        else: stale+=1
        record = dict(iteration=step,forward=aggregate(records,'forward'),within=aggregate(records,'within'),within_matched=aggregate(records,'within',True),within_averaged=aggregate(records,'within_averaged'),within_averaged_matched=aggregate(records,'within_averaged',True),stale=stale,improved=improved,months=records)
        history.append(record)
        atomic_json(OUT/'history.json',history)
        print('EPOCH',json.dumps({k:v for k,v in record.items() if k!='months'}),flush=True)
        # Retain parameters and records for all epochs, initial/best LP witnesses,
        # and previous/current KKT states. Never accumulate every interior state.
        if step>=2:
            for month in range(1,13):
                old = OUT/f'month-{month:02d}'/f'iteration-{step-2:03d}'
                for path in old.glob('hour-*.npz'): path.unlink()
                for name in ['optimizer-start.npz','parameters.npy']:
                    p = old/name
                    if p.exists():
                        if name=='parameters.npy': atomic_npz(old/'parameters-archive.npz',theta=np.load(p))
                        p.unlink()
                if step-2>0:
                    for name in ['within.npz','within-averaged.npz','forward.npz']:
                        p=old/name
                        if p.exists(): p.unlink() # best retains separate hardlinks
        if stale>=design['patience']:
            atomic_json(OUT/'summary.json',dict(status='stopped_after_three_forward_price_nonimprovements',best=json.loads((OUT/'best/selection.json').read_text()),epochs=len(history),last=record,independent_audit='pending'))
            atomic_json(OUT/'progress.json',dict(stage='fit-complete-audit-pending',iterations=len(history)))
            return
        step+=1


if __name__=='__main__':
    argparse.ArgumentParser().parse_args()
    try: run()
    except Exception:
        if OUT.exists(): atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()))
        raise
