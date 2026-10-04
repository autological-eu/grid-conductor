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


def elastic_block(block,boundary_only=False):
    n=len(block.cost);A=sparse.csr_matrix(block.equality);B=sparse.csr_matrix(block.coupling)
    ne=A.shape[0]
    U=sparse.csr_matrix((0,n)) if block.inequality is None else sparse.csr_matrix(block.inequality)
    nu=U.shape[0]
    V=sparse.csr_matrix((nu,B.shape[1])) if block.inequality_coupling is None else sparse.csr_matrix(block.inequality_coupling)
    erows=np.flatnonzero(B.getnnz(axis=1)) if boundary_only else np.arange(ne)
    urows=np.flatnonzero(V.getnnz(axis=1)) if boundary_only else np.arange(nu)
    ke=len(erows);ku=len(urows)
    E=sparse.csr_matrix((np.ones(ke),(erows,np.arange(ke))),shape=(ne,ke))
    I=sparse.csr_matrix((np.ones(ku),(urows,np.arange(ku))),shape=(nu,ku))
    return Block(np.r_[np.zeros(n),np.ones(2*ke+ku)],block.bounds+[(0.,None)]*(2*ke+ku),
        sparse.hstack([A,E,-E,sparse.csr_matrix((ne,ku))],format='csr'),block.rhs,B,
        sparse.hstack([U,sparse.csr_matrix((nu,2*ke)),-I],format='csr'),
        np.zeros(nu) if block.limit is None else block.limit,V)


def anchor_candidate(block,state,primal,boundary_only=False):
    B=sparse.csr_matrix(block.coupling)
    erows=np.flatnonzero(B.getnnz(axis=1)) if boundary_only else np.arange(block.equality.shape[0])
    nu=0 if block.inequality is None else block.inequality.shape[0]
    V=sparse.csr_matrix((nu,B.shape[1])) if block.inequality_coupling is None else sparse.csr_matrix(block.inequality_coupling)
    urows=np.flatnonzero(V.getnnz(axis=1)) if boundary_only else np.arange(nu)
    delta=np.asarray(block.rhs-block.equality@primal-B@state)[erows]
    violation=np.zeros(0) if not nu else np.maximum(0.,block.inequality@primal+V@state-block.limit)[urows]
    return np.r_[primal,np.maximum(delta,0.),np.maximum(-delta,0.),violation]


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
    source=load_block(args.folder/f'{args.month:02d}.npz')
    anchor_row=anchor_audit['rows'][args.month-1]
    anchor_receipt_path=args.anchor/'warm-audit'/f'{args.month:02d}.json'
    anchor_receipt=json.loads(anchor_receipt_path.read_text())
    anchor_witness=anchor_receipt_path.parent/anchor_receipt['witness_file']
    if digest(anchor_receipt_path)!=anchor_row['receipt_sha256'] or digest(anchor_witness)!=anchor_row['witness_sha256'] or anchor_receipt['block_sha256']!=signature['block_sha256']:
        raise ValueError('Verified feasible anchor witness/source changed')
    with np.load(anchor_witness,allow_pickle=False) as saved:point=anchor_candidate(source,state,saved['primal'],boundary_only=args.mode=='boundary')
    block=elastic_block(source,boundary_only=args.mode=='boundary')
    anchor_eq=float(np.max(abs(block.equality@point+block.coupling@state-block.rhs),initial=0.))
    anchor_ub=float(max(0.,np.max(block.inequality@point+block.inequality_coupling@state-block.limit,initial=0.)))
    if not np.isfinite(point).all() or max(anchor_eq,anchor_ub)>1e-7:raise ValueError('Constructed elastic anchor fails primal gate')
    elastic_upper=math.fsum(float(c)*float(v) for c,v in zip(block.cost,point))
    del source,point
    result=solve_native(block,state,time_limit=600.,threads=2)
    if result is None:raise ValueError('Elastic Phase-I unexpectedly infeasible')
    support=feasibility_support(block,state,result,anchor)
    if support["phase_one_cost"]>elastic_upper+1e-7:raise ValueError("Phase-I optimum exceeds checked feasible elastic anchor")
    target=args.folder/('phase-one-boundary' if args.mode=='boundary' else 'phase-one')/f'{args.month:02d}-witness.npz'
    temporary=target.with_suffix('.npz.tmp')
    with temporary.open('wb') as stream:np.savez_compressed(stream,primal=result.x,equality_duals=result.eqlin.marginals,inequality_duals=result.ineqlin.marginals,lower_marginals=result.lower.marginals,upper_marginals=result.upper.marginals)
    temporary.replace(target)
    save(target.with_suffix('.json'),dict(**signature,**support,month=args.month,mode=args.mode,slack_variables=int(np.count_nonzero(block.cost)),elastic_anchor_cost=elastic_upper,elastic_anchor_equality_residual=anchor_eq,elastic_anchor_inequality_violation=anchor_ub,witness_sha256=digest(target),tool_sha256=digest(Path(__file__)),anchor_audit_sha256=digest(args.anchor/'warm-audit'/'independent-witness-audit.json'),dependencies={name:digest(Path(__file__).with_name(name)) for name in ['native_storage_solver.py','check_storage_dual_bounds.py','disk_storage_blocks.py']}))


def run(args):
    output=args.folder/('phase-one-boundary' if args.mode=='boundary' else 'phase-one');output.mkdir(exist_ok=True)
    if (output/f'{args.month:02d}-witness.json').exists():raise ValueError('Existing Phase-I evidence must not be overwritten')
    with (output/f'{args.month:02d}.log').open('w') as log:
        child=subprocess.Popen([sys.executable,__file__,'--folder',str(args.folder),'--anchor',str(args.anchor),'--month',str(args.month),'--mode',args.mode,'--worker'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
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
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--folder',type=Path,required=True);parser.add_argument('--anchor',type=Path,required=True);parser.add_argument('--month',type=int,required=True);parser.add_argument('--worker',action='store_true');parser.add_argument('--mode',choices=['all','boundary'],default='all')
    args=parser.parse_args()
    if not 1<=args.month<=12:parser.error('Invalid month')
    args.folder=args.folder.resolve();args.anchor=args.anchor.resolve()
    worker(args) if args.worker else run(args)
