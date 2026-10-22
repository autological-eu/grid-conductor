"""Bid-fit boundary tests; annual feasibility is checked against saved LP proofs."""
import unittest
import numpy as np
from solar_anchor_bids_2025 import fit,costs


class BidRules(unittest.TestCase):
    def test_missing_and_unsupported_never_imputed(self):
        a=np.ones((200,2));b=np.full(200,np.nan)
        np.testing.assert_array_equal(fit(a,b,np.ones(200,bool),168,168),[0,0])
        np.testing.assert_array_equal(fit(a,np.ones(200),np.arange(200)<167,168,168),[0,0])

    def test_ridge_and_clipped_extremes(self):
        a=np.ones((200,1));mask=np.ones(200,bool)
        self.assertAlmostEqual(fit(a,np.full(200,10000.),mask,168,168)[0],20000/368)

    def test_bounded_resource_shifts_preserve_tranche_order_and_other_bids(self):
        anchor=np.array([[10.,30.,2.,-5.,5000.]])
        beta=np.zeros((1,3,1));beta[0,0,0]=-100;beta[0,2,0]=100
        result=costs(anchor,['DE-LU'],['DE-LU']*5,['gas','gas','nuclear','renewable','other'],np.ones((1,1,1)),beta,.5,[30,30,7.5])
        np.testing.assert_array_equal(result,[[0,15,5.75,-5,5000]])
        np.testing.assert_array_equal(costs(anchor,['DE-LU'],['DE-LU']*5,['gas','gas','nuclear','renewable','other'],np.ones((1,1,1)),beta,0,[30,30,7.5]),anchor)


if __name__=='__main__':unittest.main()
