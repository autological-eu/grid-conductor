"""Guarded elastic Phase-I diagnostic; a positive dual support yields a feasibility cut."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from scipy import sparse
from storage_coordinator import Block
from disk_storage_blocks import load_block
from native_storage_solver import solve_native
from check_storage_dual_bounds import objective_support
from audit_annual_warm_state import receipts, guard_reason, terminate_worker
from monthly_dispatch import digest, save


def elastic_block(block):
    n=len(block.cost);ne=block.equality.shape[0]
    U=sparse.csr_matrix((0,n)) if block.inequality is None else block.inequality
    nu=U.shape[0]
    V=sparse.csr_matrix((nu,block.coupling.shape[1])) if block.inequality_coupling is None else block.inequality_coupling
    return Block(np.r_[np.zeros(n),np.ones(2*ne+nu)],block.bounds+[(0.,None)]*(2*ne+nu),
        sparse.hstack([block.equality,sparse.eye(ne),-sparse.eye(ne),sparse.csr_matrix((ne,nu))],format='csr'),
        block.rhs,block.coupling,
        sparse.hstack([U,sparse.csr_matrix((nu,2*ne)),-sparse.eye(nu)],format='csr'),
        np.zeros(nu) if block.limit is None else block.limit,V)


def feasibility_support(block,state,result,anchor):
    eq=float(np.max(abs(block.equality@result.x+block.coupling@state-block.rhs),initial=0.))
    ub=float(max(0.,np.max(block.inequality@result.x+block.inequality_coupling@state-block.limit,initial=0.)))
    bound=float(max([0.]+[lo-v for v,(lo,hi) in zip(result.x,block.bounds) if lo is not None]+[v-hi for v,(lo,hi) in zip(result.x,block.bounds) if hi is not None]))
    if max(eq,ub,bound)>1e-7:raise ValueError('Phase-I primal fails original-unit gate')
    if not np.isfinite(result.x).all():raise ValueError('Nonfinite Phase-I primal')
    cost=math.fsum(float(c)*float(v) for c,v in zip(block.cost,result.x))
    gradient,intercept=objective_support(block,state,result)
    lower=float(intercept+gradient@state)
    if not np.isfinite(lower) or not np.isfinite(gradient).all() or lower>cost+1e-7:raise ValueError('Invalid Phase-I dual support')
    if lower<=1e-7:raise ValueError('No independently supported positive infeasibility cut')
    anchor_value=float(intercept+gradient@anchor)
    if anchor_value>1e-7:raise ValueError('Feasibility cut excludes verified feasible anchor')
    return dict(phase_one_cost=cost,dual_support=lower,gradient=gradient.tolist(),intercept=float(intercept),
        feasibility_limit=1e-7-float(intercept),anchor_support=anchor_value,
        max_equality_residual=eq,max_inequality_violation=ub,max_bound_violation=bound,
        scope='Necessary numerical feasibility cut only; not a welfare or annual objective cut.')


def worker(args):
    signature=receipts(args,args.month)
    anchor_manifest=json.loads((args.anchor/'master-workspace.json').read_text())
    if anchor_manifest['input_sha256']!=signature['input_sha256']:raise ValueError('Anchor model differs')
    with np.load(args.folder/'master-state.npz',allow_pickle=False) as data:state=data['warm_state_mwh'].copy()
    with np.load(args.anchor/'master-state.npz',allow_pickle=False) as data:anchor=data['warm_state_mwh'].copy()
    anchor_audit=json.loads((args.anchor/'warm-audit'/'independent-witness-audit.json').read_text())
    if anchor_audit['status']!='annual_fixed_inventory_feasible' or anchor_audit['warm_state_sha256']!=digest(args.anchor/'master-state.npz'):
        raise ValueError('Verified annual feasible anchor required')
    block=elastic_block(load_block(args.folder/f'{args.month:02d}.npz'))
    result=solve_native(block,state,time_limit=600.,threads=2)
    if result is None:raise ValueError('Elastic Phase-I unexpectedly infeasible')
    support=feasibility_support(block,state,result,anchor)
    target=args.folder/'phase-one'/f'{args.month:02d}-witness.npz'
    temporary=target.with_suffix('.npz.tmp')
    with temporary.open('wb') as stream:np.savez_compressed(stream,primal=result.x,equality_duals=result.eqlin.marginals,inequality_duals=result.ineqlin.marginals,lower_marginals=result.lower.marginals,upper_marginals=result.upper.marginals)
    temporary.replace(target)
    save(target.with_suffix('.json'),dict(**signature,**support,month=args.month,witness_sha256=digest(target),tool_sha256=digest(Path(__file__)),anchor_audit_sha256=digest(args.anchor/'warm-audit'/'independent-witness-audit.json'),dependencies={name:digest(Path(__file__).with_name(name)) for name in ['native_storage_solver.py','check_storage_dual_bounds.py','disk_storage_blocks.py']}))


def run(args):
    output=args.folder/'phase-one';output.mkdir(exist_ok=True)
    if (output/f'{args.month:02d}-witness.json').exists():raise ValueError('Existing Phase-I evidence must not be overwritten')
    with (output/f'{args.month:02d}.log').open('w') as log:
        child=subprocess.Popen([sys.executable,__file__,'--folder',str(args.folder),'--anchor',str(args.anchor),'--month',str(args.month),'--worker'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        save(output/'status.json',dict(status='solving_phase_one',month=args.month,pid=child.pid))
        peak=0;started=time.monotonic()
        while child.poll() is None:
            try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
            except FileNotFoundError:rss=0
            peak=max(peak,rss);reason=guard_reason(time.monotonic()-started,rss,6.,900.)
            if reason:
                terminate_worker(child);save(output/'status.json',dict(status=reason,month=args.month,peak_rss_bytes=peak));return
            time.sleep(1)
        save(output/'status.json',dict(status='cut_requires_independent_replay' if child.returncode==0 else 'failed',month=args.month,returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--folder',type=Path,required=True);parser.add_argument('--anchor',type=Path,required=True);parser.add_argument('--month',type=int,required=True);parser.add_argument('--worker',action='store_true')
    args=parser.parse_args()
    if not 1<=args.month<=12:parser.error('Invalid month')
    args.folder=args.folder.resolve();args.anchor=args.anchor.resolve()
    worker(args) if args.worker else run(args)
