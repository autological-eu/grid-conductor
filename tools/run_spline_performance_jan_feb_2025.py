"""Bounded full-January training / full-February forward performance study."""
from concurrent.futures import ProcessPoolExecutor
import fcntl
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import condensed_spline_kkt_2025 as fast
import hourly_spline_reconstruction_2025 as base
import hourly_spline_numerical_recovery_2025 as recovery
import run_forward_hourly_splines_2025 as study
from run_differentiable_spline_2025 import atomic_json
from sigmoid_month_pairs_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/spline-performance-jan-feb-v1'
PLAN=ROOT/'config/spline-performance-jan-feb-2025.json'
SEED=study.OUT/'month-01/iteration-000'


def provenance():
    paths=[PLAN,Path(__file__),ROOT/'tools/condensed_spline_kkt_2025.py',ROOT/'tools/pilot_condensed_spline_2025.py',OUT/'gradient-pilot.json',SEED/'parameters.npy',SEED/'record.json']
    for name in ['test_condensed_spline_2025.py','report_spline_performance_jan_feb_2025.py']:
        paths.append(ROOT/'tools'/name)
    sources=study.provenance()
    sources.update({str(p.relative_to(ROOT)):digest(p) for p in paths})
    return sources


def run():
    OUT.mkdir(exist_ok=True)
    lock=(OUT/'job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    pilot=json.loads((OUT/'gradient-pilot.json').read_text())
    if pilot['status']!='passed' or any(digest(ROOT/p)!=sha for p,sha in pilot['sources'].items()):raise ValueError('Current gradient pilot required')
    pinned=provenance()
    if (OUT/'provenance.json').exists() and json.loads((OUT/'provenance.json').read_text())!=pinned:raise ValueError('Changed sealed experiment')
    atomic_json(OUT/'provenance.json',pinned)
    s,d,A,_,_=study.initialize()
    fast.install()
    base.forward_job=recovery.replay_or_recover
    study.OUT=OUT
    initial,_,_=study.neutral_state(s,d,np.arange(744))
    np.testing.assert_array_equal(initial,np.load(SEED/'parameters.npy'))
    stage=OUT/'month-01/iteration-000';stage.mkdir(parents=True,exist_ok=True)
    for h in range(744):
        source=SEED/f'hour-{h:04d}.npz'
        if not (stage/source.name).exists():os.link(source,stage/source.name)
    history=[]
    if (OUT/'history.json').exists():history=json.loads((OUT/'history.json').read_text())
    design=json.loads(PLAN.read_text())
    best_record=next((r for r in reversed(history) if r['improved']),None)
    best=best_record['forward']['metrics']['price_mae'] if best_record else float('inf')
    stale=history[-1]['stale'] if history else 0
    began=time.perf_counter()
    for step in range(len(history),design['maximum_updates']+1):
        with ProcessPoolExecutor(max_workers=2,initializer=base.worker_init,mp_context=multiprocessing.get_context('fork')) as pool:
            row=study.fit_month(1,step,design,pool)
        score=row['forward']['metrics']['price_mae']
        improved=base.should_keep(score,best,design)
        if improved:best,stale=score,0
        else:stale+=1
        row.update(stale=stale,improved=improved,initial_witness_replay=step==0,session_seconds=time.perf_counter()-began)
        history.append(row);atomic_json(OUT/'history.json',history)
        print('EVALUATION',step,'forward',score,'stale',stale,flush=True)
        if stale>=design['patience']:break
    if provenance()!=pinned:raise ValueError('Producer changed while running')
    selected=min((r for r in history if r['improved']),key=lambda r:r['forward']['metrics']['price_mae'])
    atomic_json(OUT/'summary.json',dict(status='completed_bounded_pipeline_test',stop_reason='forward_patience' if stale>=3 else 'three_update_test_budget_not_convergence',best_iteration=selected['iteration'],selected=selected,history_sha256=digest(OUT/'history.json'),seconds_this_session=time.perf_counter()-began,independent_audit='pending'))
    atomic_json(OUT/'progress.json',dict(stage='bounded-test-complete-audit-pending'))


if __name__=='__main__':
    try:run()
    except Exception:
        OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
