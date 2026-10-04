"""Check fixed-state dual supports at another real feasible inventory state.

This is a two-block numerical check, not full coordinator or annual validation.
It reads existing solved chronology without changing preparation or receipts.
"""
import json
from pathlib import Path
import numpy as np
import pypsa
from check_storage_dual_bounds import objective_support
from disk_storage_blocks import load_block
from storage_coordinator import solve_block
from sparse_primal_correction import correct_sparse
from monthly_dispatch import save,digest

def run():
 folder=Path(__file__).resolve().parents[1]/'data/pypsa-eur/benchmark-2025-window'
 reference=folder/'coordination-reference.json'
 state=np.array(json.loads(reference.read_text())['state_mwh'])
 source=folder/'native-input.nc';n=pypsa.Network(source)
 monthly=folder.parent/'monthly-dispatch-sequential/01.nc';warm=pypsa.Network(monthly)
 ids=n.storage_units.index;ns=len(ids)
 target=state.copy();target[ns:2*ns]=warm.storage_units_t.state_of_charge.iloc[23].reindex(ids).to_numpy()
 rows=[]
 for i in range(2):
  path=folder/f'coordination-block-{i}.npz';block=load_block(path)
  origin,_=solve_block(block,state,residual_tolerance=1e-7)
  gradient,intercept=objective_support(block,state,origin)
  other,_=solve_block(block,target,residual_tolerance=1e-7)
  candidate,checks=correct_sparse(block,target,other.x)
  support=float(intercept+gradient@target);cost=float(block.cost@candidate)
  if not checks['original_unit_gate_passed']:raise RuntimeError('Alternate-state primal gate failed')
  if support>cost+1e-7:raise RuntimeError('Support exceeds alternate-state feasible cost')
  rows.append(dict(block=i,block_sha256=digest(path),support_eur=support,feasible_cost_eur=cost,slack_eur=cost-support,primal=checks))
 report=dict(reference_sha256=digest(reference),native_input_sha256=digest(source),warm_source_sha256=digest(monthly),origin_state_mwh=state.tolist(),alternate_state_mwh=target.tolist(),rows=rows,scope='Floating-point supporting-plane check at sequential warm inventory; not coordinator convergence or annual certificate')
 save(folder/'inventory-support-diagnostics.json',report)
 print(json.dumps({**report,'origin_state_mwh':'saved in receipt','alternate_state_mwh':'saved in receipt'},indent=2))
if __name__=='__main__':run()
