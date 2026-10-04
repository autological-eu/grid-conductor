"""Bounded inventory perturbation diagnostics at the failed two-block state.

Move toward the saved feasible incumbent, preserve both fixed endpoints, and
require original primal/dual gates in both blocks. No coordinator cuts modified.
"""
import json
from pathlib import Path
import numpy as np
from disk_storage_blocks import load_block
from storage_coordinator import solve_block
from storage_objective_oracle import objective_oracle
from storage_checkpoint_provenance import fingerprints,verify
from monthly_dispatch import digest,save

def perturb(failed,best,budget):
 failed=np.asarray(failed,dtype=float);best=np.asarray(best,dtype=float)
 if failed.ndim!=1 or failed.shape!=best.shape or len(failed)%3 or not len(failed) or not np.isfinite(failed).all() or not np.isfinite(best).all():raise ValueError('Invalid reference states')
 if not np.isfinite(budget) or budget<=0:raise ValueError('Invalid change budget')
 ns=len(failed)//3
 if not np.array_equal(failed[:ns],best[:ns]) or not np.array_equal(failed[2*ns:],best[2*ns:]):raise ValueError('Fixed endpoints differ')
 direction=best-failed;distance=float(np.max(abs(direction),initial=0))
 if distance==0:raise ValueError('No inventory perturbation direction')
 fraction=min(1.,budget/distance)
 return failed+fraction*direction,fraction

def run():
 folder=Path(__file__).resolve().parents[1]/'data/pypsa-eur/benchmark-2025-window';failure=folder/'coordination-failure-dual-support.json';checkpoint=folder/'coordination-cuts-dual-support.json'
 f=json.loads(failure.read_text());r=json.loads(checkpoint.read_text());verify(r['dependency_fingerprints'],fingerprints([Path(p) for p in r['dependency_fingerprints']]))
 failed=np.array(f['state_mwh']);best=np.array(r['best_state']);ns=len(failed)//3
 if len(failed)!=3*ns or r['blocks']!=2:raise ValueError('Only two-block reference supported')
 if not np.array_equal(failed[:ns],best[:ns]) or not np.array_equal(failed[2*ns:],best[2*ns:]):raise ValueError('Fixed endpoints differ')
 direction=best-failed;distance=float(np.max(abs(direction),initial=0))
 if distance==0:raise ValueError('No inventory perturbation direction')
 paths=[folder/f'coordination-block-{i}.npz' for i in range(2)]
 if [digest(p) for p in paths]!=f['block_hashes']:raise ValueError('Block fingerprints changed')
 report=dict(failure_sha256=digest(failure),checkpoint_sha256=digest(checkpoint),block_sha256=f['block_hashes'],trials=[],scope='Two-block perturbation feasibility/objective diagnostics; not convergence or annual validation')
 for budget in [1e-5,1e-3,.1]:
  state,fraction=perturb(failed,best,budget)
  if not np.array_equal(state[:ns],failed[:ns]) or not np.array_equal(state[2*ns:],failed[2*ns:]):raise ValueError('Perturbation changed endpoints')
  trial=dict(maximum_change_budget_mwh=budget,maximum_actual_change_mwh=float(np.max(abs(state-failed))),fraction_toward_incumbent=fraction,blocks=[],state_mwh=state.tolist())
  for i,path in enumerate(paths):
   b=load_block(path)
   try:
    solved=solve_block(b,state)
    if solved is None:raise RuntimeError('Objective LP reports infeasible')
    result,_=solved;upper,g,lower=objective_oracle(b,state,result)
    trial['blocks'].append(dict(block=i,status='local_gates_passed',primal_cost_eur=upper,dual_support_eur=lower,gap_eur=upper-lower))
   except (RuntimeError,ValueError) as e:trial['blocks'].append(dict(block=i,status='failed_not_accepted',reason=str(e)))
  trial['both_blocks_passed']=all(x['status']=='local_gates_passed' for x in trial['blocks']);report['trials'].append(trial)
  save(folder/'inventory-perturbation-diagnostics.json',report)
  print(json.dumps({k:v for k,v in trial.items() if k!='state_mwh'}),flush=True)
  if trial['both_blocks_passed']:break
if __name__=='__main__':run()
