"""Read-only reconstruction of a rejected two-block inventory proposal.

Reuses exact coordinator master/level solves. Does not accept states or modify cuts.
"""
import json
from pathlib import Path
import numpy as np
from scipy import sparse
import pypsa
from storage_coordinator import solve_master,bounded_proposal
from storage_checkpoint_provenance import fingerprints,verify
from monthly_dispatch import digest,save

def run():
 folder=Path(__file__).resolve().parents[1]/'data/pypsa-eur/benchmark-2025-window'
 checkpoint=folder/'coordination-cuts-dual-support.json';r=json.loads(checkpoint.read_text())
 paths=[Path(p) for p in r['dependency_fingerprints']];verify(r['dependency_fingerprints'],fingerprints(paths))
 n=pypsa.Network(folder/'native-input.nc');ns=len(n.storage_units);nx=r['shared_variables'];nb=r['blocks']
 if nx!=3*ns or nb!=2:raise ValueError('Only two-block reference supported')
 initial=n.storage_units.state_of_charge_initial.to_numpy();terminal=n.storage_units_t.state_of_charge_set.iloc[-1].reindex(n.storage_units.index).to_numpy();maximum=(n.storage_units.p_nom*n.storage_units.max_hours).to_numpy()
 bounds=[(v,v) for v in initial]+[(0,v) for v in maximum]+[(v,v) for v in terminal]
 # Identical independent floors from the existing input blocks.
 from disk_storage_blocks import load_block
 from scipy.optimize import linprog
 theta=[]
 for i in range(nb):
  b=load_block(folder/f'coordination-block-{i}.npz');A=b.equality;B=b.coupling;eq=np.asarray(B.getnnz(axis=1))==0;U=b.inequality;V=b.inequality_coupling;keep=np.ones(U.shape[0],dtype=bool) if V is None else np.asarray(V.getnnz(axis=1))==0
  floor=linprog(b.cost,A_eq=A[eq],b_eq=b.rhs[eq],A_ub=U[keep],b_ub=b.limit[keep],bounds=b.bounds,method='highs')
  if not floor.success:raise RuntimeError('Floor reconstruction failed')
  theta.append((float(floor.fun),None))
 cuts=np.array(r['cuts']);limits=np.array(r['limits']);best=np.array(r['best_state']);upper=r['upper_bound']
 master=solve_master(np.r_[np.zeros(nx),np.ones(nb)],A_ub=sparse.csr_matrix(cuts),b_ub=limits,bounds=bounds+theta)
 if not master.success:raise RuntimeError('Master reconstruction failed')
 lower=max(r['lower_bound'],float(master.fun));iteration=r['iteration']+1;state=master.x[:nx]
 if iteration%5!=0:
  level=lower+.5*(upper-lower);width=np.array([max(1.,hi-lo) for lo,hi in bounds])
  original=sparse.hstack([sparse.csr_matrix(cuts),sparse.csr_matrix((len(cuts),nx))],format='csr')
  distance=sparse.vstack([sparse.hstack([sparse.eye(nx),sparse.csr_matrix((nx,nb)),-sparse.eye(nx)]),sparse.hstack([-sparse.eye(nx),sparse.csr_matrix((nx,nb)),-sparse.eye(nx)])],format='csr')
  target=sparse.csr_matrix(np.r_[np.zeros(nx),np.ones(nb),np.zeros(nx)][None,:])
  solve=solve_master(np.r_[np.zeros(nx+nb),1/width],A_ub=sparse.vstack([original,distance,target],format='csr'),b_ub=np.r_[limits,best,-best,level],bounds=bounds+theta+[(0,None)]*nx)
  if not solve.success:raise RuntimeError('Level reconstruction failed')
  state=solve.x[:nx]
 state=bounded_proposal(state,bounds,1e-7)
 # The original reference's first 6*ns rows are its necessary envelopes.
 count=6*ns
 if np.any(cuts[:count,nx:]):raise ValueError('Unexpected envelope layout')
 errors=cuts[:count,:nx]@state-limits[:count];j=int(np.argmax(errors))
 report=dict(checkpoint_sha256=digest(checkpoint),iteration=iteration,lower_bound_eur=lower,maximum_envelope_violation=float(errors[j]),worst_row=j,row_nonzeros=int(np.count_nonzero(cuts[j,:nx])),rhs=float(limits[j]),row_coefficients=cuts[j,:nx].tolist(),state_mwh=state.tolist(),best_state_violation=float(np.max(cuts[:count,:nx]@best-limits[:count])),scope='Read-only master proposal diagnostic; no accepted cuts or annual result')
 save(folder/'master-proposal-diagnostic.json',report)
 print(json.dumps({k:v for k,v in report.items() if k not in ['row_coefficients','state_mwh']},indent=2))
if __name__=='__main__':run()
