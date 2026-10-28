"""The mixed-coverage fit must backpropagate its observed generation terms."""

import unittest
from types import SimpleNamespace

import numpy as np

from fit_mixed_flow_monthly_bids_2025 import data_loss
from batched_transport_dispatch_2025 import softclip


class MixedFlowLossTest(unittest.TestCase):
    def test_compatible_observed_flow_loss_has_correct_price_gradient(self):
        market = SimpleNamespace(lower=np.array([[-1.]]), upper=np.array([[1.]]),
                                 cost=4., M=np.array([[-1., 1.]]), flow_tau=.1)

        def score(prices):
            unconstrained=(prices@market.M.T)/market.cost
            flow=market.lower+softclip(unconstrained-market.lower,
                                      market.upper-market.lower,market.flow_tau)
            result=dict(prices=prices, quantities_gw=np.array([[2.]]),
                        flows_gw=flow,hours=np.array([0]))
            return data_loss(market,result,np.full((1,2),np.nan),
                np.array([[[np.nan]]]),np.zeros((1,1,1)),np.array([0]),np.array([0]),
                np.array([[.1]]),np.array([[True]]))

        prices=np.array([[20.,21.]])
        metrics,_,gradient=score(prices)
        self.assertEqual(metrics['observed_flow_cells'],1)
        for zone in range(2):
            up=prices.copy();down=prices.copy();up[0,zone]+=1e-5;down[0,zone]-=1e-5
            numerical=(score(up)[0]['total_loss']-score(down)[0]['total_loss'])/2e-5
            self.assertTrue(np.isclose(gradient[0,zone],numerical,atol=1e-7))

    def test_price_is_scored_when_exchange_is_missing(self):
        market = SimpleNamespace(lower=np.array([[-1.]]), upper=np.array([[1.]]),
                                 cost=np.array([10.]), M=np.array([[1.]]), flow_tau=1.)
        result = dict(prices=np.array([[40.]]), quantities_gw=np.array([[2.]]),
                      flows_gw=np.array([[0.]]), hours=np.array([0]))
        metrics, _, gp = data_loss(market, result, np.array([[20.]]),
            np.array([[[np.nan]]]), np.zeros((1, 1, 1)), np.array([0]), np.array([0]),
            np.array([[np.nan]]), np.array([[False]]))
        self.assertEqual(metrics['price_cells'], 1)
        self.assertEqual(metrics['observed_flow_cells'], 0)
        self.assertGreater(gp[0, 0], 0)

    def test_generation_volume_and_mix_have_nonzero_correct_gradients(self):
        market = SimpleNamespace(lower=np.array([[-1.]]), upper=np.array([[1.]]),
                                 cost=np.array([10.]), M=np.array([[1.]]), flow_tau=1.)
        q = np.array([[2., 3.]])
        fixed = np.zeros((1, 1, 2))
        observed = np.array([[[4., 1.]]])

        def score(values):
            result = dict(prices=np.array([[40.]]), quantities_gw=values,
                          flows_gw=np.array([[0.]]), hours=np.array([0]))
            return data_loss(market, result, np.array([[np.nan]]), observed, fixed,
                             np.array([0, 0]), np.array([0, 1]),
                             np.array([[np.nan]]), np.array([[False]]))

        metrics, gq, _ = score(q)
        self.assertGreater(metrics['mix_share_mae'], 0)
        self.assertGreater(metrics['generation_mae_gw'], 0)
        for group in range(2):
            up = q.copy(); down = q.copy(); up[0, group] += 1e-5; down[0, group] -= 1e-5
            numerical = (score(up)[0]['total_loss']-score(down)[0]['total_loss'])/2e-5
            self.assertTrue(np.isclose(gq[0, group], numerical, atol=1e-7))


if __name__ == '__main__':
    unittest.main()
