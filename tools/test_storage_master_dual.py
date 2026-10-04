import unittest
import numpy as np
from storage_coordinator import solve_master
from storage_master_dual import master_dual
class MasterDualTests(unittest.TestCase):
 def test_original_units_and_independence_from_primal_objective(self):
  c=np.array([0.,1.]);A=np.array([[-1.,-1.]]);b=np.array([-10.]);bounds=[(0.,5.),(0.,None)]
  r=solve_master(c,A_ub=A,b_ub=b,bounds=bounds)
  r.fun=1000. # An invalid primal objective must not become a lower bound.
  value=master_dual(c,A,b,bounds,r,1)['lower_bound_eur']
  self.assertLessEqual(value,5.+1e-10);self.assertAlmostEqual(value,5.)
 def test_negative_theta_reduced_cost_is_repaired_by_multipliers(self):
  c=np.array([0.,1.]);A=np.array([[-1.,-1.]]);b=np.array([-10.]);bounds=[(0.,5.),(0.,None)]
  r=solve_master(c,A_ub=A,b_ub=b,bounds=bounds);r.ineqlin.marginals*=1.+1e-8
  d=master_dual(c,A,b,bounds,r,1)
  self.assertGreaterEqual(d['minimum_theta_reduced_cost'],0.);self.assertLessEqual(d['lower_bound_eur'],5.+1e-10)
if __name__=='__main__':unittest.main()
