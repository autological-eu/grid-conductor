import unittest
import numpy as np

from audit_flow_adjusted_eligibility_2025 import net_import_intervals


class ImportIntervalTest(unittest.TestCase):
    def test_missing_corridor_expands_opposite_zone_balances(self):
        net=np.array([[.2,-.2],[.2,-.2]])
        flows=np.array([[np.nan],[.3]])
        lo,hi=net_import_intervals(net,flows,np.array([[0,1]]),
                                   np.array([[-1.],[-1.]]),np.array([[2.],[2.]]))
        np.testing.assert_allclose(lo[0],[-1.8,-1.2])
        np.testing.assert_allclose(hi[0],[1.2,1.8])
        np.testing.assert_allclose(lo[1],net[1])
        np.testing.assert_allclose(hi[1],net[1])


if __name__=='__main__':unittest.main()
