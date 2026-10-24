import unittest
import numpy as np
from forward_hourly_splines_2025 import month_hours, clock_slots, polynomials, project, interval_bids, CachedKnotCost
from supply_knot_splines_2025 import KnotCost, initial_parameters, spline
from run_forward_hourly_splines_2025 import aggregate


class ForwardTests(unittest.TestCase):
    def test_all_months_and_no_wrap(self):
        hours = [month_hours(m) for m in range(1,13)]
        np.testing.assert_array_equal(np.concatenate(hours),np.arange(8760))
        self.assertEqual(sum(map(len,hours[1:])),8016)
        with self.assertRaises(ValueError): month_hours(13)

    def test_dst_keeps_actual_hours(self):
        groups = [dict(zone='DE-LU')]
        hours = np.arange(8760)
        labels = clock_slots(groups,hours)[:,0]
        self.assertEqual(len(labels),8760)
        #2025-10-26 00/01UTC both local Sunday02:00; spring skips02:00.
        self.assertEqual(labels[7152],labels[7153])
        self.assertEqual((labels[2113]-labels[2112])%168,2)

    def test_exact_mean_functions_not_mean_parameters(self):
        rng = np.random.default_rng(17)
        theta = rng.normal(size=(8,3,6))
        zero = np.array([False,False,True])
        slots = np.zeros((8,3),dtype=int)
        av = np.ones((8,3))
        neutral = initial_parameters(3)[:,[0,5,6,7,8,9]]
        profile,support = project(theta,av,slots,zero,neutral)
        np.testing.assert_allclose(profile[0],polynomials(theta,zero).mean(axis=0),atol=1e-12)
        np.testing.assert_allclose(interval_bids(profile[0]),interval_bids(polynomials(theta,zero)).mean(axis=0),atol=1e-11)
        self.assertTrue((support[0]==8).all())
        self.assertEqual(float(abs(profile[:,2]).max()),0.)
        # Poisoning unavailable-hour parameters cannot affect the projection.
        av[0,0]=0
        first = project(theta,av,slots,zero,neutral)[0]
        theta[0,0]=100
        np.testing.assert_array_equal(first,project(theta,av,slots,zero,neutral)[0])

    def test_interval_cost_matches_original_integral(self):
        rng = np.random.default_rng(23)
        theta = rng.normal(size=(5,6))
        zero = np.array([0,1,0,0,0],dtype=bool)
        got = interval_bids(polynomials(theta[None],zero)[0])
        inc = .001+20*np.logaddexp(0,theta[:,1:])
        primitive = np.array([spline(np.full(5,u),inc)[1] for u in np.linspace(0,1,21)]).T
        wanted = 80*np.tanh(theta[:,0,None]/4)+np.diff(primitive,axis=1)*20
        wanted[zero]=0
        np.testing.assert_allclose(got,wanted,atol=2e-11)

    def test_cached_cost_same_objective_hessian_and_vjp(self):
        rng=np.random.default_rng(6)
        theta=initial_parameters(7)+rng.normal(size=(7,10))
        kw=dict(capacity=rng.uniform(.2,4,7),source=rng.uniform(0,80,7),parameter=np.arange(7),features=rng.normal(size=(7,5)),zero_bid=np.array([1,1,0,0,0,0,0],dtype=bool),theta=theta,extra_count=3)
        old,new=KnotCost(**kw),CachedKnotCost(**kw)
        for scale in [-.3,.2,.9,1.3]:
            x=np.r_[kw['capacity']*scale,rng.normal(size=3)]
            for a,b in zip(old.evaluate(x),new.evaluate(x)):
                np.testing.assert_allclose(a,b,rtol=1e-12,atol=1e-10)
            adj=rng.normal(size=10)
            np.testing.assert_array_equal(old.parameter_vjp(x,adj),new.parameter_vjp(x,adj))

    def test_forward_selection_weighting_and_december_exclusion(self):
        def row(h,p,g): return dict(hours=h,metrics=dict(price_mae=p,generation_mae_twh=g,generation_normalized_mae=g/2,generation_cells=3))
        records=[dict(month=1,within=row(744,1,2),forward=row(672,10,2)),dict(month=12,within=row(744,0,0))]
        self.assertEqual(aggregate(records,'forward')['price_mae'],10)
        self.assertEqual(aggregate(records,'forward')['hours'],672)
        self.assertEqual(aggregate(records,'within',True)['hours'],744)


if __name__=='__main__': unittest.main()
