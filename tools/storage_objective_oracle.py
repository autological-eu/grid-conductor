"""Opt-in numerical primal/dual separation for coordinator reference validation.

Not rigorous interval certification. Original-unit feasibility remains mandatory.
"""
import numpy as np
from check_storage_dual_bounds import objective_support
from sparse_primal_correction import correct_sparse

def objective_oracle(block,state,result):
 eq=float(np.max(abs(block.equality@result.x+block.coupling@state-block.rhs),initial=0))
 ub=0. if block.inequality is None else float(np.max(block.inequality@result.x+(0 if block.inequality_coupling is None else block.inequality_coupling@state)-block.limit,initial=0))
 violation=max([0.]+[lo-v for v,(lo,hi) in zip(result.x,block.bounds) if lo is not None]+[v-hi for v,(lo,hi) in zip(result.x,block.bounds) if hi is not None])
 candidate=result.x
 if max(eq,ub,violation)>1e-7:
  candidate,checks=correct_sparse(block,state,result.x)
  if not checks['original_unit_gate_passed']:raise RuntimeError('Corrected objective candidate fails original-unit primal gates')
 upper=float(block.cost@candidate)
 gradient,intercept=objective_support(block,state,result)
 lower=float(intercept+gradient@state)
 if not np.isfinite(upper) or not np.isfinite(lower) or not np.isfinite(gradient).all():raise RuntimeError('Nonfinite objective oracle')
 if lower>upper+1e-7:raise RuntimeError(f'Dual support exceeds primal upper value: excess={lower-upper:.12g} EUR, lower={lower:.12g}, upper={upper:.12g}, equality={eq:.12g}, inequality={ub:.12g}, bounds={violation:.12g}')
 return upper,gradient,lower
