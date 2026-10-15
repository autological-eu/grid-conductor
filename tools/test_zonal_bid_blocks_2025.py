import unittest
import numpy as np
from scipy.sparse import csc_matrix
from zonal_bid_blocks_2025 import split_model,collapse,costs,proposal,choose,NTRAIN,canonical_parameters


class ZonalBlocksTest(unittest.TestCase):
    def fixture(self,T=2):
        m=dict(ng=2,nl=0,nz=2,zones=['A','B'],A=csc_matrix([[1.,0.,-1.,0.],[0.,1.,0.,-1.]]),
               availability=np.tile([100.,50.],(T,1)),cost=np.tile([40.,20.],(T,1)),
               offer_zones=np.array(['A','B']),emergency_mask=np.array([False,False]))
        ctx=dict(groups=[[0],[1]],classes=['gas','nuclear'],availability=m['availability'],generation_keys=[('A','Gas'),('B','Nuclear')],country_keys=['A','B'])
        return m,ctx

    def test_blocks_preserve_available_capacity_and_physical_rows(self):
        m,c=self.fixture();s,ctx,layout=split_model(m,c)
        x=np.c_[s['availability'],np.array([[100,50],[100,50]])];combined=collapse(x,m,layout)
        np.testing.assert_allclose(combined[:,:2],m['availability'])
        np.testing.assert_allclose(s['A']@x.T,m['A']@combined.T)
        np.testing.assert_allclose(ctx['availability'].sum(axis=1),c['availability'].sum(axis=1))

    def test_zonal_offsets_and_monotone_blocks(self):
        m,c=self.fixture();s,ctx,l=split_model(m,c);delta=np.zeros((2,3));delta[0,0]=10;spread=np.zeros_like(delta);spread[0,0]=30
        b=costs(s,ctx,l,delta,spread)
        np.testing.assert_array_equal(b[0],[50,80,20,20])
        spread[0,0]=-1
        with self.assertRaises(ValueError):costs(s,ctx,l,delta,spread)

    def test_training_only_and_unsupported_pairs(self):
        m,c=self.fixture(NTRAIN);x=np.tile([50.,50.,0.,0.],(NTRAIN,1));p=np.tile([40.,20.],(NTRAIN,1));obs=p+10
        result,counts=proposal(m,c,x,p,obs,'offset')
        self.assertGreater(result[0,0],0);self.assertEqual(result[1,2],0) # Nuclear is at its cap, not a local interior offer.
        with self.assertRaises(ValueError):proposal(m,c,x,p,np.r_[obs,obs],'offset')

    def test_failed_trial_and_tie_selection(self):
        records=[dict(index=0,score=1.,penalty=0.),dict(index=1,score=1.,penalty=.1),dict(index=2,score=None,penalty=0.)]
        self.assertEqual(choose(records)['index'],0)

    def test_signed_zero_is_one_parameter_state(self):
        import json
        a=np.array([[-0.,0.,-0.]]);b=np.zeros((1,3))
        key=lambda x:json.dumps([v.tolist() for v in canonical_parameters(x,b)])
        self.assertEqual(key(a),key(b))

    def test_closed_zone_clears_on_upper_block_after_seventy_percent(self):
        from scipy.optimize import linprog
        m,c=self.fixture(1);s,ctx,layout=split_model(m,c);delta=np.zeros((2,3));spread=np.zeros_like(delta);spread[0,0]=30
        bids=costs(s,ctx,layout,delta,spread)[0]
        # Isolated-zone demand exceeds gas's 70 MW lower block. Nuclear is in B.
        bounds=[(0,a) for a in s['availability'][0]]+[(0,0),(0,0)]
        result=linprog(np.r_[bids,0,0],A_eq=s['A'],b_eq=[80,25],bounds=bounds,method='highs')
        self.assertTrue(result.success)
        np.testing.assert_allclose(result.x[:2],[70,10])
        np.testing.assert_allclose(result.eqlin.marginals,[70,20])


if __name__=='__main__':unittest.main()
