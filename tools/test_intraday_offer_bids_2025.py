import unittest
import numpy as np
from intraday_offer_bids_2025 import FIT,features,fit_proposal,shift,costs,demean


class IntradayBidsTest(unittest.TestCase):
    def inputs(self):
        daily=np.tile(np.sin(np.arange(24)*2*np.pi/24),365)
        m=dict(nz=1,zones=['ES'],load=(100+20*daily)[:,None],
               availability=np.full((8760,5),10.),offer_zones=['ES']*5)
        layout=dict(kinds=['renewable','gas','gas','nuclear','other'])
        return m,layout

    def test_daily_features_use_available_supply_and_training_scale(self):
        m,l=self.inputs();x,scale,residual=features(m,l)
        np.testing.assert_allclose(residual[:,0],m['load'][:,0]-10)
        np.testing.assert_allclose(x.reshape(365,24,1,5).mean(axis=1),0,atol=1e-14)
        changed=m|dict(load=m['load'].copy());changed['load'][4344:]*=100
        _,scale2,_=features(changed,l);np.testing.assert_array_equal(scale,scale2)

    def test_proposal_rejects_evaluation_prices(self):
        m,l=self.inputs();x,_,_=features(m,l)
        with self.assertRaises(ValueError):fit_proposal(x,np.zeros((8760,1)),np.zeros((8760,1)))

    def test_fit_recovers_shape_without_daily_price_level(self):
        m,l=self.inputs();x,_,_=features(m,l);prior=np.full((FIT,1),50.)
        observed=prior+20*x[:FIT,:,0]+100
        beta,counts=fit_proposal(x[:FIT],prior,observed)
        pred=shift(x,beta,[1.,1.])[:FIT]
        self.assertEqual(counts,[FIT]);self.assertGreater(np.corrcoef(pred[:,0],demean(observed)[:,0])[0,1],.99)

    def test_missing_days_and_unknown_zones_not_filled(self):
        m,l=self.inputs();x,_,_=features(m,l);obs=np.zeros((FIT,1));obs[0]=np.nan
        _,counts=fit_proposal(x[:FIT],np.zeros_like(obs),obs);self.assertEqual(counts,[FIT-24])
        b,c=fit_proposal(x[:FIT],np.zeros_like(obs),np.full_like(obs,np.nan));self.assertEqual(c,[0]);self.assertFalse(b.any())

    def test_bids_remain_monotone_and_physics_unchanged(self):
        m,l=self.inputs();original=m['availability'].copy();anchor=np.tile([0.,10.,31.,5.,2.],(8760,1))
        h=np.tile(np.linspace(-30,30,24),365)[:,None];out=costs(anchor,m,l,h)
        np.testing.assert_array_equal(m['availability'],original)
        np.testing.assert_array_equal(out[:,[0,4]],anchor[:,[0,4]])
        self.assertTrue((out[:,2]>=out[:,1]).all());self.assertTrue((out>=0).all())
        self.assertLessEqual(abs(out[:,3]-anchor[:,3]).max(),7.5)

    def test_hourly_bid_changes_reach_the_clearing_price(self):
        from scipy.optimize import linprog
        m,l=self.inputs();m['availability'][:]=0;m['availability'][:,1]=10
        anchor=np.tile([0.,10.,31.,5.,2.],(8760,1));hourly=np.zeros((8760,1));hourly[:24,0]=np.linspace(-5,5,24)
        offers=costs(anchor,m,l,hourly);prices=[]
        for t in range(24):
            r=linprog(offers[t],A_eq=np.ones((1,5)),b_eq=[5],bounds=[(0,v) for v in m['availability'][t]],method='highs')
            self.assertTrue(r.success);prices.append(r.eqlin.marginals[0])
        np.testing.assert_allclose(prices,10+hourly[:24,0]);self.assertGreater(prices[-1],prices[0])


if __name__=='__main__':unittest.main()
