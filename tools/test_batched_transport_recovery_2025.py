import unittest
import numpy as np
from batched_transport_newton_recovery_2025 import RecoveredTransportMarket


class RecoveryTests(unittest.TestCase):
    def test_leaves_flat_saturated_region_without_changing_bounds(self):
        groups=[dict(zone_id=0,technology='gas'),dict(zone_id=1,technology='coal')]
        m=RecoveredTransportMarket(['A','B'],groups,np.full((3,1),-3.),np.full((3,1),3.),[(0,1)],
            np.tile([10.,12.],(3,1)),np.tile([20.,40.],(3,1)),np.array([[6.,8.],[7.,8.],[5.,9.]]))
        theta=np.zeros((2,6));theta[:,1:]=np.log(np.expm1((9.6-.001)/20))
        ordinary=m.solve(theta,np.arange(3))
        recovered=m.solve(theta,np.arange(3),p0=np.full((3,2),500.))
        self.assertGreater(recovered['coordinate_recoveries'],0)
        self.assertLess(recovered['certificate']['balance_mw'],1e-4)
        np.testing.assert_allclose(ordinary['prices'],recovered['prices'],atol=1e-6)
        np.testing.assert_array_equal(recovered['hours'],np.arange(3))


if __name__=='__main__':unittest.main()
