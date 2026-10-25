import unittest
import numpy as np
from stock_anchored_hydro_2025 import schedule
class Checks(unittest.TestCase):
 def test_tracks_stock_without_creating_water(self):
  f=np.array([2.,2.,2.,2.]);target=np.array([10.,9.,8.,10.]);reference=np.array([1.,1.,3.,3.]);p,s,info=schedule(f,10,10,20,np.zeros(4),np.full(4,5.),np.zeros(4),target,reference)
  np.testing.assert_allclose(s,target,atol=1e-4);np.testing.assert_allclose(p.sum(),8,atol=1e-8)
  self.assertLess(info['water_residual_mwh'],1e-8)
 def test_incompatible_stock_does_not_relax_turbine_bounds(self):
  p,s,info=schedule(np.ones(4),4,4,8,np.zeros(4),np.ones(4),np.zeros(4),np.array([0.,0.,0.,4.]),np.ones(4))
  self.assertTrue((p<=1+1e-8).all());self.assertGreater(info['stock_max_discrepancy_mwh'],1)
 def test_impossible_water_budget_fails(self):
  with self.assertRaises(ValueError):schedule(np.ones(3),2,7,8,np.zeros(3),np.ones(3),np.zeros(3),np.ones(3),np.ones(3))
if __name__=='__main__':unittest.main()
