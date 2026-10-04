"""Experimental sparse least-squares primal correction, not an optimality oracle."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.sparse.linalg import lsmr
from disk_storage_blocks import load_block
from monthly_dispatch import digest,save

def correct_sparse(block,state,primal,iterations=100):
 x=np.asarray(primal,dtype=float).copy()
 # Freeze variables at/near bounds; no projection or clipping of the solution.
 free=np.array([(lo is None or v-lo>1e-6) and (hi is None or hi-v>1e-6) for v,(lo,hi) in zip(x,block.bounds)])
 if not free.any():raise ValueError('No interior variables available for correction')
 residual=block.rhs-block.coupling@state-block.equality@x
 matrix=block.equality[:,free].tocsr()
 solve=lsmr(matrix,residual,atol=1e-14,btol=1e-14,maxiter=iterations)
 x[free]+=solve[0]
 eq=float(np.max(abs(block.equality@x+block.coupling@state-block.rhs),initial=0))
 ub=0. if block.inequality is None else float(np.max(block.inequality@x+(0 if block.inequality_coupling is None else block.inequality_coupling@state)-block.limit,initial=0))
 bound=max([0.]+[max(0.,lo-v) if lo is not None else 0. for v,(lo,hi) in zip(x,block.bounds)]+[max(0.,v-hi) if hi is not None else 0. for v,(lo,hi) in zip(x,block.bounds)])
 return x,dict(lsmr_stop_code=int(solve[1]),lsmr_iterations=int(solve[2]),free_variables=int(free.sum()),max_equality_residual=eq,max_inequality_violation=ub,max_bound_violation=bound,maximum_correction=float(np.max(abs(x-primal),initial=0)),cost_change_eur=float(block.cost@(x-primal)),original_unit_gate_passed=max(eq,ub,bound)<=1e-7)

def run(folder,month):
 root=folder/'warm-audit';meta=json.loads((root/f'{month:02d}-rejected-primal.json').read_text())
 files=[(folder/f'{month:02d}.npz','block_sha256'),(root/f'{month:02d}-rejected-primal.npz','primal_sha256'),(folder/'master-state.npz','warm_state_sha256')]
 for p,k in files:
  if digest(p)!=meta[k]:raise ValueError('Rejected candidate fingerprint mismatch')
 block=load_block(files[0][0])
 with np.load(files[1][0],allow_pickle=False) as d:x=d['primal']
 with np.load(files[2][0],allow_pickle=False) as d:state=d['warm_state_mwh']
 candidate,report=correct_sparse(block,state,x)
 report.update(source=meta,scope='Sparse correction diagnostic only; no accepted objective cuts or annual optimality')
 if report['original_unit_gate_passed']:
  target=root/f'{month:02d}-sparse-corrected-primal.npz';temporary=target.with_suffix('.npz.tmp')
  with temporary.open('wb') as stream:np.savez_compressed(stream,primal=candidate)
  temporary.replace(target);report['corrected_primal_sha256']=digest(target);report['corrected_cost_eur']=float(block.cost@candidate)
 save(root/f'{month:02d}-sparse-correction.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);p.add_argument('--month',type=int,default=1);p.add_argument('--worker',action='store_true');a=p.parse_args()
 if a.worker:run(a.folder,a.month)
 else:
  from refine_rejected_primal import guarded
  guarded(a.folder,a.month,worker_file=__file__,label='sparse-correction')
