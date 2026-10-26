import unittest
import numpy as np
from norway_demand_allocation_2025 import allocate
class Checks(unittest.TestCase):
 def test_additive_does_not_discard_residual_or_change_national_total(self):
  value,meta=allocate([[6.,4.]],[[3.,5.]],'metered_plus_original_residual');np.testing.assert_allclose(value,[[4.2,5.8]]);self.assertEqual(meta['minimum_nonmetered_residual_mw'],2)
 def test_negative_residual_is_rejected_not_hidden(self):
  with self.assertRaises(ValueError):allocate([[1.,1.]],[[2.,2.]],'metered_plus_original_residual')
 def test_proportional_is_an_explicit_scope_control(self):
  value,_=allocate([[6.,4.]],[[2.,6.]],'metered_proportional_scope_control');np.testing.assert_allclose(value,[[2.5,7.5]])
if __name__=='__main__':unittest.main()
