"""Weekly bids preserve unrelated resources and respect local calendar/support."""
import unittest
import numpy as np
import pandas as pd
from weekly_supply_bids_2025 import weekly,offers,fit


class WeeklyBidsTest(unittest.TestCase):
    def test_local_midnight_and_zero_mean(self):
        w,weekend=weekly(['DE-LU','GB'])
        # Friday 23:00 UTC is Saturday Berlin but still Friday London in January.
        t=int((pd.Timestamp('2025-01-03T23:00Z')-pd.Timestamp('2025-01-01T00:00Z')).total_seconds()/3600)
        self.assertTrue(weekend[t,0]);self.assertFalse(weekend[t,1])
        np.testing.assert_allclose(w.mean(axis=0),0,atol=1e-13)

    def test_resources_and_monotone_blocks(self):
        m=dict(zones=['DE-LU'],offer_zones=np.array(['DE-LU']*5))
        layout=dict(kinds=['gas','gas','nuclear','renewable','other'])
        c=np.tile([50.,75.,5.,-10.,40.],(8760,1));coef=np.array([[-30.,0.,-7.5]])
        out=offers(m,layout,c,coef)
        np.testing.assert_array_equal(c[:,3:],out[:,3:]);np.testing.assert_array_equal(c,np.tile([50.,75.,5.,-10.,40.],(8760,1)))
        np.testing.assert_allclose(out[:,1]-out[:,0],25.)
        self.assertTrue((out[:,:3]>=0).all())

    def test_no_local_interior_means_no_calibration(self):
        m=dict(zones=['DE-LU'],nz=1,ng=1,offer_zones=np.array(['DE-LU']),availability=np.ones((8760,1)))
        layout=dict(kinds=['gas']);c=np.full((8760,1),80.);x=np.ones_like(c);prices=c.copy();observed=c+30
        design=dict(resources=['gas','coal','nuclear'],minimum_interior_hours=168,minimum_daytype_hours=24,ridge=168,coefficient_bounds_eur_mwh=[30,30,7.5])
        coef,support=fit(m,layout,c,x,prices,observed,np.zeros((8760,1,15)),design)
        self.assertFalse(coef.any());self.assertTrue(all(s['interior_hours']==0 for s in support))


if __name__=='__main__':unittest.main()
