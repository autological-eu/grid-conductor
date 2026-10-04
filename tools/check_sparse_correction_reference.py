"""Real fixed-boundary 24h reference with a deliberate small primal perturbation."""
import json
from pathlib import Path
import numpy as np
from disk_storage_blocks import load_block
from storage_coordinator import solve_block
from sparse_primal_correction import correct_sparse
from monthly_dispatch import save,digest
ROOT=Path(__file__).resolve().parents[1]
def run():
 folder=ROOT/'data/pypsa-eur/benchmark-2025-window';ref=json.loads((folder/'coordination-reference.json').read_text());state=np.array(ref['state_mwh']);path=folder/'coordination-block-0.npz';b=load_block(path)
 original,_=solve_block(b,state,residual_tolerance=1e-7)
 x=original.x.copy();j=next(i for i,(lo,hi) in enumerate(b.bounds) if (lo is None or x[i]-lo>1e-4) and (hi is None or hi-x[i]>1e-4))
 x[j]+=3e-7
 corrected,report=correct_sparse(b,state,x)
 report.update(block_sha256=digest(path),perturbed_variable=j,perturbation=3e-7,cost_difference_eur=float(b.cost@corrected-original.fun),scope='One fixed-boundary real 24h perturbation check; not coordination or annual validation')
 passed=report['original_unit_gate_passed'] and abs(report['cost_difference_eur'])<=.02
 report['status']='reference_check_passed' if passed else 'reference_check_failed'
 save(folder/'sparse-correction-reference.json',report);print(json.dumps(report,indent=2))
 if not passed:raise ValueError('Sparse reference correction failed unchanged gates')
if __name__=='__main__':run()
