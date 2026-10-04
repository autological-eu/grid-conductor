"""Diagnostic LP dual bounds at the real fixed-boundary reference state.

Floating-point diagnostics are not rigorous interval certificates. A negative
reduced cost on an unbounded-above variable makes this bound unavailable;
never silently discard it or treat it as zero.
"""
import json,math
from pathlib import Path
import numpy as np
from disk_storage_blocks import load_block
from storage_coordinator import solve_block
from sparse_primal_correction import correct_sparse
from monthly_dispatch import save,digest

def implied_bounds(block,state):
 bounds=[list(pair) for pair in block.bounds]
 matrices=[(block.equality,block.rhs-block.coupling@state,True)]
 if block.inequality is not None:matrices.append((block.inequality,block.limit-(0 if block.inequality_coupling is None else block.inequality_coupling@state),False))
 for matrix,rhs,equality in matrices:
  matrix=matrix.tocsr()
  for row in range(matrix.shape[0]):
   start,end=matrix.indptr[row:row+2];indices=matrix.indices[start:end];data=matrix.data[start:end];nonzero=np.flatnonzero(data)
   if len(nonzero)!=1:continue
   k=nonzero[0];j=indices[k];value=float(rhs[row]/data[k]);lo,hi=bounds[j]
   if equality or data[k]<0:lo=value if lo is None else max(lo,value)
   if equality or data[k]>0:hi=value if hi is None else min(hi,value)
   if lo is not None and hi is not None and lo>hi:raise ValueError('Inconsistent source-implied bounds')
   bounds[j]=[lo,hi]
 return bounds

def diagnostic(block,state,result,use_implied=False):
 y=np.asarray(result.eqlin.marginals);z=np.minimum(np.asarray(result.ineqlin.marginals),0.)
 rhs=block.rhs-block.coupling@state
 reduced=block.cost-block.equality.T@y
 constant=math.fsum(float(a)*float(b) for a,b in zip(y,rhs))
 if block.inequality is not None:
  limit=block.limit-(0 if block.inequality_coupling is None else block.inequality_coupling@state)
  reduced-=block.inequality.T@z;constant+=math.fsum(float(a)*float(b) for a,b in zip(z,limit))
 terms=[];unbounded=[]
 bounds=implied_bounds(block,state) if use_implied else block.bounds
 for j,(value,(lo,hi)) in enumerate(zip(reduced,bounds)):
  endpoint=lo if value>=0 else hi
  if value!=0 and (endpoint is None or not np.isfinite(endpoint)):unbounded.append(dict(variable=j,reduced_cost=float(value)))
  else:terms.append(0. if value==0 else float(value)*float(endpoint))
 lower=None if unbounded else constant+math.fsum(terms)
 stationarity=reduced-np.asarray(result.lower.marginals)-np.asarray(result.upper.marginals)
 return dict(lower_bound_eur=lower,unbounded_reduced_cost_count=len(unbounded),unbounded_examples=unbounded[:10],max_stationarity_residual=float(np.max(abs(stationarity),initial=0)),scope='Floating-point diagnostic, not rigorous interval certification')

def run():
 root=Path(__file__).resolve().parents[1];folder=root/'data/pypsa-eur/benchmark-2025-window'
 ref=json.loads((folder/'coordination-reference.json').read_text());state=np.array(ref['state_mwh']);rows=[]
 for i in range(2):
  path=folder/f'coordination-block-{i}.npz';block=load_block(path);result,_=solve_block(block,state,residual_tolerance=1e-7)
  candidate,primal=correct_sparse(block,state,result.x)
  dual=diagnostic(block,state,result);implied=diagnostic(block,state,result,use_implied=True);upper=float(block.cost@candidate)
  rows.append(dict(block=i,block_sha256=digest(path),primal=primal,dual=dual,source_implied_bound=implied,source_implied_gap_eur=None if implied['lower_bound_eur'] is None else upper-implied['lower_bound_eur'],primal_cost_eur=upper,duality_gap_eur=None if dual['lower_bound_eur'] is None else upper-dual['lower_bound_eur']))
 report=dict(reference_sha256=digest(folder/'coordination-reference.json'),state_mwh=state.tolist(),rows=rows,scope='Two fixed-boundary 24h dual diagnostics; not coordinator or annual validation')
 save(folder/'dual-bound-diagnostics.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':run()
