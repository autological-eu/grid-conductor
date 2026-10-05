import unittest
import numpy as np
from prepare_submonthly_blocks import partitions
from submonthly_inventory_mapping import project_state,lift_gradient
from prepare_submonthly_inventory_workspace import monthly_projection


class SubmonthlyWorkspaceProjectionTests(unittest.TestCase):
    def test_projection_and_cut_transpose_match_declared_layout(self):
        rows=partitions(2025,168);ns=3;P=monthly_projection(ns,rows)
        state=np.arange((len(rows)+1)*ns,dtype=float);gradient=np.arange(13*ns,dtype=float)-20.
        np.testing.assert_array_equal(P@state,project_state(state,ns,rows))
        np.testing.assert_array_equal(P.T@gradient,lift_gradient(gradient,ns,rows))
        self.assertEqual(float(gradient@(P@state)),float((P.T@gradient)@state))
        with self.assertRaises(ValueError):monthly_projection(0,rows)
