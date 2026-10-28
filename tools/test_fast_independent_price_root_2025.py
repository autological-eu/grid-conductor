"""Numerical equivalence and implicit-gradient checks for the compiled root."""
import unittest
import numpy as np

from batched_transport_dispatch_2025 import TransportMarket
from fast_independent_price_root_2025 import solve,njit


@unittest.skipIf(njit is None,'numba unavailable')
class FastRootTest(unittest.TestCase):
    def test_root_and_implicit_price_gradient(self):
        market=TransportMarket(['A'],[dict(zone_id=0,technology='gas')],
            np.empty((1,0)),np.empty((1,0)),[],np.ones((1,1)),
            np.array([[65.]]),np.array([[.43]]))
        theta=np.zeros((1,6));hours=np.array([0]);target=np.array([[.43]])
        def root(weights):
            offers=market.offers(weights,hours)
            p,q,valid,residual=solve(market,offers,target,np.ones((1,1),bool))
            self.assertTrue(valid[0,0]);self.assertLess(abs(residual[0,0]),1e-7)
            return p[0,0],offers
        price,offers=root(theta)
        p=np.array([[price]])
        _,dq,raw=market.supply(p,offers,parameters=True)
        implicit=-raw[0,0,2]/dq[0,0]
        eps=1e-4
        plus=theta.copy();minus=theta.copy();plus[0,2]+=eps;minus[0,2]-=eps
        finite=(root(plus)[0]-root(minus)[0])/(2*eps)
        self.assertAlmostEqual(implicit,finite,delta=1e-4)


if __name__=='__main__':unittest.main()
