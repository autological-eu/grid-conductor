import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import Block
from submonthly_farkas_support import checked_support,native_ray


class FarkasSupportTests(unittest.TestCase):
    def test_native_ray_separates_impossible_stock_from_feasible_anchor(self):
        # x=s with physical x in [0,1]; s=2 cannot be reached. Economic cost
        # is arbitrary and must be removed before inferring feasibility.
        block=Block(np.array([100.]),[(0.,1.)],sparse.csr_matrix([[1.]]),np.array([0.]),
          sparse.csr_matrix([[-1.]]),sparse.csr_matrix((0,1)),np.zeros(0),sparse.csr_matrix((0,1)))
        state=np.array([2.]);anchor=np.array([.5]);ray,status=native_ray(block,state,seconds=5.)
        value,result,g,intercept,at_anchor,sign,norm=checked_support(block,state,anchor,ray)
        self.assertEqual(status,'Infeasible');self.assertAlmostEqual(value,1.)
        self.assertLessEqual(at_anchor,0.);self.assertGreater(float(g@state+intercept),0.)
        for feasible in np.linspace(0.,1.,11):self.assertLessEqual(float(g@np.array([feasible])+intercept),1e-12)
        with self.assertRaises(ValueError):checked_support(block,state,anchor,np.array([np.nan]))
