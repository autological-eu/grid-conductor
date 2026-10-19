"""Resource bounds, supported proposals, unchanged physics and ensemble filters."""
import copy,json,unittest
import numpy as np
from inverse_bid_ensemble_2025 import PLAN,zero,advance,costs,proposal,record_score,ensemble


class InverseTests(unittest.TestCase):
    def setUp(self):self.d=json.loads(PLAN.read_text())
    def test_zero_identity_monotone_curve_and_caps(self):
        m=dict(zones=['FR'],offer_zones=['FR']*4);layout=dict(kinds=['gas']*3+['nuclear'],ranks=[0,1,2,0]);a=np.full((10,4),50.);x=np.ones((10,1,5));shares=np.ones((4,1));state=zero(1,1)
        np.testing.assert_array_equal(costs(m,layout,a,x,shares,state,self.d),a)
        state['price'][:]=10000;state['curve'][:]=1;got=costs(m,layout,a,x,shares,state,self.d)
        np.testing.assert_allclose(got[0],[95,116,155,65]);self.assertTrue(np.all(np.diff(got[:,:3],axis=1)>=0));np.testing.assert_array_equal(a,np.full((10,4),50.))
        state['price'][:]=-10000;state['curve'][:]=0;np.testing.assert_allclose(costs(m,layout,a,x,shares,state,self.d)[0],[5,5,5,35])
    def test_supported_resource_proposal_and_missing_generation(self):
        T=400;m=dict(nz=1,ng=1,zones=['FR'],offer_zones=['FR'],availability=np.full((T,1),100.));layout=dict(kinds=['gas']);x=np.zeros((T,1,5));x[:,:,0]=1
        monthly=[dict(generation_lower_twh=np.zeros((1,5)),generation_upper_twh=np.ones((1,5))) for _ in range(12)];target=dict(generation=np.full((12,1,5),np.nan))
        args=[m,layout,x,None,np.full((T,1),50.),np.full((T,1),50.),np.full((T,1),50.),np.full((T,1),60.),monthly,target,self.d]
        p=proposal(*args);self.assertAlmostEqual(p['price'][0,0,0],4000/736);self.assertEqual(p['support_hours'][0,0],400);self.assertFalse(p['complete_mix_targets'].any());self.assertFalse(p['mix'].any())
        args[5][:]=0;p=proposal(*args);self.assertFalse(p['price'].any())
    def test_mix_proposal_is_bid_signal_not_available_mw(self):
        T=200;m=dict(nz=1,ng=1,zones=['FR'],offer_zones=['FR'],availability=np.ones((T,1)));monthly=[dict(generation_lower_twh=np.zeros((1,5)),generation_upper_twh=np.ones((1,5))) for _ in range(12)];target=dict(generation=np.full((12,1,5),2.));before=m['availability'].copy()
        p=proposal(m,dict(kinds=['gas']),np.ones((T,1,5)),None,np.ones((T,1)),np.zeros((T,1)),np.ones((T,1)),np.ones((T,1)),monthly,target,self.d)
        np.testing.assert_allclose(p['mix'],[[-7.5,-7.5,-7.5]]);np.testing.assert_array_equal(m['availability'],before)
        z=zero(1,1);v=advance(z,p,[1,1,.5],self.d);np.testing.assert_array_equal(z['mix'],[[0,0,0]]);np.testing.assert_array_equal(v['curve'],[.5,.5])
    def test_score_rejects_material_mix_regression(self):
        ref=dict(price=30.,daily_demeaned_price=20.,generation=.3,trade=.1)
        self.assertAlmostEqual(record_score(ref,ref,0,self.d)['score'],1.)
        bad=ref|dict(price=20.,generation=.31);self.assertFalse(record_score(bad,ref,0,self.d)['eligible'])
    def test_ensemble_can_be_singleton_and_uses_declared_tolerances(self):
        r=dict(id='a',score=.9,penalty=0,ordinal=0,eligible=True,metrics=dict(price=25.));states={k:zero(1,1) for k in ['a','b','c']};records=[r]
        self.assertEqual(ensemble(records,states,self.d),['a'])
        records += [r|dict(id='b',score=.905,ordinal=1),r|dict(id='c',score=.905,ordinal=2,metrics=dict(price=27.))];states['b']['price'][:]=1
        self.assertEqual(ensemble(records,states,self.d),['a','b'])


if __name__=='__main__':unittest.main()
