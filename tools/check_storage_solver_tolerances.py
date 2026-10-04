"""Isolated solver-tolerance study; original acceptance gates stay unchanged.

No coordinator settings/checkpoints changed. Phase-I duals are never used.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from disk_storage_blocks import load_block
from storage_objective_oracle import objective_oracle
from monthly_dispatch import digest,save

def run():
 folder=Path(__file__).resolve().parents[1]/'data/pypsa-eur/benchmark-2025-window';failure=folder/'coordination-failure-dual-support.json';r=json.loads(failure.read_text());i=r['block'];state=np.array(r['state_mwh']);path=folder/f'coordination-block-{i}.npz'
 if digest(path)!=r['block_hashes'][i]:raise ValueError('Failure fingerprint mismatch')
 b=load_block(path);rhs=b.rhs-b.coupling@state;limit=b.limit-(0 if b.inequality_coupling is None else b.inequality_coupling@state)
 report=dict(block_sha256=digest(path),failure_sha256=digest(failure),trials=[],scope='Isolated tolerance study, original 1e-7 primal/consistency gates; no coordinator change')
 for tolerance in [1e-9,1e-8,1e-7]:
  result=linprog(b.cost,A_eq=b.equality,b_eq=rhs,A_ub=b.inequality,b_ub=limit,bounds=b.bounds,method='highs',options={'time_limit':60.,'primal_feasibility_tolerance':tolerance,'dual_feasibility_tolerance':1e-10})
  trial=dict(solver_primal_tolerance=tolerance,solver_status=int(result.status),solver_success=bool(result.success))
  if result.success:
   try:
    upper,g,lower=objective_oracle(b,state,result)
    trial.update(status='original_gates_passed',primal_cost_eur=upper,dual_support_eur=lower,gap_eur=upper-lower)
    out=folder/f'tolerance-candidate-{tolerance}.npz'
    with out.open('wb') as stream:np.savez_compressed(stream,solver_primal=result.x,equality_duals=result.eqlin.marginals,inequality_duals=result.ineqlin.marginals,state_mwh=state)
    trial['solver_candidate_sha256']=digest(out)
   except (RuntimeError,ValueError) as e:trial.update(status='failed_not_accepted',reason=str(e))
  else:trial['status']='failed_not_accepted'
  report['trials'].append(trial);save(folder/'solver-tolerance-diagnostics.json',report);print(json.dumps(trial),flush=True)
if __name__=='__main__':run()
