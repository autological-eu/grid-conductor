"""Compare row-conditioned local solves at the saved 48h reference state."""
import json
from pathlib import Path
import numpy as np
from disk_storage_blocks import load_block
from condition_storage_block import condition_rows
from storage_coordinator import solve_block
from monthly_dispatch import digest,save
ROOT=Path(__file__).resolve().parents[1]
def run():
 folder=ROOT/'data/pypsa-eur/benchmark-2025-window';reference=json.loads((folder/'coordination-reference.json').read_text());state=np.array(reference['state_mwh']);rows=[]
 for i in range(2):
  path=folder/f'coordination-block-{i}.npz';block=load_block(path);scaled=condition_rows(block)
  original,gradient=solve_block(block,state,residual_tolerance=1e-7)
  result,scaled_gradient=solve_block(scaled,state)
  eq=float(np.max(abs(block.equality@result.x+block.coupling@state-block.rhs)))
  ub=float(np.max(block.inequality@result.x+block.inequality_coupling@state-block.limit,initial=0))
  bound=max([0.]+[max(0.,lo-x) if lo is not None else 0. for x,(lo,hi) in zip(result.x,block.bounds)]+[max(0.,x-hi) if hi is not None else 0. for x,(lo,hi) in zip(result.x,block.bounds)])
  row=dict(block=i,sha256=digest(path),cost_difference_eur=float(result.fun-original.fun),gradient_max_difference=float(np.max(abs(gradient-scaled_gradient))),original_unit_equality_residual=eq,inequality_violation=ub,bound_violation=bound)
  if max(eq,ub,bound)>1e-7 or abs(row['cost_difference_eur'])>.02:
   save(folder/'conditioning-reference.json',dict(status='local_fixed_state_gate_failed',rows=rows+[row],scope='Rejected row-scaling experiment; not suitable for annual use'))
   raise ValueError(f'Conditioning reference gate failed: {row}')
  rows.append(row)
 save(folder/'conditioning-reference.json',dict(status='local_fixed_state_checks_passed',rows=rows,scope='Fixed-boundary row-scaling experiment only; not coordination or annual validation'))
 print(json.dumps(rows,indent=2))
if __name__=='__main__':run()
