import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import solve_master
from storage_master_dual import master_dual
from grouped_master_dual import restore,support


class EqualityMasterDualTests(unittest.TestCase):
    def test_annual_closure_multiplier_restores_tight_analytic_bound(self):
        c=np.array([0.,0.,1.]);A=sparse.csr_matrix([[1.,-1.,-1.]]);b=np.array([-20.])
        E=sparse.csr_matrix([[1.,-1.,0.]]);d=np.array([0.]);bounds=[(0.,10.),(0.,10.),(0.,None)]
        solved=solve_master(c,A_eq=E,b_eq=d,A_ub=A,b_ub=b,bounds=bounds)
        self.assertAlmostEqual(solved.fun,20.)
        full,z,y=restore(c,A,b,E,d,bounds,solved,2)
        self.assertAlmostEqual(full['lower_bound_eur'],20.)
        self.assertLessEqual(master_dual(c,A,b,bounds,solved,2)['lower_bound_eur'],full['lower_bound_eur'])
        self.assertEqual(support(c,A,b,E,d,bounds,z,y,2),full)

    def test_positive_inequality_multiplier_and_unbounded_direction_rejected(self):
        c=[0.,1.];A=sparse.csr_matrix([[0.,-1.]]);E=sparse.csr_matrix((0,2));bounds=[(0.,10.),(0.,None)]
        for z in [[1.],[-2.]]:
            with self.assertRaises(ValueError):support(c,A,[0.],E,[],bounds,z,[],1)
