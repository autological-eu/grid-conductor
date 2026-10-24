import unittest
import numpy as np
from monthly_diurnal_splines_2025 import labels,expand,aggregate,penalties


class MonthlyTests(unittest.TestCase):
    def test_compiled_dispatch_true_quadratic_and_cubic_optima(self):
        from scipy.sparse import csc_matrix
        from scipy.optimize import brentq
        from clarabel_spline_dispatch_2025 import solve,passed
        class Cost:
            capacity=np.array([3.]);extra_count=1;ng=1
            def __init__(self,cubic):self.cubic=cubic
            def evaluate(self,x):
                q,y=x
                if self.cubic:return q**4/4+q*q/2+y*y/2,np.array([q**3+q,y]),np.array([3*q*q+1,1.])
                return q*q+y*y/2,np.array([2*q,y]),np.array([2.,1.])
        p=dict(E=csc_matrix([[1.,1.]]),b=np.array([2.]),G=csc_matrix([[1.,0.],[-1.,0.],[0.,1.],[0.,-1.]]),h=np.array([3.,0.,3.,0.]),x0=None)
        for cubic in [False,True]:
            r=solve(Cost(cubic),p)
            expected=brentq(lambda q:q**3+2*q-2,0,2) if cubic else 2/3
            np.testing.assert_allclose(r['x'],[expected,2-expected],atol=1e-6)
            self.assertTrue(passed(r['certificate']))

    def test_shared_local_clock_across_days_and_dst(self):
        groups=[dict(zone='DE-LU'),dict(zone='GB')]
        clock=labels(groups,np.array([0,24,48]))
        np.testing.assert_array_equal(clock,np.tile([1,0],(3,1)))
        theta=np.arange(24*2*6).reshape(24,2,6)
        hourly=expand(theta,clock)
        np.testing.assert_array_equal(hourly[0],hourly[2])
        autumn=labels(groups,np.array([7152,7153]))
        self.assertEqual(autumn[0,0],autumn[1,0])

    def test_shared_gradient_chain_rule(self):
        rng=np.random.default_rng(181)
        theta=rng.normal(size=(24,3,6))
        clock=rng.integers(0,24,size=(100,3))
        grad=rng.normal(size=(100,3,6))
        direction=rng.normal(size=theta.shape)
        actual=float((aggregate(grad,clock)*direction).sum())
        wanted=float((grad*expand(direction,clock)).sum())
        self.assertAlmostEqual(actual,wanted,delta=1e-10)

    def test_cyclic_penalty_gradient_and_inactive_freeze(self):
        rng=np.random.default_rng(813)
        theta=rng.normal(size=(24,3,6));initial=np.zeros_like(theta)
        active=rng.random((24,3))>.2
        d=dict(hourly_shrinkage=.01,temporal_penalty=.01)
        value,g,_=penalties(theta,initial,active,d)
        direction=rng.normal(size=theta.shape);eps=1e-5
        finite=(penalties(theta+eps*direction,initial,active,d)[0]-penalties(theta-eps*direction,initial,active,d)[0])/(2*eps)
        self.assertAlmostEqual(finite,float((g*direction).sum()),delta=1e-10)
        self.assertEqual(float(abs(g[~active]).max()),0.)


if __name__=='__main__':unittest.main()
