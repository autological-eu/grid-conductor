import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import Block,solve_block
from condition_storage_block import condition_rows
class Conditioning(unittest.TestCase):
 def test_cost_and_boundary_gradient_preserved(self):
  block=Block(np.array([3.]),[(0,None)],sparse.csr_matrix([[1000.]]),np.array([2000.]),sparse.csr_matrix([[1000.]]))
  a,g=solve_block(block,np.array([.5]));b,h=solve_block(condition_rows(block),np.array([.5]))
  self.assertAlmostEqual(a.fun,b.fun);self.assertAlmostEqual(g[0],h[0]);self.assertAlmostEqual(h[0],-3.)
 def test_positive_inequality_scaling_preserves_feasibility(self):
  block=Block(np.array([-1.]),[(0,10)],sparse.csr_matrix((0,1)),np.array([]),sparse.csr_matrix((0,1)),sparse.csr_matrix([[200.]]),np.array([800.]),sparse.csr_matrix([[200.]]))
  a,g=solve_block(block,np.array([1.]));b,h=solve_block(condition_rows(block),np.array([1.]))
  self.assertAlmostEqual(a.x[0],3.);self.assertAlmostEqual(a.fun,b.fun);self.assertAlmostEqual(g[0],h[0])
if __name__=='__main__':unittest.main()
