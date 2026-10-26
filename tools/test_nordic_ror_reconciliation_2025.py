import unittest
import numpy as np
from nordic_ror_reconciliation_2025 import river_profile
class Checks(unittest.TestCase):
 def test_partition_clipping_and_explicit_spill_conserve_water(self):
  a,s=river_profile([10.,40.],.5,[2.,3.]);np.testing.assert_allclose(a,[[2.,3.],[2.,3.]]);np.testing.assert_allclose(s,[[0.,0.],[6.,9.]])
 def test_not_generation_as_availability(self):
  a,s=river_profile([2.,0.],.5,[2.,3.]);np.testing.assert_allclose(a,[[.4,.6],[0.,0.]]);self.assertEqual(s.sum(),0)
if __name__=='__main__':unittest.main()
