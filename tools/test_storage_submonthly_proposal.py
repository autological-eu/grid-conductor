import unittest
import numpy as np
from scipy import sparse
from submonthly_proposal import stabilise


class ProposalTests(unittest.TestCase):
    def test_stabilisation_preserves_closure_and_does_not_mutate_master_point(self):
        original=np.array([8.,8.]);anchor=np.array([2.,2.]);saved=original.copy()
        point=stabilise(original,anchor,.01,[(0.,10.)]*2,sparse.csr_matrix([[1.,-1.]]),np.zeros(1),
            sparse.csr_matrix([[1.,0.]]),np.array([10.]))
        np.testing.assert_array_equal(original,saved);np.testing.assert_allclose(point,[2.06,2.06])
        self.assertEqual(point[0]-point[1],0.)

    def test_invalid_weights_cannot_hide_restricted_master(self):
        for weight in [0.,-1.,1.1,float('nan')]:
            with self.assertRaises(ValueError):
                stabilise([1.],[0.],weight,[(0.,2.)],sparse.csr_matrix((0,1)),np.zeros(0),sparse.csr_matrix((0,1)),np.zeros(0))

    def test_necessary_feasibility_gate_remains(self):
        with self.assertRaises(ValueError):
            stabilise([2.],[0.],.5,[(0.,2.)],sparse.csr_matrix((0,1)),np.zeros(0),sparse.csr_matrix([[1.]]),np.array([.5]))


if __name__=='__main__':unittest.main()
