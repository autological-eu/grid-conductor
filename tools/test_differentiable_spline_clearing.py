import unittest
import numpy as np
from scipy.sparse import csc_matrix
from differentiable_spline_clearing import BASIS,BidCost,initial_parameters,solve,adjoint


def toy(theta, demand=1.4, limit=.3):
    # Two zones: cheap supply at zone0 exports through a constrained line.
    cost=BidCost(np.array([2.,2.]),np.array([30.,90.]),np.array([0,1]),np.array([[1.,0,0,0,0]]*2),np.array([False,False]),theta,1)
    E=csc_matrix([[1.,0.,-1.],[0.,1.,1.]])
    G=csc_matrix(np.r_[-np.eye(3)[:2],np.eye(3)[:2],[[0,0,1.],[0,0,-1.]]])
    h=np.array([0,0,2.,2.,limit,limit]);b=np.array([.5,demand])
    return cost,E,b,G,h


class SplineTests(unittest.TestCase):
    def test_monotonicity_and_integrals(self):
        u=np.linspace(0,1,501);I,J,M=BASIS.evaluate(u)
        self.assertTrue((np.diff(I,axis=0)>=-1e-12).all())
        np.testing.assert_allclose(I@BASIS.linear_weights,48*(u-.5),atol=1e-11)
        eps=1e-6
        ip,jp,_=BASIS.evaluate(u+eps);im,jm,_=BASIS.evaluate(u-eps)
        np.testing.assert_allclose((jp-jm)/(2*eps),I,atol=1e-8)
        np.testing.assert_allclose((ip-im)/(2*eps),M,atol=5e-5)

    def test_congested_dispatch_and_prices(self):
        theta=initial_parameters(2);cost,E,b,G,h=toy(theta)
        r=solve(cost,E,b,G,h)
        np.testing.assert_allclose(E@r['x'],b,atol=2e-8)
        self.assertAlmostEqual(r['x'][2],.3,places=6)
        price=-r['nu'];self.assertGreater(price[1],price[0]+20)

    def test_price_and_generation_gradient_finite_difference(self):
        theta=initial_parameters(2);cost,E,b,G,h=toy(theta);r=solve(cost,E,b,G,h,gap_tolerance=1e-8)
        gx=np.array([.3,-.2,.1]);gp=np.array([.4,-.7])
        gradient=adjoint(cost,E,G,r,gx,gp)
        for index in [(0,0),(1,0),(0,5),(1,7),(1,10)]:
            eps=1e-4;plus=theta.copy();minus=theta.copy();plus[index]+=eps;minus[index]-=eps
            def objective(v):
                c,e,bb,g,hh=toy(v);rr=solve(c,e,bb,g,hh,gap_tolerance=1e-8)
                return float(gx@rr['x']-gp@rr['nu'])
            finite=(objective(plus)-objective(minus))/(2*eps)
            self.assertAlmostEqual(gradient[index],finite,delta=max(2e-4,abs(finite)*2e-4))

    def test_zero_bid_has_no_learned_gradient(self):
        theta=initial_parameters(1);c=BidCost(np.array([1.]),np.zeros(1),np.array([0]),np.array([[1.,0,0,0,0]]),np.array([True]),theta,0)
        _,g,H=c.evaluate(np.array([.4]));self.assertAlmostEqual(g[0],.004)
        np.testing.assert_array_equal(c.parameter_vjp(np.array([.4]),np.ones(1)),np.zeros_like(theta))


if __name__=='__main__':unittest.main()
