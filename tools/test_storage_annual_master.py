import unittest
import numpy as np
from scipy import sparse
from annual_inventory_master import solve_cut_master

class AnnualMasterTests(unittest.TestCase):
 def test_cut_sign_and_original_units(self):
  r=solve_cut_master([(0.,5.)],sparse.csr_matrix((0,1)),np.array([]),sparse.csr_matrix((0,1)),np.array([]),[0.],[(0,[-1.],10.)])
  self.assertAlmostEqual(r['master_objective_eur'],5.)
  self.assertAlmostEqual(r['lower_bound_eur'],5.)
  self.assertAlmostEqual(r['proposal_mwh'][0],5.)
 def test_closure_and_reachability_are_preserved(self):
  r=solve_cut_master([(0.,5.),(0.,5.)],[[1.,-1.]],np.array([0.]),[[1.,0.]],np.array([3.]),[0.],[(0,[-1.,0.],10.)])
  self.assertAlmostEqual(r['master_objective_eur'],7.)
  self.assertAlmostEqual(r['proposal_mwh'][0],r['proposal_mwh'][1])
  self.assertLessEqual(r['lower_bound_eur'],7.+1e-7)
 def test_invalid_cut_rejected(self):
  with self.assertRaises(ValueError):solve_cut_master([(0.,5.)],[[1.]],np.array([0.]),[[1.]],np.array([3.]),[0.],[(1,[0.],10.)])

 def test_roundoff_infeasible_proposal_is_withheld(self):
  from unittest.mock import patch
  import annual_inventory_master as module
  original=module.solve_master
  def perturbed(*args,**kwargs):
   result=original(*args,**kwargs);result.x[0]+=1e-5
   return result
  with patch.object(module,'solve_master',side_effect=perturbed):
   r=solve_cut_master([(0.,5.)],sparse.csr_matrix((0,1)),np.array([]),sparse.csr_matrix((0,1)),np.array([]),[0.],[(0,[-1.],10.)])
  self.assertFalse(r['proposal_accepted']);self.assertIsNone(r['proposal_mwh'])
  self.assertGreater(r['max_bound_violation'],1e-7)

 def test_repair_does_not_change_unrestricted_bound(self):
  from unittest.mock import patch
  import annual_inventory_master as module
  original=module.solve_master
  def perturbed(*args,**kwargs):
   result=original(*args,**kwargs);result.x[0]+=4e-7
   return result
  with patch.object(module,'solve_master',side_effect=perturbed):
   r=solve_cut_master([(0.,5.)],sparse.csr_matrix((0,1)),np.array([]),[[1.]],np.array([3.]),[0.],[(0,[-1.],10.)],warm=np.array([1.]))
  self.assertTrue(r['proposal_accepted']);self.assertTrue(r['proposal_repaired'])
  self.assertLessEqual(r['proposal_mwh'][0],3.)
  self.assertAlmostEqual(r['lower_bound_eur'],7.)
  self.assertGreater(r['max_inequality_violation'],1e-7)
 def test_invalid_repair_anchor_rejected(self):
  from unittest.mock import patch
  import annual_inventory_master as module
  original=module.solve_master
  def perturbed(*args,**kwargs):
   result=original(*args,**kwargs);result.x[0]+=4e-7
   return result
  with patch.object(module,'solve_master',side_effect=perturbed):
   with self.assertRaises(ValueError):solve_cut_master([(0.,5.)],[[1.]],np.array([3.]),[[1.]],np.array([3.]),[0.],[(0,[-1.],10.)],warm=np.array([1.]))
