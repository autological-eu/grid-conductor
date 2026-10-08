import unittest
import numpy as np
from audit_retained_inventory_2025 import check_boundaries

class BoundaryTests(unittest.TestCase):
    def test_nonempty_cyclic_state_and_roundoff_preserved(self):
        state=np.array([[4., 0.], [2., -1e-14], [4., 0.]])
        result=check_boundaries(state,np.array([5.,0.]),np.array([True,True]))
        self.assertEqual(result['cyclic_closure_residual_mwh'],0.)
        self.assertEqual(state[0,0],4.)
    def test_broken_closure_capacity_and_missing_state_rejected(self):
        for state in [np.array([[4.],[3.]]),np.array([[6.],[6.]]),np.array([[-1.],[-1.]]),np.array([[np.nan],[np.nan]])]:
            with self.subTest(state=state),self.assertRaises(ValueError):
                check_boundaries(state,np.array([5.]),np.array([True]))

if __name__=='__main__':unittest.main()
