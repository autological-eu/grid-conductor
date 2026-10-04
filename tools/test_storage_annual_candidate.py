import unittest
import numpy as np
from scipy import sparse
from prepare_annual_inventory_candidate import checked_candidate

class AnnualCandidateTests(unittest.TestCase):
 def test_original_bounds_closure_and_reachability(self):
  state=checked_candidate([2.,2.],[(0.,3.),(0.,3.)],sparse.csr_matrix([[1.,-1.]]),np.array([0.]),sparse.csr_matrix([[1.,0.]]),np.array([2.]))
  np.testing.assert_array_equal(state,[2.,2.])
 def test_reject_bad_closure_reachability_or_capacity(self):
  for state in ([2.,1.],[2.5,2.5],[4.,4.]):
   with self.assertRaises(ValueError):checked_candidate(state,[(0.,3.),(0.,3.)],sparse.csr_matrix([[1.,-1.]]),np.array([0.]),sparse.csr_matrix([[1.,0.]]),np.array([2.]))
