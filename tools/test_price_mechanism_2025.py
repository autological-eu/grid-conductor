import unittest
import numpy as np
from scipy.sparse import csc_matrix
from price_mechanism_2025 import dual_replay,decompose,marginal_labels

def fixture():
    # Cheap area exports its 5 MW line limit; expensive area has a local marginal plant.
    m=dict(A=csc_matrix([[1,0,-1,0],[0,1,0,-1],[0,0,1,1],[0,0,1,0]]),
        ng=2,nl=0,nz=2,islands=[['A','B']],zones=['A','B'],
        cost=np.array([[10.,100.]]),availability=np.array([[20.,20.]]),
        load=np.array([[0.,15.]]),island_rhs=np.array([[0.]]),ratings=np.array([5.]),
        link_min=np.empty((1,0)),link_max=np.empty((1,0)))
    x=np.array([[5.,10.,5.,-5.]]);y=np.array([[10.,100.,100.,-90.]])
    return m,x,y,np.zeros_like(x),np.array([1050.]),np.array([[0.]])

class PriceTests(unittest.TestCase):
    def test_congestion_decomposition_and_duality(self):
        m,x,y,rc,obj,off=fixture();d=dual_replay(m,x,y,rc,obj,off)
        self.assertEqual(d['duality_gap_maximum_eur'],0.)
        e,c=decompose(m,y);np.testing.assert_array_equal(e,[[100,100]]);np.testing.assert_array_equal(c,[[-90,0]])
    def test_wrong_shadow_sign_rejected(self):
        m,x,y,rc,obj,off=fixture();y[0,-1]=90
        with self.assertRaises(AssertionError):dual_replay(m,x,y,rc,obj,off)
    def test_mixed_offer_identity_is_not_invented(self):
        m,x,y,rc,obj,off=fixture()
        labels=marginal_labels([dict(zone='A',carriers=['solar','onwind']),dict(zone='B',carriers=['CCGT'])],m,x,y[:,:2])
        self.assertTrue(labels[0,0].startswith('mixed:'));self.assertEqual(labels[0,1],'gas')
    def test_capacity_bound_is_not_an_interior_marginal_offer(self):
        m,x,y,rc,obj,off=fixture();m['availability'][0,0]=5.
        labels=marginal_labels([dict(zone='A',carriers=['nuclear']),dict(zone='B',carriers=['CCGT'])],m,x,y[:,:2])
        self.assertEqual(labels[0,0],'no_local_interior_offer')

if __name__=='__main__':unittest.main()
