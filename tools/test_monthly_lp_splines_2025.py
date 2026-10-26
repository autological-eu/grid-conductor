import unittest
import numpy as np

from clear_monthly_lp_splines_2025 import sampled_costs,BINS
from conditional_monotone_market_2025 import basis


class MonthlyLpSplineTests(unittest.TestCase):
    def test_interval_bids_are_ordered_and_preserve_zero_renewables(self):
        theta=np.zeros((2,2,10));theta[:,:,1:]=1
        cost=sampled_costs(theta,np.array([[30.,10.],[50.,20.]]),
            np.array([[1.,.4],[1.,.2]]),np.array([1.,1.]),np.array([False,True]))
        self.assertEqual(cost.shape,(2,2,BINS))
        self.assertTrue((np.diff(cost[:,0],axis=1)>=-1e-10).all())
        np.testing.assert_array_equal(cost[:,1],0)
        self.assertAlmostEqual(cost[0,0,0]-cost[1,0,0],-20,places=4)

    def test_full_availability_segment_average_matches_polynomial_integral(self):
        theta=np.zeros((1,1,10));theta[...,1:]=np.arange(9)
        sampled=sampled_costs(theta,np.array([[35.]]),np.array([[2.]]),
                              np.array([2.]),np.array([False]))[0,0]
        slopes=.05+20*np.logaddexp(0,theta[0,0,1:])
        for k in range(BINS):
            u=np.linspace(k/BINS,(k+1)/BINS,1001)
            exact=np.trapezoid(35+basis(u)@slopes,u)/(1/BINS)
            self.assertAlmostEqual(sampled[k],exact,places=5)


if __name__=='__main__':unittest.main()
