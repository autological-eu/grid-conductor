"""Checks that the annual transfer changes bids, not physical offer geometry."""
import unittest
import numpy as np

from monthly_fast_lp_costs_2025 import sampled_anchors,costs_for_hours
from fit_monthly_fast_splines_2025 import initial_weights,penalty


class TransferTests(unittest.TestCase):
    def test_piecewise_linear_curve_and_endpoints(self):
        anchors=np.broadcast_to(np.arange(6.)*10,(2,3,6))
        u=np.array([[0,.1,.2],[.5,.9,1.]])
        np.testing.assert_allclose(sampled_anchors(anchors,u),50*u)

    def test_existing_offer_midpoints_and_untouched_columns(self):
        class Market:
            ng=2
            capacity=np.array([[.1,.05],[.1,.05]])
            def offers(self,theta,hours):
                anchors=np.broadcast_to(np.arange(6.)*10,(len(hours),2,6)).copy()
                return {'anchors':anchors}
        schema={'groups':[{'zone':'DE-LU','technology':'gas'},
                          {'zone':'DE-LU','technology':'solar'}]}
        data={'capacity':np.array([[40.,60.],[40.,60.]])}
        lp={'cost':np.array([[8.,12.,0.,500.],[12.,8.,0.,500.]]),
            'availability':np.array([[16.,24.,60.,1000.],[16.,24.,60.,1000.]])}
        before=lp['cost'].copy();available=lp['availability'].copy()
        weights=np.zeros((2,26,6));centers=np.zeros((2,2))
        cost=costs_for_hours(schema,data,Market(),lp,weights,centers,
                             np.arange(2),{0:[0,1],1:[2]})
        np.testing.assert_allclose(cost[0,:2],[10.,35.])
        np.testing.assert_allclose(cost[1,:2],[40.,15.])
        np.testing.assert_array_equal(cost[:,2:],before[:,2:])
        np.testing.assert_array_equal(lp['availability'],available)
        np.testing.assert_array_equal(lp['cost'],before)

    def test_neutral_parameters_are_unpenalized(self):
        weights=initial_weights(3)
        value,gradient=penalty(weights,weights.copy(),np.array([True,False,True]))
        self.assertEqual(value,0.)
        np.testing.assert_array_equal(gradient,0.)


if __name__=='__main__':unittest.main()
