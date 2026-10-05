"""Bounded nonoptimal dual probe for necessary feasibility cuts, never economic solves."""
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
from scipy.optimize import OptimizeResult
from annual_inventory_phase_one import elastic_block,anchor_candidate,feasibility_support
from audit_annual_warm_state import receipts,guard_reason,terminate_worker
from check_storage_dual_bounds import implied_bounds
from disk_storage_blocks import load_block
from monthly_dispatch import digest,save


def recover(block,state,point,scaled_duals,scale):
    if scale!=2.**-7 or not np.isin(block.cost,[0.,1.]).all() or not np.any(block.cost==1.):
        raise ValueError('Probe supports unit-penalty elastic LPs only')
    A=sparse.vstack([block.equality,block.inequality],format='csr');ne=block.equality.shape[0]
    dual=np.asarray(scaled_duals,dtype=float)/scale
    if dual.shape!=(A.shape[0],) or not np.isfinite(dual).all():raise ValueError('No finite full row-dual candidate')
    dual[ne:]=np.minimum(dual[ne:],0.)
    priced=np.asarray(A.T@dual).ravel();bounds=implied_bounds(block,state,state_independent=True)
    # Finite variable bounds are priced exactly by the Lagrangian. Unbounded
    # upper directions require nonnegative reduced cost; shrink unit-slack duals.
    factor=1.
    for c,p,(lo,hi) in zip(block.cost,priced,bounds):
        if hi is None and p>c:
            if c<=0:raise ValueError('Unsupported unbounded zero-cost reduced direction')
            factor=min(factor,float(c/p)*(1.-8*np.finfo(float).eps))
    dual*=factor
    reduced=block.cost-np.asarray(A.T@dual).ravel()
    return OptimizeResult(x=np.asarray(point),fun=math.fsum(float(c)*float(v) for c,v in zip(block.cost,point)),
        eqlin=OptimizeResult(marginals=dual[:ne]),ineqlin=OptimizeResult(marginals=dual[ne:]),
        lower=OptimizeResult(marginals=np.maximum(reduced,0.)),upper=OptimizeResult(marginals=np.minimum(reduced,0.))),factor


def probe(block,state,point):
    import highspy
    ne=block.equality.shape[0];A=sparse.vstack([block.equality,block.inequality],format='csr')
    rhs=block.rhs-block.coupling@state;limit=block.limit-block.inequality_coupling@state
    scale=2.**-7;lp=highspy.HighsLp();lp.num_col_=len(block.cost);lp.num_row_=A.shape[0]
    lp.col_cost_=block.cost*scale
    lp.col_lower_=np.array([-highspy.kHighsInf if lo is None else lo for lo,hi in block.bounds])
    lp.col_upper_=np.array([highspy.kHighsInf if hi is None else hi for lo,hi in block.bounds])
    lp.row_lower_=np.r_[rhs,np.full(len(limit),-highspy.kHighsInf)];lp.row_upper_=np.r_[rhs,limit]
    lp.a_matrix_.format_=highspy.MatrixFormat.kRowwise;lp.a_matrix_.start_=A.indptr;lp.a_matrix_.index_=A.indices;lp.a_matrix_.value_=A.data
    solver=highspy.Highs()
    for name,value in [('output_flag',False),('threads',2),('solver','ipm'),('run_crossover','off'),('time_limit',600.),('primal_feasibility_tolerance',1e-10),('dual_feasibility_tolerance',1e-10),('ipm_optimality_tolerance',1e-12)]:
        if solver.setOptionValue(name,value)!=highspy.HighsStatus.kOk:raise ValueError('Probe solver option rejected')
    if solver.passModel(lp)!=highspy.HighsStatus.kOk:raise ValueError('Probe model rejected')
    solver.run();termination=solver.modelStatusToString(solver.getModelStatus())
    result,factor=recover(block,state,point,solver.getSolution().row_dual,scale)
    return result,dict(solver_termination=termination,objective_scale=scale,dual_shrink_factor=factor,
        primal_origin='Constructed from hash-checked feasible anchor; not the solver primal.',
        certificate_scope='Any positive independently replayed Lagrangian support is a necessary feasibility cut; no optimum inferred.')


def worker(args):
    signature=receipts(args,args.month)
    audit_path=args.anchor/'warm-audit'/'independent-witness-audit.json';audit=json.loads(audit_path.read_text())
    if audit['status']!='annual_fixed_inventory_feasible' or audit['input_sha256']!=signature['input_sha256'] or audit['warm_state_sha256']!=digest(args.anchor/'master-state.npz'):
        raise ValueError('Verified feasible anchor required')
    row=audit['rows'][args.month-1];receipt_path=args.anchor/'warm-audit'/f'{args.month:02d}.json'
    receipt=json.loads(receipt_path.read_text());witness=receipt_path.parent/receipt['witness_file']
    if digest(receipt_path)!=row['receipt_sha256'] or digest(witness)!=row['witness_sha256'] or receipt['block_sha256']!=signature['block_sha256']:
        raise ValueError('Feasible anchor/source changed')
    with np.load(args.folder/'master-state.npz',allow_pickle=False) as data:state=data['warm_state_mwh'].copy()
    with np.load(args.anchor/'master-state.npz',allow_pickle=False) as data:anchor=data['warm_state_mwh'].copy()
    source=load_block(args.folder/f'{args.month:02d}.npz')
    with np.load(witness,allow_pickle=False) as data:point=anchor_candidate(source,state,data['primal'],boundary_only=True)
    block=elastic_block(source,boundary_only=True);del source
    if max(float(np.max(abs(block.equality@point+block.coupling@state-block.rhs),initial=0.)),float(np.max(block.inequality@point+block.inequality_coupling@state-block.limit,initial=0.)))>1e-7:
        raise ValueError('Constructed elastic anchor fails original-unit gate')
    result,diagnostic=probe(block,state,point);support=feasibility_support(block,state,result,anchor)
    target=args.folder/'phase-one-boundary-dual-probe'/f'{args.month:02d}-witness.npz';temporary=target.with_suffix('.npz.tmp')
    with temporary.open('wb') as stream:np.savez_compressed(stream,primal=result.x,equality_duals=result.eqlin.marginals,inequality_duals=result.ineqlin.marginals,lower_marginals=result.lower.marginals,upper_marginals=result.upper.marginals)
    temporary.replace(target)
    save(target.with_suffix('.json'),dict(**signature,**support,**diagnostic,month=args.month,mode='boundary',producer_kind='dual_probe',witness_sha256=digest(target),tool_sha256=digest(Path(__file__)),anchor_audit_sha256=digest(audit_path),dependencies={name:digest(Path(__file__).with_name(name)) for name in ['annual_inventory_phase_one.py','native_storage_solver.py','check_storage_dual_bounds.py','disk_storage_blocks.py']}))


def run(args):
    output=args.folder/'phase-one-boundary-dual-probe';output.mkdir(exist_ok=True)
    if (output/f'{args.month:02d}-witness.json').exists():raise ValueError('Existing probe evidence must not be overwritten')
    with (output/f'{args.month:02d}.log').open('w') as log:
        child=subprocess.Popen([sys.executable,__file__,'--folder',str(args.folder),'--anchor',str(args.anchor),'--month',str(args.month),'--worker'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        save(output/'status.json',dict(status='probing_phase_one_duals',month=args.month,pid=child.pid));peak=0;started=time.monotonic()
        while child.poll() is None:
            try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
            except FileNotFoundError:rss=0
            peak=max(peak,rss);reason=guard_reason(time.monotonic()-started,rss,6.,900.)
            if reason:terminate_worker(child);save(output/'status.json',dict(status=reason,month=args.month,peak_rss_bytes=peak));return
            time.sleep(1)
        save(output/'status.json',dict(status='cut_requires_independent_replay' if child.returncode==0 else 'failed',month=args.month,returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--folder',type=Path,required=True);parser.add_argument('--anchor',type=Path,required=True);parser.add_argument('--month',type=int,required=True);parser.add_argument('--worker',action='store_true')
    args=parser.parse_args()
    if not 1<=args.month<=12:parser.error('Invalid month')
    args.folder=args.folder.resolve();args.anchor=args.anchor.resolve();worker(args) if args.worker else run(args)
