import unittest
from types import SimpleNamespace
import numpy as np
from scipy import sparse
from storage_coordinator import Block
from check_storage_dual_bounds import diagnostic, implied_bounds, objective_support
class DualBounds(unittest.TestCase):
 def check(self,bounds,y):
  b=Block(np.array([1.]),[bounds],sparse.csr_matrix([[1.]]),np.array([1.]),sparse.csr_matrix([[0.]]))
  r=SimpleNamespace(eqlin=SimpleNamespace(marginals=np.array([y])),ineqlin=SimpleNamespace(marginals=np.array([])),lower=SimpleNamespace(marginals=np.array([0.])),upper=SimpleNamespace(marginals=np.array([0.])))
  return diagnostic(b,np.array([0.]),r)
 def test_exact_dual_matches_optimum(self):self.assertEqual(self.check((0,None),1.)['lower_bound_eur'],1.)
 def test_tiny_negative_unbounded_reduced_cost_not_clamped(self):
  r=self.check((0,None),1.+1e-12);self.assertIsNone(r['lower_bound_eur']);self.assertEqual(r['unbounded_reduced_cost_count'],1)
 def test_finite_bound_penalty_preserved(self):self.assertAlmostEqual(self.check((0,2),1.01)['lower_bound_eur'],.99)
 def test_source_bounds_include_sign_and_state_coupling(self):
  b=Block(np.zeros(2),[(None,None),(None,None)],sparse.csr_matrix([[2.,0.]]),np.array([8.]),sparse.csr_matrix([[2.]]),sparse.csr_matrix([[0.,-2.],[0.,1.]]),np.array([-6.,7.]),sparse.csr_matrix([[0.],[1.]]))
  self.assertEqual(implied_bounds(b,np.array([1.])),[[3.,3.],[3.,6.]])
 def test_affine_support_across_inventory_states(self):
  # x = 2 - state, 0 <= x <= 3. Deliberately inexact multiplier.
  b=Block(np.array([1.]),[(0.,3.)],sparse.csr_matrix([[1.]]),np.array([2.]),sparse.csr_matrix([[1.]]))
  r=SimpleNamespace(eqlin=SimpleNamespace(marginals=np.array([1.01])),ineqlin=SimpleNamespace(marginals=np.array([])),lower=SimpleNamespace(marginals=np.array([0.])),upper=SimpleNamespace(marginals=np.array([0.])))
  g,a=objective_support(b,np.array([0.]),r)
  for state in np.linspace(-1.,2.,21):self.assertLessEqual(float(a+g@np.array([state])),2.-state+1e-14)
  self.assertLess(a,2.)
 def test_global_bounds_exclude_inventory_dependent_rows(self):
  b=Block(np.zeros(2),[(None,None),(None,None)],sparse.csr_matrix([[2.,0.]]),np.array([8.]),sparse.csr_matrix([[2.]]),sparse.csr_matrix([[0.,-2.],[0.,1.]]),np.array([-6.,7.]),sparse.csr_matrix([[0.],[1.]]))
  self.assertEqual(implied_bounds(b,np.array([1.]),state_independent=True),[[None,None],[3.,None]])
 def test_inconsistent_implied_bounds_rejected(self):
  b=Block(np.ones(1),[(0.,.5)],sparse.csr_matrix([[1.]]),np.array([1.]),sparse.csr_matrix([[0.]]))
  with self.assertRaises(ValueError):implied_bounds(b,np.array([0.]))
if __name__=='__main__':unittest.main()
