"""An Optimal label cannot bypass the unchanged numerical feasibility guard."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from scipy.sparse import csc_matrix
from run_regional_water_candidate_2025 import guarded_hour


class GuardTests(unittest.TestCase):
    def test_rejects_out_of_bounds_optimal(self):
        m=dict(ng=1,A=csc_matrix([[1.]]),availability=np.array([[1.]]),
               link_min=np.empty((1,0)),link_max=np.empty((1,0)),load=np.array([[0.]]),
               island_rhs=np.empty((1,0)),ratings=np.array([]))
        h=SimpleNamespace(getSolution=lambda:SimpleNamespace(col_value=[2.]))
        with patch('run_regional_water_candidate_2025.clear_hour',side_effect=ValueError('Zonal primal replay failed')):
            result,x=guarded_hour(h,m,0,np.array([]))
        self.assertIsNone(x)
        self.assertEqual(result['status'],'Optimal_rejected_primal_guard')
        self.assertEqual(result['maximum_residual_mw'],2.)

    def test_unrelated_error_still_stops_producer(self):
        with patch('run_regional_water_candidate_2025.clear_hour',side_effect=ValueError('bad source')):
            with self.assertRaisesRegex(ValueError,'bad source'):guarded_hour(None,None,0,None)


if __name__=='__main__':unittest.main()
