import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import Block,solve_block
from condition_storage_block import condition_rows
from check_storage_scaled_failure import weights
from storage_objective_oracle import objective_oracle
class ScaledFailureTests(unittest.TestCase):
 def test_original_dual_units_preserve_objective_and_inventory_gradient(self):
  b=Block(np.array([3.]),[(0.,4.)],sparse.csr_matrix([[100.]]),np.array([200.]),sparse.csr_matrix([[10.]]))
  r,_=solve_block(condition_rows(b),np.array([1.]))
  r.eqlin.marginals*=weights(b.equality,b.coupling)
  upper,g,lower=objective_oracle(b,np.array([1.]),r)
  self.assertAlmostEqual(upper,5.7);self.assertAlmostEqual(lower,5.7);self.assertAlmostEqual(g[0],-.3)
 def test_coupling_and_negative_coefficients_use_positive_scaling(self):
  self.assertEqual(weights(sparse.csr_matrix([[-2.]]),sparse.csr_matrix([[4.]]))[0],.25)
if __name__=='__main__':unittest.main()
