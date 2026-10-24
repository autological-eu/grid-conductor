import unittest
import numpy as np
from batched_transport_dispatch_2025 import TransportMarket,softclip


def market():
    groups=[dict(zone_id=0,technology='gas'),dict(zone_id=1,technology='coal')]
    return TransportMarket(['A','B'],groups,np.full((3,1),-3.),np.full((3,1),3.),[(0,1)],np.tile([10.,12.],(3,1)),np.tile([20.,40.],(3,1)),np.array([[6.,8.],[7.,8.],[5.,9.]]))


class TransportTests(unittest.TestCase):
    def test_softclip_bounds_and_extreme_stability(self):
        x=np.linspace(-1e4,1e4,1000);q=softclip(x,.01,.001)
        self.assertGreaterEqual(q.min(),0)
        self.assertLessEqual(q.max(),.01)
        self.assertEqual(float(softclip(1e4,0,.0001)),0.)

    def test_exact_price_generation_gradient_and_every_hour(self):
        m=market();theta=np.zeros((3,2,6));theta[:,:,1:]=np.log(np.expm1((9.6-.001)/20))
        hours=np.arange(3);r=m.solve(theta,hours)
        np.testing.assert_array_equal(r['hours'],hours)
        self.assertLess(r['certificate']['balance_mw'],1e-4)
        gq=np.array([[.2,-.1],[.4,.1],[-.2,.3]]);gp=np.array([[.02,-.04],[.01,.05],[.03,.01]])
        gradient,info=m.backward(theta,r,gq,gp)
        self.assertEqual(info['unidentified_directions'],0)
        rng=np.random.default_rng(319);direction=rng.normal(size=theta.shape);eps=1e-4
        def loss(state):
            result=m.solve(state,hours,p0=r['prices'])
            return float((result['prices']*gp).sum()+(result['quantities_gw']*gq).sum())
        finite=(loss(theta+eps*direction)-loss(theta-eps*direction))/(2*eps)
        self.assertAlmostEqual(finite,float((gradient*direction).sum()),delta=1e-5)

    def test_residual_jacobian_and_flow_sign(self):
        m=market();theta=np.zeros((2,6));theta[:,1:]=-.5
        hours=np.arange(3);r=m.solve(theta,hours);offers=m.offers(theta,hours)
        residual,J,_,flow=m.evaluate(r['prices'],offers,jacobian=True)
        perturb=np.zeros_like(r['prices']);perturb[:,0]=1e-4
        finite=(m.evaluate(r['prices']+perturb,offers)[0]-m.evaluate(r['prices']-perturb,offers)[0])/2e-4
        np.testing.assert_allclose(finite,J[:,:,0],atol=1e-6,rtol=1e-5)
        self.assertTrue((flow[:,0]>0).all())
        self.assertTrue((r['prices'][:,1]>r['prices'][:,0]).all())


if __name__=='__main__':unittest.main()
