import unittest
import numpy as np
from scipy.sparse import csc_matrix
from hourly_offer_curves_2025 import compile_curves,offer_costs,shape_metrics,offset_direction,period_target,choose,FIT


class OfferCurveTest(unittest.TestCase):
    def fixture(self):
        # Parent 0 mixes zero-cost wind and run-of-river. Only wind may bid negative.
        base=dict(ng=2,nl=0,nz=1,zones=['A'],A=csc_matrix([[1.,1.,-1.],[0.,0.,1.]]),
                  availability=np.array([[100.,100.]]),cost=np.array([[0.,40.]]),offer_zones=np.array(['A','A']),emergency_mask=np.array([False,False]))
        ctx=dict(groups=[[0,1],[2]],availability=np.array([[60.,40.,100.]]),generation_keys=[('A','Wind'),None,('A','Gas')],country_keys=['A','A','A'])
        return base,ctx

    def test_mixed_renewable_parent_preserves_cap_and_leaves_ror_unchanged(self):
        base,ctx=self.fixture();m,c,l=compile_curves(base,ctx);cost=offer_costs(m,l,np.zeros((1,3)),[0,0,30])
        for parent in range(2):np.testing.assert_allclose(m['availability'][:,np.array(l['parent'])==parent].sum(axis=1),base['availability'][:,parent])
        self.assertEqual(sum(m['availability'][0,cost[0]<0]),30.)
        for j,k in enumerate(l['kinds']):
            if k=='other':self.assertEqual(cost[0,j],0)

    def test_thermal_upper_block_sets_known_clearing_price(self):
        from scipy.optimize import linprog
        base,ctx=self.fixture();m,c,l=compile_curves(base,ctx);cost=offer_costs(m,l,np.zeros((1,3)),[0,1,0])[0]
        result=linprog(np.r_[cost,0],A_eq=m['A'],b_eq=[190,0],bounds=[(0,a) for a in m['availability'][0]]+[(0,0)],method='highs')
        self.assertTrue(result.success);self.assertAlmostEqual(result.eqlin.marginals[0],160.)

    def test_daily_level_and_shape_are_distinguished(self):
        o=np.tile(np.arange(24.),3);r=shape_metrics(o+10,o)
        self.assertEqual(r['demeaned_mae'],0);self.assertAlmostEqual(r['within_day_error_mse_share'],0)
        q=shape_metrics(2*o-o.reshape(-1,24).mean(axis=1).repeat(24),o)
        self.assertAlmostEqual(q['within_day_error_mse_share'],1)

    def test_missing_days_not_imputed_and_material_negative_threshold(self):
        o=np.zeros(48);o[0]=np.nan;r=shape_metrics(np.zeros(48)-1e-8,o)
        self.assertEqual(r['complete_utc_days'],1);self.assertEqual(r['model_material_negative_hours'],0)

    def test_proposal_and_targets_exclude_later_period(self):
        base,ctx=self.fixture();m,c,l=compile_curves(base,ctx)
        with self.assertRaises(ValueError):offset_direction(m,l,np.zeros((FIT+24,m['ng'])),np.zeros((FIT+24,1)),np.zeros((FIT+24,1)))
        half=dict(prices=np.arange(4344)[:,None],generation=np.arange(6)[:,None],trade=np.arange(6)[:,None],months=np.arange(1,7))
        self.assertEqual(period_target(half,'fit')['prices'][-1,0],2879);self.assertEqual(period_target(half,'selection')['prices'][0,0],2880)

    def test_ties_and_failed_trials(self):
        rows=[dict(index=0,fit_score=1.,penalty=0.),dict(index=1,fit_score=1.,penalty=.1),dict(index=2,fit_score=None,penalty=0.)]
        self.assertEqual(choose(rows,'fit_score')['index'],0)

    def test_negative_discounts_do_not_exceed_declared_grid(self):
        b,c=self.fixture();m,_,l=compile_curves(b,c)
        with self.assertRaises(ValueError):offer_costs(m,l,np.zeros((1,3)),[0,0,31])


if __name__=='__main__':unittest.main()
