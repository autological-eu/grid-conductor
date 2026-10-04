import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import Block,solve_block
from annual_inventory_phase_one import elastic_block,feasibility_support,anchor_candidate

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

 def test_boundary_only_keeps_independent_equalities_hard(self):
  b=Block(np.array([0.]),[(0.,10.)],sparse.csr_matrix([[1.],[1.]]),np.array([3.,5.]),sparse.csr_matrix([[0.],[1.]]))
  elastic=elastic_block(b,boundary_only=True)
  self.assertEqual(len(elastic.cost),3)
  self.assertEqual(elastic.equality[0,1:].nnz,0)
  result,_=solve_block(elastic,np.array([0.]))
  cut=feasibility_support(elastic,np.array([0.]),result,np.array([2.]))
  self.assertAlmostEqual(result.x[0],3.);self.assertAlmostEqual(cut['dual_support'],2.)
  zero,_=solve_block(elastic,np.array([2.]));self.assertAlmostEqual(zero.fun,0.)
 def test_boundary_inequality_orientation(self):
  b=Block(np.array([0.]),[(0.,10.)],sparse.csr_matrix([[1.]]),np.array([3.]),sparse.csr_matrix([[0.]]),sparse.csr_matrix([[1.]]),np.array([1.]),sparse.csr_matrix([[-1.]]))
  elastic=elastic_block(b,boundary_only=True)
  self.assertEqual(len(elastic.cost),2)
  result,_=solve_block(elastic,np.array([0.]))
  cut=feasibility_support(elastic,np.array([0.]),result,np.array([2.]))
  self.assertAlmostEqual(cut['dual_support'],2.)
  self.assertAlmostEqual(cut['gradient'][0],-1.)
  zero,_=solve_block(elastic,np.array([2.]));self.assertAlmostEqual(zero.fun,0.)

 def test_verified_primal_constructs_feasible_elastic_point(self):
  b=Block(np.array([0.]),[(0.,10.)],sparse.csr_matrix([[1.],[1.]]),np.array([3.,5.]),sparse.csr_matrix([[0.],[1.]]),sparse.csr_matrix([[1.]]),np.array([1.]),sparse.csr_matrix([[-1.]]))
  state=np.array([0.])
  for mode in [False,True]:
   elastic=elastic_block(b,boundary_only=mode);point=anchor_candidate(b,state,np.array([3.]),boundary_only=mode)
   np.testing.assert_allclose(elastic.equality@point+elastic.coupling@state,elastic.rhs)
   self.assertLessEqual(float(np.max(elastic.inequality@point+elastic.inequality_coupling@state-elastic.limit)),0.)
