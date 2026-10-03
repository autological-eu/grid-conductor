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
 with np.load(args.folder/'master-state.npz',allow_pickle=False) as data:state=data['warm_state_mwh'].copy()
 block=load_block(args.folder/f'{args.month:02d}.npz')
 local=solve_block(block,state,time_limit=args.solver_seconds,first_method=args.first_solver)
 if local is None:raise ValueError('Fixed warm inventories infeasible')
 r,_=local
 eq=float(np.max(abs(block.equality@r.x+block.coupling@state-block.rhs)))
 ub=float(max(0.,np.max(block.inequality@r.x+block.inequality_coupling@state-block.limit)))
 bound=max([0.]+[max(0.,lo-x) if lo is not None else 0. for x,(lo,hi) in zip(r.x,block.bounds)]+[max(0.,x-hi) if hi is not None else 0. for x,(lo,hi) in zip(r.x,block.bounds)])
 if max(eq,ub,bound)>1e-7:
  save(args.folder/'warm-audit'/f'{args.month:02d}-rejected.json',dict(**signature,
   month=args.month,status='rejected_original_unit_residuals',cost_eur=float(r.fun),
   max_equality_residual=eq,max_inequality_violation=ub,max_bound_violation=bound,
   solver_seconds=args.solver_seconds,first_solver=args.first_solver,
   scope='diagnostic only; not accepted feasibility or an annual result'))
  raise ValueError(f'Original-unit primal residual gate failed: equality={eq:.12g}, inequality={ub:.12g}, bounds={bound:.12g}')
 save(args.folder/'warm-audit'/f'{args.month:02d}.json',dict(**signature,month=args.month,cost_eur=float(r.fun),
  max_equality_residual=eq,max_inequality_violation=ub,max_bound_violation=bound,
  solver_seconds=args.solver_seconds,first_solver=args.first_solver,scope='verified fixed monthly inventories only; no annual optimum'))
def run(args):
 output=args.folder/'warm-audit';output.mkdir(exist_ok=True)
 for month in range(1,args.last_month+1):
  signature=receipts(args,month);receipt=output/f'{month:02d}.json'
  if receipt.exists():
   item=json.loads(receipt.read_text())
   if any(item.get(k)!=v for k,v in signature.items()):raise ValueError('Warm audit/source mismatch')
   continue
  with (output/f'{month:02d}.log').open('w') as log:
   child=subprocess.Popen([sys.executable,__file__,'--folder',str(args.folder),'--month',str(month),'--solver-seconds',str(args.solver_seconds),'--first-solver',args.first_solver],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save(output/'status.json',dict(status='solving_fixed_inventories',month=month,pid=child.pid))
   peak=0
   while child.poll() is None:
    try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
    except FileNotFoundError:rss=0
    peak=max(peak,rss)
    if rss>args.memory_gib*2**30:
     os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=30)
     save(output/'status.json',dict(status='stopped_memory_guard',month=month,peak_rss_bytes=peak))
     raise RuntimeError('Monthly warm re-solve exceeded memory guard')
    time.sleep(1)
   if child.returncode:
    save(output/'status.json',dict(status='failed',month=month,returncode=child.returncode,peak_rss_bytes=peak))
    raise RuntimeError('Monthly warm re-solve failed; inspect log')
   item=json.loads(receipt.read_text());item['peak_rss_bytes']=peak;save(receipt,item)
 save(output/'status.json',dict(status='requested_warm_months_verified',months=args.last_month,
  scope='conditional monthly re-solves, not annual optimisation'))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True)
 p.add_argument('--month',type=int);p.add_argument('--last-month',type=int,default=1);p.add_argument('--memory-gib',type=float,default=6.);p.add_argument('--solver-seconds',type=float,default=300.);p.add_argument('--first-solver',choices=['highs','highs-ipm'],default='highs-ipm')
 args=p.parse_args();args.folder=args.folder.resolve()
 if not 1<=args.last_month<=12 or (args.month is not None and not 1<=args.month<=12) or not 0<args.memory_gib<=6 or not 0<args.solver_seconds<=600:p.error('Invalid month/resource limit')
 worker(args) if args.month is not None else run(args)
