import unittest
from types import SimpleNamespace
import numpy as np
from scipy import sparse
from storage_coordinator import Block
from storage_objective_oracle import objective_oracle

class ObjectiveOracleTests(unittest.TestCase):
 def test_primal_within_residual_gate_still_corrected_when_dual_exceeds_cost(self):
  b=Block(np.array([100.]),[(0.,2.)],sparse.csr_matrix([[1.]]),np.array([1.]),sparse.csr_matrix([[0.]]))
  r=SimpleNamespace(x=np.array([1.-1e-8]),eqlin=SimpleNamespace(marginals=np.array([100.])),ineqlin=SimpleNamespace(marginals=np.array([])),lower=SimpleNamespace(marginals=np.array([0.])),upper=SimpleNamespace(marginals=np.array([0.])))
  upper,g,lower=objective_oracle(b,np.array([0.]),r)
  self.assertAlmostEqual(upper,100.);self.assertAlmostEqual(lower,100.)
  self.assertAlmostEqual(r.x[0],1.-1e-8)
 def test_remaining_dual_excess_is_rejected(self):
  from unittest.mock import patch
  b=Block(np.array([100.]),[(0.,2.)],sparse.csr_matrix([[1.]]),np.array([1.]),sparse.csr_matrix([[0.]]))
  r=SimpleNamespace(x=np.array([1.-1e-8]),eqlin=SimpleNamespace(marginals=np.array([100.])),ineqlin=SimpleNamespace(marginals=np.array([])),lower=SimpleNamespace(marginals=np.array([0.])),upper=SimpleNamespace(marginals=np.array([0.])))
  with patch('storage_objective_oracle.correct_sparse',return_value=(r.x,{'original_unit_gate_passed':True})):
   with self.assertRaisesRegex(RuntimeError,'Dual support exceeds'):objective_oracle(b,np.array([0.]),r)

class PrimalFallbackTests(unittest.TestCase):
 def test_fallback_keeps_independent_gate_and_dual_defaults(self):
  from unittest.mock import patch
  from storage_objective_oracle import solve_with_primal_fallback
  with patch('storage_coordinator.solve_block',side_effect=[None,('result','gradient')]) as mock:
   self.assertEqual(solve_with_primal_fallback('block','state'),('result','gradient'))
   self.assertEqual(mock.call_args.kwargs,{'primal_tolerance':1e-7,'residual_tolerance':1e-7})
 def test_strict_success_does_not_fallback(self):
  from unittest.mock import patch
  from storage_objective_oracle import solve_with_primal_fallback
  with patch('storage_coordinator.solve_block',return_value=('result','gradient')) as mock:
   solve_with_primal_fallback('block','state');self.assertEqual(mock.call_count,1)

if __name__=='__main__':unittest.main()
