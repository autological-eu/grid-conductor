import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import Block
from refine_rejected_primal import correct
class Refinement(unittest.TestCase):
 def block(self):return Block(np.array([3.]),[(0,2)],sparse.csr_matrix([[1.]]),np.array([1.]),sparse.csr_matrix([[1.]]))
 def test_repairs_small_error_in_original_units(self):
  x,r=correct(self.block(),np.array([0.]),np.array([1.+3e-7]));self.assertTrue(r['original_unit_gate_passed']);self.assertAlmostEqual(x[0],1.);self.assertAlmostEqual(r['cost_change_eur'],-9e-7)
 def test_box_does_not_hide_infeasibility(self):
  with self.assertRaises(RuntimeError):correct(self.block(),np.array([0.]),np.array([1.1]))
 def test_invalid_radius(self):
  with self.assertRaises(ValueError):correct(self.block(),np.array([0.]),np.array([1.]),radius=0)
if __name__=='__main__':unittest.main()
