import unittest
import numpy as np
from scipy.sparse import csc_matrix
from scipy.optimize import linprog
from hourly_storage_bids import coefficients,advance,future_reference,matrix,certificate


def asset(**changes):
    return dict(id='test',zone='A',technology='battery',charge_mw=10.,discharge_mw=10.,energy_mwh=20.,eta_charge=.9,eta_discharge=.8,standing_loss=0.)|changes


class Storage(unittest.TestCase):
    def test_empty_full_and_efficiencies(self):
        b=coefficients([asset()],['A'],[0],[100],1);self.assertEqual(b['discharge_max'][0],0)
        e,_=advance(b,[10],[0]);self.assertEqual(e[0],9)
        b=coefficients([asset()],['A'],e,[100],1);self.assertAlmostEqual(b['discharge_max'][0],7.2)
        e,_=advance(b,[0],[7.2]);self.assertAlmostEqual(e[0],0)
        b=coefficients([asset()],['A'],[20],[100],1);self.assertEqual(b['charge_max'][0],0)
    def test_carry_across_day_and_loss(self):
        e=np.array([10.]);a=asset(standing_loss=.01)
        for _ in range(25):e,_=advance(coefficients([a],['A'],e,[50],1),[0],[0])
        self.assertAlmostEqual(e[0],10*.99**25)
    def test_no_wrap_or_observed_price_requirement(self):
        p=np.array([[100.],[10.],[20.],[-10.]])
        np.testing.assert_array_equal(future_reference(p,2)[:,0],[15.,5.,0.,0.])
    def test_reject_state_power_and_cycle(self):
        with self.assertRaises(ValueError):coefficients([asset()],['A'],[-1],[10],1)
        b=coefficients([asset()],['A'],[10],[10],1)
        with self.assertRaises(ValueError):advance(b,[11],[0])
        with self.assertRaises(ValueError):advance(b,[1],[1])
    def test_negative_forecast_spread_stays_positive(self):
        b=coefficients([asset()],['A'],[10],[-100],1);self.assertLess(b['buy'][0],b['sell'][0])
    def test_lp_buy_and_sell_and_certificate(self):
        A=matrix(csc_matrix([[1.]]),[asset()],['A'])
        for e,price,expected in [(0,5,'charge'),(20,100,'discharge')]:
            b=coefficients([asset()],['A'],[e],[50],1);cost=np.r_[price,-b['buy'],b['sell']];lo=np.zeros(3);hi=np.r_[100,b['charge_max'],b['discharge_max']]
            r=linprog(cost,A_eq=A,b_eq=[10.],bounds=list(zip(lo,hi)),method='highs');self.assertTrue(r.success)
            certificate(A,cost,lo,hi,np.array([10.]),np.array([10.]),r.x,r.eqlin.marginals)
            self.assertGreater(r.x[1 if expected=='charge' else 2],0);advance(b,r.x[1:2],r.x[2:3])


if __name__=='__main__':unittest.main()
