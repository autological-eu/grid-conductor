"""Bounded diagnostic feasibility correction; never an optimality oracle."""
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from disk_storage_blocks import load_block
from monthly_dispatch import digest,save

def correct(block,state,primal,radius=1e-6,seconds=60):
 if not np.isfinite(radius) or radius<=0 or not np.isfinite(seconds) or seconds<=0:raise ValueError('Invalid correction limits')
 bounds=[(max(-radius,lo-x) if lo is not None else -radius,min(radius,hi-x) if hi is not None else radius) for x,(lo,hi) in zip(primal,block.bounds)]
 if any(lo>hi for lo,hi in bounds):raise ValueError('Candidate outside correction box')
 rhs=block.rhs-block.coupling@state-block.equality@primal
 limit=None if block.inequality is None else block.limit-block.inequality_coupling@state-block.inequality@primal
 result=linprog(np.zeros(len(primal)),A_eq=block.equality,b_eq=rhs,A_ub=block.inequality,b_ub=limit,bounds=bounds,method='highs-ds',options={'time_limit':seconds,'primal_feasibility_tolerance':1e-10,'dual_feasibility_tolerance':1e-10})
 if not result.success:raise RuntimeError(f'Correction LP failed: status {result.status}')
 x=primal+result.x
 eq=float(np.max(abs(block.equality@x+block.coupling@state-block.rhs),initial=0))
 ub=0. if block.inequality is None else float(np.max(block.inequality@x+block.inequality_coupling@state-block.limit,initial=0))
 bound=max([0.]+[max(0.,lo-v) if lo is not None else 0. for v,(lo,hi) in zip(x,block.bounds)]+[max(0.,v-hi) if hi is not None else 0. for v,(lo,hi) in zip(x,block.bounds)])
 return x,dict(max_equality_residual=eq,max_inequality_violation=ub,max_bound_violation=bound,maximum_correction=float(np.max(abs(result.x),initial=0)),cost_change_eur=float(block.cost@result.x),corrected_cost_eur=float(block.cost@x),original_unit_gate_passed=max(eq,ub,bound)<=1e-7)

def run(folder,month):
 root=folder/'warm-audit';meta=json.loads((root/f'{month:02d}-rejected-primal.json').read_text());paths=[(folder/f'{month:02d}.npz','block_sha256'),(root/f'{month:02d}-rejected-primal.npz','primal_sha256'),(folder/'master-state.npz','warm_state_sha256')]
 for p,k in paths:
  if digest(p)!=meta[k]:raise ValueError('Rejected candidate fingerprint mismatch')
 block=load_block(paths[0][0])
 with np.load(paths[1][0],allow_pickle=False) as d:x=d['primal']
 with np.load(paths[2][0],allow_pickle=False) as d:state=d['warm_state_mwh']
 candidate,report=correct(block,state,x)
 report.update(source=meta,scope='Diagnostic corrected primal only; no accepted monthly optimum, objective cut or annual certificate')
 save(root/f'{month:02d}-correction-diagnostic.json',report)
 if report['original_unit_gate_passed']:
  with (root/f'{month:02d}-corrected-diagnostic.npz').open('wb') as f:np.savez_compressed(f,primal=candidate)
 print(json.dumps(report,indent=2))
def guarded(folder,month):
 root=folder/'warm-audit';started=time.monotonic();peak=0;reason=None
 with (root/'correction.log').open('w') as log:
  child=subprocess.Popen([sys.executable,__file__,'--folder',str(folder),'--month',str(month),'--worker'],stdout=log,stderr=log,start_new_session=True)
  save(root/'correction-status.json',dict(status='running_diagnostic',pid=child.pid))
  while child.poll() is None:
   try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
   except FileNotFoundError:rss=0
   peak=max(peak,rss)
   if rss>6*2**30 or time.monotonic()-started>120:
    reason='memory_guard' if rss>6*2**30 else 'wall_time_guard'
    os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=30);break
   time.sleep(.5)
 save(root/'correction-status.json',dict(status='diagnostic_finished' if child.returncode==0 else 'diagnostic_failed',returncode=child.returncode,peak_rss_bytes=peak,stop_reason=reason))
 if child.returncode:raise RuntimeError('Correction diagnostic failed; no accepted result')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);p.add_argument('--month',type=int,default=1);p.add_argument('--worker',action='store_true');a=p.parse_args();run(a.folder,a.month) if a.worker else guarded(a.folder,a.month)
