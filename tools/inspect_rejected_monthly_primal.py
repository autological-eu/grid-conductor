"""Inspect rejected LP equality rows; diagnostics never certify feasibility."""
import argparse,json,math
from pathlib import Path
import numpy as np
from disk_storage_blocks import load_block
from monthly_dispatch import digest,save

def inspect(folder,month,kind="rejected"):
 root=folder/'warm-audit'
 if kind=='sparse-corrected':
  report=json.loads((root/f'{month:02d}-sparse-correction.json').read_text())
  receipt=dict(report['source'],primal_sha256=report['corrected_primal_sha256'],cost_eur=report['corrected_cost_eur'],scope=report['scope'])
  primal_path=root/f'{month:02d}-sparse-corrected-primal.npz'
 else:
  receipt=json.loads((root/f'{month:02d}-rejected-primal.json').read_text());primal_path=root/f'{month:02d}-rejected-primal.npz'
 block_path=folder/f'{month:02d}.npz';state_path=folder/'master-state.npz'
 for path,key in [(block_path,'block_sha256'),(primal_path,'primal_sha256'),(state_path,'warm_state_sha256')]:
  if digest(path)!=receipt[key]:raise ValueError('Rejected candidate fingerprint mismatch')
 block=load_block(block_path)
 with np.load(primal_path,allow_pickle=False) as data:x=data['primal']
 with np.load(state_path,allow_pickle=False) as data:state=data['warm_state_mwh']
 residual=block.equality@x+block.coupling@state-block.rhs
 indices=np.argsort(np.abs(residual))[-100:][::-1];rows=[]
 for i in indices:
  a=block.equality.getrow(i);c=block.coupling.getrow(i)
  terms=[float(v)*float(x[j]) for j,v in zip(a.indices,a.data)]+[float(v)*float(state[j]) for j,v in zip(c.indices,c.data)]+[-float(block.rhs[i])]
  compensated=math.fsum(terms)
  # Extended products and sum distinguish multiplication from summation error.
  extended=np.sum(a.data.astype(np.longdouble)*x[a.indices].astype(np.longdouble),dtype=np.longdouble)+np.sum(c.data.astype(np.longdouble)*state[c.indices].astype(np.longdouble),dtype=np.longdouble)-np.longdouble(block.rhs[i])
  rows.append(dict(row=int(i),csr_residual=float(residual[i]),compensated_sum_residual=compensated,extended_precision_residual=float(extended),rhs=float(block.rhs[i]),nonzeros=len(terms)-1,sum_absolute_terms=math.fsum(abs(v) for v in terms),max_absolute_coefficient=float(np.max(abs(a.data),initial=0.)),min_nonzero_absolute_coefficient=float(np.min(abs(a.data[a.data!=0]))) if np.any(a.data!=0) else None))
 result=dict(month=month,source=receipt,max_csr_equality_residual=float(np.max(abs(residual))),rows=rows,
  scope='Worst 100 CSR equality rows only; extended arithmetic diagnostic, not acceptance or a full audit')
 save(root/(f'{month:02d}-corrected-row-diagnostics.json' if kind=='sparse-corrected' else f'{month:02d}-row-diagnostics.json'),result)
 print(json.dumps(dict(month=month,max_csr=result['max_csr_equality_residual'],worst_row=rows[0]),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);p.add_argument('--month',type=int,default=1);p.add_argument('--kind',choices=['rejected','sparse-corrected'],default='rejected');a=p.parse_args();inspect(a.folder,a.month,a.kind)
