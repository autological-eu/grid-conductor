import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import Block
from sparse_primal_correction import correct_sparse
class SparseCorrection(unittest.TestCase):
 def test_corrects_interior_without_changing_bound_variable(self):
  b=Block(np.array([1.,1.]),[(0,2),(0,0)],sparse.csr_matrix([[1.,1.]]),np.array([1.]),sparse.csr_matrix([[0.]]))
  x,r=correct_sparse(b,np.array([0.]),np.array([1.+3e-7,0.]));self.assertTrue(r['original_unit_gate_passed']);self.assertEqual(x[1],0.);self.assertAlmostEqual(x[0],1.)
 def test_inequality_violation_is_rejected(self):
  b=Block(np.array([1.]),[(0,2)],sparse.csr_matrix([[1.]]),np.array([1.5]),sparse.csr_matrix([[0.]]),sparse.csr_matrix([[1.]]),np.array([1.]),sparse.csr_matrix([[0.]]))
  _,r=correct_sparse(b,np.array([0.]),np.array([.5]));self.assertFalse(r['original_unit_gate_passed'])
 def test_no_interior_fails(self):
  b=Block(np.array([1.]),[(0,0)],sparse.csr_matrix([[1.]]),np.array([1.]),sparse.csr_matrix([[0.]]))
  with self.assertRaises(ValueError):correct_sparse(b,np.array([0.]),np.array([0.]))
if __name__=='__main__':unittest.main()
