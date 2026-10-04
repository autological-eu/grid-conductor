"""Resource-guarded fixed-inventory monthly re-solves; never annual optimality."""
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path
from monthly_dispatch import digest,save
def receipts(args,month):
 master=json.loads((args.folder/'master-workspace.json').read_text())
 for name,value in master['workspace_sha256'].items():
  if digest(args.folder/name)!=value:raise ValueError('Inventory workspace fingerprint mismatch')
 block=json.loads((args.folder/f'{month:02d}.json').read_text())
 if block['input_sha256']!=master['input_sha256'] or digest(args.folder/f'{month:02d}.npz')!=block['block_sha256']:
  raise ValueError('Block/source fingerprint mismatch')
 return dict(input_sha256=master['input_sha256'],block_sha256=block['block_sha256'],
  warm_state_sha256=master['workspace_sha256']['master-state.npz'])
def worker(args):
 import numpy as np
 from disk_storage_blocks import load_block
 from storage_coordinator import solve_block
 signature=receipts(args,args.month)
 signature['audit_tool_sha256']=digest(Path(__file__))
 with np.load(args.folder/'master-state.npz',allow_pickle=False) as data:state=data['warm_state_mwh'].copy()
 block=load_block(args.folder/f'{args.month:02d}.npz')
 def retain_rejected(result,diagnostic):
  target=args.folder/'warm-audit'/f'{args.month:02d}-rejected-primal.npz'
  temporary=target.with_suffix('.npz.tmp')
  with temporary.open('wb') as stream:np.savez_compressed(stream,primal=result.x)
  temporary.replace(target)
  save(target.with_suffix('.json'),dict(**signature,**diagnostic,month=args.month,
   primal_sha256=digest(target),cost_eur=float(result.fun),
   scope='rejected candidate, diagnostic only; no accepted feasibility or annual result'))
 native=bool(getattr(args,'native_no_crossover',False))
 dual_record={}
 if native:
  import math
  from native_storage_solver import solve_native
  from sparse_primal_correction import correct_sparse
  from check_storage_dual_bounds import objective_support
  result=solve_native(block,state,time_limit=args.solver_seconds,threads=getattr(args,'native_threads',1))
  local=None
  if result is not None:
   candidate,checks=correct_sparse(block,state,result.x)
   if not checks['original_unit_gate_passed']:raise ValueError('Native corrected monthly primal gate failed')
   result.x=candidate;result.fun=math.fsum(float(c)*float(x) for c,x in zip(block.cost,candidate))
   gradient,intercept=objective_support(block,state,result);lower=float(intercept+gradient@state)
   if not np.isfinite(lower) or lower>result.fun+1e-7:raise ValueError('Native monthly primal/dual consistency failed')
   dual_record=dict(dual_support_eur=lower,local_gap_eur=result.fun-lower,
    backend='native-highs-no-crossover',native_threads=getattr(args,'native_threads',1),corrected_primal_checks=checks,gradient_eur_per_mwh=gradient.tolist(),dual_intercept_eur=float(intercept),
    dependencies={name:digest(Path(__file__).with_name(name)) for name in ['native_storage_solver.py','sparse_primal_correction.py','check_storage_dual_bounds.py']})
   witness=args.folder/'warm-audit'/f'{args.month:02d}-witness.npz'
   if witness.exists():raise ValueError('Existing monthly witness must be archived or audited, never overwritten')
   temporary=witness.with_suffix('.npz.tmp')
   with temporary.open('wb') as stream:np.savez_compressed(stream,primal=candidate,
    equality_duals=result.eqlin.marginals,inequality_duals=result.ineqlin.marginals,
    lower_marginals=result.lower.marginals,upper_marginals=result.upper.marginals)
   temporary.replace(witness)
   dual_record.update(witness_file=witness.name,witness_sha256=digest(witness))
   local=(result,gradient)
 else:
  local=solve_block(block,state,time_limit=args.solver_seconds,first_method=args.first_solver,residual_tolerance=1e-7,on_residual_rejection=retain_rejected,primal_tolerance=getattr(args,'primal_tolerance',1e-10))
 if local is None:raise ValueError('Fixed warm inventories infeasible')
 r,_=local
 eq=float(np.max(abs(block.equality@r.x+block.coupling@state-block.rhs)))
 ub=float(max(0.,np.max(block.inequality@r.x+block.inequality_coupling@state-block.limit)))
 bound=max([0.]+[max(0.,lo-x) if lo is not None else 0. for x,(lo,hi) in zip(r.x,block.bounds)]+[max(0.,x-hi) if hi is not None else 0. for x,(lo,hi) in zip(r.x,block.bounds)])
 if max(eq,ub,bound)>1e-7:
  save(args.folder/'warm-audit'/f'{args.month:02d}-rejected.json',dict(**signature,
   month=args.month,status='rejected_original_unit_residuals',cost_eur=float(r.fun),
   max_equality_residual=eq,max_inequality_violation=ub,max_bound_violation=bound,
   solver_seconds=args.solver_seconds,first_solver=args.first_solver,solver_primal_tolerance=getattr(args,'primal_tolerance',1e-10),
   scope='diagnostic only; not accepted feasibility or an annual result'))
  raise ValueError(f'Original-unit primal residual gate failed: equality={eq:.12g}, inequality={ub:.12g}, bounds={bound:.12g}')
 save(args.folder/'warm-audit'/f'{args.month:02d}.json',dict(**signature,month=args.month,cost_eur=float(r.fun),
  max_equality_residual=eq,max_inequality_violation=ub,max_bound_violation=bound,
  solver_seconds=args.solver_seconds,first_solver='native-ipm-no-crossover' if native else args.first_solver,solver_primal_tolerance=1e-10 if native else getattr(args,'primal_tolerance',1e-10),**dual_record,scope='verified fixed monthly inventories only; no annual optimum'))
def terminate_worker(child):
 """Stop the owned process group, including a solver that ignores its limit."""
 if child.poll() is not None:return
 os.killpg(child.pid,signal.SIGTERM)
 try:child.wait(timeout=10)
 except subprocess.TimeoutExpired:
  os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
def guard_reason(elapsed,rss,memory_gib,wall_seconds):
 if rss>memory_gib*2**30:return 'stopped_memory_guard'
 if elapsed>wall_seconds:return 'stopped_wall_time_guard'
 return None
def run(args):
 output=args.folder/'warm-audit';output.mkdir(exist_ok=True)
 for month in range(1,args.last_month+1):
  signature=receipts(args,month);receipt=output/f'{month:02d}.json'
  if receipt.exists():
   item=json.loads(receipt.read_text())
   if any(item.get(k)!=v for k,v in signature.items()):raise ValueError('Warm audit/source mismatch')
   if bool(item.get('backend')=='native-highs-no-crossover')!=bool(getattr(args,'native_no_crossover',False)):raise ValueError('Warm audit solver mode mismatch')
   if item.get('audit_tool_sha256')!=digest(Path(__file__)):raise ValueError('Monthly audit code fingerprint mismatch')
   if bool(getattr(args,'native_no_crossover',False)):
    if any(digest(Path(__file__).with_name(name))!=value for name,value in item.get('dependencies',{}).items()):raise ValueError('Monthly native dependency fingerprint mismatch')
    if item.get('witness_file')!=f'{month:02d}-witness.npz':raise ValueError('Unexpected monthly witness filename')
    witness=output/item.get('witness_file','missing-witness')
    if not witness.exists() or digest(witness)!=item.get('witness_sha256'):raise ValueError('Monthly primal/dual witness missing or mismatched')
   continue
  with (output/f'{month:02d}.log').open('w') as log:
   child=subprocess.Popen([sys.executable,__file__,'--folder',str(args.folder),'--month',str(month),'--solver-seconds',str(args.solver_seconds),'--first-solver',args.first_solver,'--primal-tolerance',str(args.primal_tolerance),'--native-threads',str(args.native_threads)]+(['--native-no-crossover'] if args.native_no_crossover else []),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save(output/'status.json',dict(status='solving_fixed_inventories',month=month,pid=child.pid))
   peak=0;started=time.monotonic()
   wall_seconds=getattr(args,'wall_seconds',None) or 3*args.solver_seconds+120.
   while child.poll() is None:
    try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
    except FileNotFoundError:rss=0
    peak=max(peak,rss)
    elapsed=time.monotonic()-started
    reason=guard_reason(elapsed,rss,args.memory_gib,wall_seconds)
    if reason:
     terminate_worker(child)
     save(output/'status.json',dict(status=reason,month=month,peak_rss_bytes=peak,elapsed_seconds=elapsed,wall_seconds=wall_seconds,scope='no accepted monthly result; not annual optimisation'))
     raise RuntimeError(f'Monthly warm re-solve stopped: {reason}')
    time.sleep(1)
   if child.returncode:
    save(output/'status.json',dict(status='failed',month=month,returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started))
    raise RuntimeError('Monthly warm re-solve failed; inspect log')
   item=json.loads(receipt.read_text());item['peak_rss_bytes']=peak;item['elapsed_seconds']=time.monotonic()-started;item['wall_seconds']=wall_seconds;save(receipt,item)
 save(output/'status.json',dict(status='requested_warm_months_verified',months=args.last_month,
  scope='conditional monthly re-solves, not annual optimisation'))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True)
 p.add_argument('--month',type=int);p.add_argument('--last-month',type=int,default=1);p.add_argument('--memory-gib',type=float,default=6.);p.add_argument('--solver-seconds',type=float,default=300.);p.add_argument('--first-solver',choices=['highs','highs-ipm'],default='highs-ipm')
 p.add_argument('--native-threads',type=int,choices=[1,2],default=1)
 p.add_argument('--native-no-crossover',action='store_true',help='Isolated native IPM audit with corrected primal and dual checks; coordinator default unchanged')
 p.add_argument('--wall-seconds',type=float,help='Whole-worker deadline, including setup and all retries; default 3*solver-seconds+120')
 p.add_argument('--primal-tolerance',type=float,choices=[1e-10,1e-7],default=1e-10,help='Explicit solver tolerance; original-unit acceptance remains 1e-7')
 args=p.parse_args();args.folder=args.folder.resolve()
 if not 1<=args.last_month<=12 or (args.month is not None and not 1<=args.month<=12) or not 0<args.memory_gib<=6 or not 0<args.solver_seconds<=600:p.error('Invalid month/resource limit')
 if args.wall_seconds is not None and not 0<args.wall_seconds<=1920:p.error('Invalid wall-clock limit')
 worker(args) if args.month is not None else run(args)
