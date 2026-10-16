import unittest
import numpy as np
from generation_mix_2025 import MONTH
from seasonal_calendar_bids_2025 import calendar,fold_months,interior,proposals,bids


class SeasonalBidsTest(unittest.TestCase):
    def fixture(self):
        x,s=calendar(['ES']);p=np.zeros((8760,1));target=dict(generation=np.ones((12,1,5)))
        mon=[dict(generation_lower_twh=np.ones((1,5)),generation_upper_twh=np.ones((1,5))) for _ in range(12)]
        return x,s,p,mon,target

    def test_folds_cover_every_month_once_with_disjoint_roles(self):
        tests=[]
        for i in range(3):
            f=fold_months(i);tests+=f['test'];self.assertEqual(set(sum(f.values(),[])),set(range(1,13)))
            self.assertEqual(sum(map(len,f.values())),12)
            for role in ['fit','selection']:
                for month in f[role]:
                    ids=np.flatnonzero(MONTH==month);self.assertFalse(interior(f[role])[ids[:48]].any());self.assertFalse(interior(f[role])[ids[-48:]].any())
        self.assertEqual(sorted(tests),list(range(1,13)))

    def test_calendar_is_seasonal_and_dst_aware_without_load_predictor(self):
        x,s=calendar(['ES']);self.assertEqual(x.shape,(8760,1,15));self.assertFalse(np.allclose(x[12,0,7:],x[24*180+12,0,7:]))
        # Daily harmonic follows local clock: winter UTC noon is 13h, summer 14h.
        self.assertAlmostEqual(x[12,0,3],np.sin(2*np.pi*13/24));self.assertAlmostEqual(x[24*180+12,0,3],np.sin(2*np.pi*14/24))

    def test_test_month_targets_cannot_change_fitted_coefficients(self):
        x,s,p,mon,t=self.fixture();months=fold_months(0)['fit'];o=np.sin(np.arange(8760)/24)[:,None]
        a=proposals(x,s,p,o,mon,t,months);o2=o.copy();o2[~np.isin(MONTH,months)]=1e6
        t2=dict(generation=t['generation'].copy());t2['generation'][np.array(fold_months(0)['test'])-1]=1e6
        b=proposals(x,s,p,o2,mon,t2,months)
        for v,w in zip(a,b):np.testing.assert_array_equal(v,w)

    def test_ember_is_not_hourly_availability_and_only_known_training_months_fit(self):
        x,s,p,mon,t=self.fixture();t['generation'][:]=np.nan
        a=proposals(x,s,p,p,mon,t,[1,4,7,10]);self.assertFalse(a[1].any());self.assertFalse(a[3].any())
        t['generation'][0,0,3]=2.;b=proposals(x,s,p,p,mon,t,[1,4,7,10]);self.assertLess(b[1][0,0,0],0);self.assertEqual(b[3][0,0],1)

    def test_bids_respect_resource_caps_and_ignore_demand(self):
        x,s,p,mon,t=self.fixture();m=dict(cost=np.tile([40.,80.,10.,0.],(8760,1)),zones=['ES'],offer_zones=['ES']*4,load=np.zeros((8760,1)))
        layout=dict(kinds=['gas','coal','nuclear','renewable']);beta=np.ones((1,15))*100;gamma=np.ones((1,3,3))*100;shares=np.ones((4,1))
        c=bids(m,layout,x,s,beta,gamma,shares,2);m['load'][:]=1e9
        np.testing.assert_array_equal(c,bids(m,layout,x,s,beta,gamma,shares,2))
        self.assertTrue((abs(c[:,:2]-m['cost'][:,:2])<=30+1e-9).all());self.assertLessEqual(abs(c[:,2]-10).max(),7.5)
        np.testing.assert_array_equal(c[:,3],0)


if __name__=='__main__':unittest.main()
