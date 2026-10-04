"""Equivalent positive row-scaling diagnostic at the isolated failed state.

Reconstruct original objective multipliers; audit original-unit primal/dual gates.
This does not enable scaling in the coordinator or change accepted research gates.
"""
import json
from pathlib import Path
import numpy as np
from condition_storage_block import condition_rows
from disk_storage_blocks import load_block
from storage_coordinator import solve_block
from storage_objective_oracle import objective_oracle
from monthly_dispatch import digest,save

def weights(matrix,coupling):
 maxima=np.asarray(abs(matrix).max(axis=1).toarray()).ravel()
 if coupling is not None:maxima=np.maximum(maxima,np.asarray(abs(coupling).max(axis=1).toarray()).ravel())
 return 1./np.maximum(1.,maxima)

def run():
 folder=Path(__file__).resolve().parents[1]/'data/pypsa-eur/benchmark-2025-window';failure=folder/'coordination-failure-dual-support.json';r=json.loads(failure.read_text());i=r['block'];state=np.array(r['state_mwh']);path=folder/f'coordination-block-{i}.npz'
 if digest(path)!=r['block_hashes'][i]:raise ValueError('Block fingerprint mismatch')
 b=load_block(path);report=dict(block_sha256=digest(path),failure_sha256=digest(failure),iteration=r['iteration'],block=i,scope='Local equivalent-scaling diagnostic, not coordinator or annual validation')
 try:
  solved=solve_block(condition_rows(b),state)
  if solved is None:raise RuntimeError('Scaled objective LP still reports infeasible')
  result,_=solved
  result.eqlin.marginals*=weights(b.equality,b.coupling)
  result.ineqlin.marginals*=weights(b.inequality,b.inequality_coupling)
  upper,g,lower=objective_oracle(b,state,result)
  report.update(status='local_gates_passed',primal_cost_eur=upper,dual_support_eur=lower,gap_eur=upper-lower)
 except (RuntimeError,ValueError) as e:report.update(status='failed_not_accepted',reason=str(e))
 save(folder/f'scaled-failure-{r["iteration"]}-{i}.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':run()
