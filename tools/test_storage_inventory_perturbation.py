import unittest
import numpy as np
from check_storage_inventory_perturbation import perturb
class InventoryPerturbationTests(unittest.TestCase):
 def test_budget_and_fixed_endpoints(self):
  a=np.array([2.,100.,4.]);b=np.array([2.,200.,4.]);p,f=perturb(a,b,.001)
  self.assertEqual(p[0],2.);self.assertEqual(p[2],4.)
  self.assertAlmostEqual(p[1]-a[1],.001);self.assertAlmostEqual(f,1e-5)
 def test_never_extrapolates_past_incumbent(self):
  p,f=perturb([0,1,0],[0,2,0],10)
  np.testing.assert_array_equal(p,[0,2,0]);self.assertEqual(f,1.)
 def test_changed_endpoints_or_invalid_budget_rejected(self):
  for b,budget in [([1,2,0],1),([0,2,0],0),([0,2,0],float('nan'))]:
   with self.assertRaises(ValueError):perturb([0,1,0],b,budget)
if __name__=='__main__':unittest.main()
