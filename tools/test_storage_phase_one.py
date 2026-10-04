import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import Block,solve_block
from annual_inventory_phase_one import elastic_block,feasibility_support

class PhaseOneTests(unittest.TestCase):
 def test_cut_excludes_infeasible_state_and_keeps_feasible_anchor(self):
  b=Block(np.array([0.]),[(0.,0.)],sparse.csr_matrix([[1.]]),np.array([2.]),sparse.csr_matrix([[1.]]))
  elastic=elastic_block(b);state=np.array([0.]);result,_=solve_block(elastic,state)
  cut=feasibility_support(elastic,state,result,np.array([2.]))
  self.assertAlmostEqual(cut['dual_support'],2.)
  self.assertGreater(np.dot(cut['gradient'],state),cut['feasibility_limit'])
  self.assertLessEqual(np.dot(cut['gradient'],[2.]),cut['feasibility_limit'])
 def test_zero_infeasibility_is_not_a_cut(self):
  b=Block(np.array([0.]),[(0.,0.)],sparse.csr_matrix([[1.]]),np.array([2.]),sparse.csr_matrix([[1.]]))
  elastic=elastic_block(b);state=np.array([2.]);result,_=solve_block(elastic,state)
  with self.assertRaises(ValueError):feasibility_support(elastic,state,result,state)
