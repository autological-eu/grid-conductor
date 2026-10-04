import unittest
import numpy as np
from scipy import sparse
from annual_inventory_master import solve_cut_master
from build_annual_multicut_master import matching_domain

class MultiCutTests(unittest.TestCase):
 def test_new_cut_tightens_lower_bound_without_resetting_previous_cut(self):
  args=([(0.,5.)],sparse.csr_matrix((0,1)),np.array([]),sparse.csr_matrix((0,1)),np.array([]),[0.])
  first=solve_cut_master(*args,[(0,[-1.],10.)])
  both=solve_cut_master(*args,[(0,[-1.],10.),(0,[1.],5.)])
  self.assertAlmostEqual(first['lower_bound_eur'],5.)
  self.assertAlmostEqual(both['lower_bound_eur'],7.5)
 def test_different_domain_rejected(self):
  a=dict(bounds=np.array([[0.,5.]]),rhs=np.array([0.]),limit=np.array([3.]))
  matching_domain(a,a)
  for name in a:
   b={k:v.copy() for k,v in a.items()};b[name]+=1.
   with self.assertRaises(ValueError):matching_domain(a,b)
