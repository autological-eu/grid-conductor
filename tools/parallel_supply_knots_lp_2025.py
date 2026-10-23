"""Two-process scheduling of independent fits; numerical producers unchanged.

The original runner must be stopped at a readable iteration checkpoint first.
The original job lock excludes another runner during this fitting phase. Each
worker also locks its own fold; LP evaluation resumes through the frozen runner.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import fcntl
import json
import resource
import time
from pathlib import Path
from sigmoid_month_pairs_2025 import ROOT,digest
import run_supply_knots_lp_2025 as runner
from supply_knot_network_2025 import load

STATE=None


def initialize():
    global STATE
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,)*2);STATE=load()


def fit_pair(pair):
    train,test=pair;lock=(runner.OUT/f'fit-{train:02d}.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    sealed,data,A,_,capacity=STATE;began=time.perf_counter();design=json.loads(runner.PLAN.read_text())
    runner.fit(sealed,data,A,capacity,design,train,test)
    return dict(train=train,test=test,worker_seconds=time.perf_counter()-began,proposal_sha256=digest(runner.OUT/f'proposal-{train:02d}.json'))


def run(prior_seconds):
    began=time.perf_counter();design=json.loads(runner.PLAN.read_text());lock=(runner.OUT/'job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    for name,expected in json.loads((runner.OUT/'provenance.json').read_text()).items():
        if digest(ROOT/name)!=expected:raise ValueError('Changed sealed dependency')
    pending=[p for p in design['pairs'] if not (runner.OUT/f'proposal-{p[0]:02d}.json').exists()]
    rows=[];receipt=dict(method='two independent month fits per process pool; same frozen numerical producer/config',
         controller_sha256=digest(__file__),prior_runner_wall_seconds=prior_seconds,pending=pending,completed=rows)
    runner.atomic_json(runner.OUT/'orchestration.json',receipt)
    with ProcessPoolExecutor(max_workers=2,initializer=initialize) as pool:
        futures=[pool.submit(fit_pair,pair) for pair in pending]
        for future in as_completed(futures):
            rows.append(future.result());runner.atomic_json(runner.OUT/'orchestration.json',receipt)
            print('PARALLEL_FIT',rows[-1],flush=True)
    receipt['parallel_stage_seconds']=time.perf_counter()-began;runner.atomic_json(runner.OUT/'orchestration.json',receipt)
    fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
    evaluation=time.perf_counter();runner.run()
    receipt.update(remaining_runner_seconds=time.perf_counter()-evaluation,total_active_job_wall_seconds=prior_seconds+time.perf_counter()-began,status='all_original_LP_pairs_complete')
    runner.atomic_json(runner.OUT/'orchestration.json',receipt)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prior-seconds',type=float,required=True);args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,)*2);run(args.prior_seconds)
