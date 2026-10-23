import unittest
import numpy as np
from scipy.interpolate import PchipInterpolator
from supply_knot_splines_2025 import KNOTS,spline,KnotCost,initial_parameters
from differentiable_spline_clearing import solve,adjoint
from test_differentiable_spline_clearing import toy


class KnotTests(unittest.TestCase):
    def test_six_nodes_and_variable_curvature(self):
        inc=np.array([[2.,20.,1.,35.,4.]]);u=np.linspace(0,1,501)
        p,j,m=spline(u,np.repeat(inc,len(u),axis=0));native=PchipInterpolator(KNOTS,np.r_[0,np.cumsum(inc)])
        np.testing.assert_allclose(p,native(u)-native(.5),atol=1e-12)
        np.testing.assert_allclose(j,native.antiderivative()(u)-u*native(.5),atol=1e-12)
        self.assertTrue((m>=-1e-9).all());self.assertGreater(np.ptp(m),100)
        at,_,_=spline(KNOTS,np.repeat(inc,6,axis=0));np.testing.assert_allclose(np.diff(at),inc[0])

    def test_exact_lp_interval_averages(self):
        theta=initial_parameters(1);theta[0,5:]=[-3,1,-2,2,-1]
        c=KnotCost(np.ones(1),np.array([40.]),np.array([0]),np.array([[1,0,0,0,0]]),np.zeros(1,bool),theta,0)
        bids=c.interval_bids(20)[0];self.assertTrue((np.diff(bids)>=-1e-10).all())
        integral=c.evaluate(np.array([1.]))[0]-c.evaluate(np.array([0.]))[0]
        self.assertAlmostEqual(bids.mean(),integral-.005,places=10)

    def test_joint_price_dispatch_adjoint(self):
        theta=initial_parameters(2);old,E,b,G,h=toy(theta)
        def cost(v):return KnotCost(old.capacity,old.source,old.parameter,old.features,old.zero_bid,v,1)
        c=cost(theta);r=solve(c,E,b,G,h,gap_tolerance=1e-8);gx=np.array([.3,-.2,.1]);gp=np.array([.4,-.7])
        grad=adjoint(c,E,G,r,gx,gp)
        for index in [(0,0),(1,0),(0,5),(1,7),(1,9)]:
            eps=1e-4;plus=theta.copy();minus=theta.copy();plus[index]+=eps;minus[index]-=eps
            def objective(v):
                rr=solve(cost(v),E,b,G,h,gap_tolerance=1e-8);return float(gx@rr['x']-gp@rr['nu'])
            finite=(objective(plus)-objective(minus))/(2*eps)
            self.assertAlmostEqual(grad[index],finite,delta=max(2e-4,abs(finite)*2e-4))

    def test_zero_economic_bids_exact_in_lp(self):
        theta=initial_parameters(1);c=KnotCost(np.ones(1),np.zeros(1),np.array([0]),np.array([[1,0,0,0,0]]),np.ones(1,bool),theta,0)
        np.testing.assert_array_equal(c.interval_bids(20),np.zeros((1,20)))
        np.testing.assert_array_equal(c.parameter_vjp(np.array([.5]),np.ones(1)),np.zeros_like(theta))


if __name__=='__main__':unittest.main()
