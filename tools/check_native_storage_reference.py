"""Audit isolated no-crossover native solves at the verified 48h boundary state."""
import json
from pathlib import Path
import numpy as np
from disk_storage_blocks import load_block
from monthly_dispatch import digest, save
from native_storage_solver import solve_native
from sparse_primal_correction import correct_sparse
from storage_objective_oracle import objective_oracle

root=Path(__file__).resolve().parents[1]
folder=root/'data/pypsa-eur/benchmark-2025-window'
reference=folder/'coordination-reference-dual-support.json'
saved=json.loads(reference.read_text())
if saved['status']!='converged':raise ValueError('Verified converged reference required')
state=np.asarray(saved['state_mwh']);rows=[]
for i in range(2):
    path=folder/f'coordination-block-{i}.npz';b=load_block(path)
    result=solve_native(b,state)
    if result is None:raise RuntimeError('Native reference reported infeasible')
    candidate,checks=correct_sparse(b,state,result.x)
    if not checks['original_unit_gate_passed']:raise RuntimeError('Native corrected primal gate failed')
    upper,gradient,lower=objective_oracle(b,state,result)
    rows.append(dict(block=i,block_sha256=digest(path),primal_cost_eur=upper,dual_support_eur=lower,local_gap_eur=upper-lower,primal=checks))
objective=sum(row['primal_cost_eur'] for row in rows)
difference=objective-saved['native_monolithic_cost_eur']
if abs(difference)>.02:raise RuntimeError('Native/reference cost parity gate failed')
result=dict(status='fixed_reference_numerical_gates_passed',reference_sha256=digest(reference),
            dependencies={name:digest(Path(__file__).with_name(name)) for name in ['native_storage_solver.py','storage_objective_oracle.py','check_storage_dual_bounds.py','sparse_primal_correction.py','disk_storage_blocks.py']},
            hours=48,objective_eur=objective,native_difference_eur=difference,rows=rows,
            scope='Two fixed 24h blocks at converged conditional inventory; no annual or new coordinator convergence claim')
save(folder/'native-no-crossover-reference.json',result)
print(json.dumps(result,indent=2))
