"""Independently re-solve converged 48h dual-reference inventories.

Original gates, matched hashes and chronology; no annual optimum claim.
"""
import json
from pathlib import Path
import numpy as np
from disk_storage_blocks import load_block
from storage_objective_oracle import solve_with_primal_fallback,objective_oracle
from sparse_primal_correction import correct_sparse
from storage_checkpoint_provenance import fingerprints,verify
from monthly_dispatch import digest,save

def run():
 root=Path(__file__).resolve().parents[1];folder=root/'data/pypsa-eur/benchmark-2025-window';reference=folder/'coordination-reference-dual-support.json';checkpoint=folder/'coordination-cuts-dual-support.json'
 r=json.loads(reference.read_text());cp=json.loads(checkpoint.read_text());verify(cp['dependency_fingerprints'],fingerprints([Path(p) for p in cp['dependency_fingerprints']]))
 if r['status']!='converged' or r['gap']>.001 or abs(r['difference_eur'])>.02:raise ValueError('Reference gates not passed')
 if cp.get('lower_bound_source')!='master_dual' or not cp.get('master_dual') or not cp.get('primal_fallback'):raise ValueError('Wrong reference modes')
 state=np.array(r['state_mwh']);rows=[]
 for i in range(2):
  path=folder/f'coordination-block-{i}.npz';b=load_block(path)
  solved=solve_with_primal_fallback(b,state)
  if solved is None:raise RuntimeError('Final-state block infeasible')
  result,_=solved;upper,g,lower=objective_oracle(b,state,result)
  candidate,checks=correct_sparse(b,state,result.x)
  if not checks['original_unit_gate_passed']:raise RuntimeError('Independent corrected primal gate failed')
  rows.append(dict(block=i,block_sha256=digest(path),re_solved_cost_eur=upper,dual_support_eur=lower,independent_corrected_cost_eur=float(b.cost@candidate),primal_checks=checks))
 total=sum(x['re_solved_cost_eur'] for x in rows);native=r['native_monolithic_cost_eur']
 if abs(total-native)>.02 or abs(total-r['objective'])>.02:raise RuntimeError('Independent objective parity failed')
 report=dict(schema_version=1,status='configured_reference_gates_passed',hours=48,blocks=rows,iterations=r['iterations'],objective_eur=r['objective'],native_cost_eur=native,difference_eur=r['difference_eur'],lower_bound_eur=r['lower_bound'],gap_eur=r['gap'],independent_cost_eur=total,independent_native_difference_eur=total-native,native_input_sha256=digest(folder/'native-input.nc'),audit_tool_sha256=digest(Path(__file__)),reference_sha256=digest(reference),checkpoint_sha256=digest(checkpoint),scope='2025 conditional 48h reference; floating-point numerical validation, not interval certification or annual optimum')
 save(folder/'dual-reference-final-audit.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':run()
