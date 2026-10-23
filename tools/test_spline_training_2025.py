"""Joint monthly loss derivatives and explicit target slicing."""
import unittest
import numpy as np
from differentiable_spline_clearing import initial_parameters
from run_differentiable_spline_2025 import loss,targets
from sigmoid_month_pairs_2025 import FAMILIES


class TrainingTests(unittest.TestCase):
    def fixture(self):
        sealed=dict(countries=['DE'],groups=[dict(country_id=0,family='Gas')])
        design=dict(price_smooth_absolute_epsilon=1.,price_scale_eur_mwh=40.,generation_floor_twh=.25,
                    generation_smooth_absolute_epsilon=.01,ridge=.001)
        theta=initial_parameters(1);neutral=theta.copy();theta[0,0]=.2
        prices=np.array([[55.],[70.]]);values=np.array([[10.,0.],[12.,0.]])
        fixed=np.zeros((1,len(FAMILIES)));ember=np.full_like(fixed,np.nan);ember[0,FAMILIES.index('Gas')]=9.
        return sealed,design,theta,neutral,prices,values,fixed,dict(prices=np.array([[50.],[75.]]),ember=ember),744

    def test_loss_dispatch_price_and_direct_derivatives(self):
        args=list(self.fixture());value,gx,gp,direct,_=loss(*args);eps=1e-5
        for arg,index,gradient in [(4,(0,0),gp[0,0]),(5,(1,0),gx[1,0]),(2,(0,0),direct[0,0])]:
            plus=list(args);minus=list(args);plus[arg]=args[arg].copy();minus[arg]=args[arg].copy()
            plus[arg][index]+=eps;minus[arg][index]-=eps
            finite=(loss(*plus)[0]-loss(*minus)[0])/(2*eps)
            self.assertAlmostEqual(gradient,finite,delta=1e-8)

    def test_target_slice_isolated_from_nontraining_data(self):
        data=dict(observed_prices=np.arange(12.).reshape(6,2),ember=np.arange(24.).reshape(12,1,2))
        first=targets(data,np.array([0,1]),1)
        data['observed_prices'][2:]=np.nan;data['ember'][1:]=np.nan
        second=targets(data,np.array([0,1]),1)
        for name in first:np.testing.assert_array_equal(first[name],second[name])
        data['observed_prices'][:]=999;np.testing.assert_array_equal(first['prices'],np.arange(4.).reshape(2,2))


if __name__=='__main__':unittest.main()
