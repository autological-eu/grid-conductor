"""Guarded equivalent-objective conditioning diagnostic; not an annual receipt."""
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from native_storage_solver import solve_native
from audit_annual_warm_state import receipts, guard_reason, terminate_worker
from monthly_dispatch import digest, save


def solve_scaled(block, state, scale):
    if scale not in (1., 2.**-7):
        raise ValueError('Only declared exact positive objective scales are supported')
    result = solve_native(replace(block, cost=block.cost*scale), state, time_limit=600., threads=2)
    if result is None:
        return None
    result.fun = math.fsum(float(c)*float(x) for c,x in zip(block.cost,result.x))
    for part in ['eqlin', 'ineqlin', 'lower', 'upper']:
        result[part].marginals = np.asarray(result[part].marginals)/scale
    return result


def worker(args):
    from disk_storage_blocks import load_block
    from sparse_primal_correction import correct_sparse
    from check_storage_dual_bounds import objective_support
    from audit_monthly_dispatch_witnesses import replay
    signature = receipts(args, args.month)
    with np.load(args.folder/'master-state.npz', allow_pickle=False) as data:
        state = data['warm_state_mwh'].copy()
    block = load_block(args.folder/f'{args.month:02d}.npz')
    result = solve_scaled(block, state, args.scale)
    if result is None:
        raise ValueError('Conditioning diagnostic classified fixed inventories infeasible')
    result.x, checks = correct_sparse(block, state, result.x)
    if not checks['original_unit_gate_passed']:
        raise ValueError('Original-unit corrected primal gate failed')
    result.fun = math.fsum(float(c)*float(x) for c,x in zip(block.cost,result.x))
    gradient, intercept = objective_support(block, state, result)
    lower = float(intercept+gradient@state)
    record = dict(**signature, cost_eur=result.fun, dual_support_eur=lower,
                  gradient_eur_per_mwh=gradient.tolist(), dual_intercept_eur=float(intercept),
                  objective_scale=args.scale, producer_sha256=digest(Path(__file__)),
                  dependencies={name:digest(Path(__file__).with_name(name)) for name in
                                ['native_storage_solver.py','sparse_primal_correction.py','check_storage_dual_bounds.py','audit_monthly_dispatch_witnesses.py']},
                  scope='Conditioning diagnostic only; no accepted monthly/annual receipt, optimum, empirical validation or investment result.')
    arrays = dict(primal=result.x,equality_duals=result.eqlin.marginals,
                  inequality_duals=result.ineqlin.marginals,lower_marginals=result.lower.marginals,
                  upper_marginals=result.upper.marginals)
    record['replayed_original_units'] = replay(block, state, arrays, record)
    witness=args.output/'witness.npz'
    with witness.open('wb') as stream:np.savez_compressed(stream,**arrays)
    record['witness_sha256'] = digest(witness)
    save(args.output/'result.json', record)


def run(args):
    if args.output.exists():
        raise ValueError('Diagnostic output already exists; preserve prior evidence')
    args.output.mkdir(parents=True)
    with (args.output/'solver.log').open('w') as log:
        child=subprocess.Popen([sys.executable,__file__,'--folder',str(args.folder),'--month',str(args.month),
                                '--scale',str(args.scale),'--output',str(args.output),'--worker'],
                               stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        save(args.output/'status.json',dict(status='running_conditioning_diagnostic',pid=child.pid));peak=0;started=time.monotonic()
        while child.poll() is None:
            p=Path(f'/proc/{child.pid}/status')
            try:rss=sum(int(line.split()[1])*1024 for line in p.read_text().splitlines() if line.startswith('VmRSS:'))
            except FileNotFoundError:rss=0
            peak=max(peak,rss);reason=guard_reason(time.monotonic()-started,rss,6.,900.)
            if reason:
                terminate_worker(child);save(args.output/'status.json',dict(status=reason,peak_rss_bytes=peak));return
            time.sleep(1)
        save(args.output/'status.json',dict(status='diagnostic_requires_separate_review' if child.returncode==0 else 'failed',
             returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,required=True);parser.add_argument('--month',type=int,required=True)
    parser.add_argument('--scale',type=float,choices=[1.,2.**-7],required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--worker',action='store_true')
    args=parser.parse_args()
    if not 1<=args.month<=12:parser.error('Invalid month')
    args.folder=args.folder.resolve();args.output=args.output.resolve()
    worker(args) if args.worker else run(args)
