"""Balance and coverage checks for fixed-exchange supply clearing."""
import unittest
import numpy as np

from batched_transport_dispatch_2025 import TransportMarket
from flow_adjusted_zonal_clearing_2025 import clear_independent


class FlowAdjustedTest(unittest.TestCase):
    def test_import_reduces_required_local_generation(self):
        market=TransportMarket(['A'],[dict(zone_id=0,technology='gas')],
            np.empty((1,0)),np.empty((1,0)),[],np.ones((1,1)),
            np.zeros((1,1)),np.array([[.6]]))
        theta=np.zeros((1,6));hours=np.array([0]);covered=np.ones((1,1),bool)
        price,q,valid,residual=clear_independent(market,theta,np.array([[.2]]),covered,hours)
        self.assertTrue(valid[0,0]);self.assertAlmostEqual(q[0,0],.4,places=6)
        self.assertLess(abs(residual[0,0]),1e-6)
        self.assertTrue(np.isfinite(price[0,0]))

    def test_missing_flow_or_insufficient_capacity_is_not_cleared(self):
        market=TransportMarket(['A'],[dict(zone_id=0,technology='gas')],
            np.empty((1,0)),np.empty((1,0)),[],np.ones((1,1)),
            np.zeros((1,1)),np.array([[.6]]))
        theta=np.zeros((1,6));hours=np.array([0])
        _,_,valid,_=clear_independent(market,theta,np.zeros((1,1)),
                                       np.zeros((1,1),bool),hours)
        self.assertFalse(valid[0,0])
        _,_,valid,_=clear_independent(market,theta,np.array([[-.5]]),
                                       np.ones((1,1),bool),hours)
        self.assertFalse(valid[0,0])


if __name__=='__main__':unittest.main()
