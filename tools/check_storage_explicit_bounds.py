"""Test redundant source-implied variable bounds at a failed reference state.

No model constraints removed. Diagnostic only, not coordinator integration.
"""
import json
from dataclasses import replace
from pathlib import Path
import numpy as np
from disk_storage_blocks import load_block
from check_storage_dual_bounds import implied_bounds
from storage_objective_oracle import objective_oracle
from storage_coordinator import solve_block
from monthly_dispatch import digest,save

def run():
 folder=Path(__file__).resolve().parents[1]/'data/pypsa-eur/benchmark-2025-window';failure=folder/'coordination-failure-dual-support.json';r=json.loads(failure.read_text());i=r['block'];state=np.array(r['state_mwh']);path=folder/f'coordination-block-{i}.npz'
 if digest(path)!=r['block_hashes'][i]:raise ValueError('Failure block fingerprint mismatch')
 block=load_block(path);explicit=replace(block,bounds=implied_bounds(block,state))
 solved=solve_block(explicit,state,residual_tolerance=1e-7)
 if solved is None:
  report=dict(status='failed_not_accepted',block_sha256=digest(path),failure_sha256=digest(failure),iteration=r['iteration'],block=i,reason='Explicit-bound LP still reported infeasible',scope='Equivalent local diagnostic; no accepted optimum or cuts')
  save(folder/f'explicit-bounds-{r["iteration"]}-{i}.json',report);print(json.dumps(report,indent=2));return
 result,_=solved;upper,gradient,lower=objective_oracle(block,state,result)
 report=dict(block_sha256=digest(path),failure_sha256=digest(failure),iteration=r['iteration'],block=i,primal_cost_eur=upper,dual_support_eur=lower,gap_eur=upper-lower,scope='Equivalent explicit-bound local diagnostic; original primal and dual-consistency gates; not coordinator or annual validation')
 save(folder/f'explicit-bounds-{r["iteration"]}-{i}.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':run()
