import unittest
import numpy as np
from supply_knot_splines_2025 import initial_parameters
from run_supply_knots_lp_2025 import joint_loss
from sigmoid_month_pairs_2025 import FAMILIES


class KnotTrainingTests(unittest.TestCase):
    def test_country_share_monthly_loss_gradient(self):
        groups=[dict(country_id=0,family='Gas'),dict(country_id=1,family='Gas')]
        sealed=dict(original_groups=groups,mapping=[0,0]);data=dict(capacity=np.array([[400.],[400.]]))
        original=np.array([[100.,300.],[300.,100.]])
        design=dict(price_smooth_absolute_epsilon=1,price_scale_eur_mwh=40,generation_floor_twh=.25,generation_smooth_absolute_epsilon=.01,ridge=.001)
        theta=initial_parameters(1);neutral=theta.copy();prices=np.array([[50.],[70.]]);values=np.array([[.1,0.],[.2,0.]])
        ember=np.full((2,len(FAMILIES)),np.nan);ember[:,FAMILIES.index('Gas')]=[.2,.3]
        target=dict(prices=np.array([[45.],[55.]]),ember=ember);fixed=np.zeros_like(ember)
        def objective(pp,xx):return joint_loss(sealed,data,original,design,theta,neutral,pp,xx,np.array([0,1]),744,target,fixed)
        _,gx,gp,_,_=objective(prices,values);eps=1e-5
        for pp,xx,index,wanted in [(prices,values,(0,0),gx[0,0]),(prices,values,(1,0),gx[1,0])]:
            plus=xx.copy();minus=xx.copy();plus[index]+=eps;minus[index]-=eps
            finite=(objective(pp,plus)[0]-objective(pp,minus)[0])/(2*eps)
            self.assertAlmostEqual(finite,wanted,delta=1e-8)
        plus=prices.copy();minus=prices.copy();plus[0,0]+=eps;minus[0,0]-=eps
        self.assertAlmostEqual((objective(plus,values)[0]-objective(minus,values)[0])/(2*eps),gp[0,0],delta=1e-8)


if __name__=='__main__':unittest.main()
