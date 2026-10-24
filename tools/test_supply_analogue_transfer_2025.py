import unittest
import numpy as np
from supply_analogue_transfer_2025 import features,match,transfer,match_neighbor_days
from independent_hourly_transport_2025 import economic_nodes


class AnalogueTests(unittest.TestCase):
    def test_exact_day_and_clock_matching(self):
        jan=np.repeat(np.arange(31),24)[:,None]+np.tile(np.arange(24),31)[:,None]/100
        feb=np.vstack([jan[day*24:(day+1)*24] for day in range(28)])
        for method in ['nearest_day','nearest_hour']:
            hours,weights,info=match(np.vstack([jan,feb]),method)
            np.testing.assert_array_equal(hours[:,0],np.arange(672))
            np.testing.assert_array_equal(weights,np.ones((672,1)))
            self.assertTrue(np.isfinite(info['nearest_distance']).all())

    def test_features_ignore_observed_targets_and_use_training_scales(self):
        source=dict(zones=['A'],groups=[dict(zone_id=0,technology='gas')])
        data=dict(load=np.ones((1416,1))*1000,capacity=np.ones((1416,1))*2000,
                  source_cost=np.ones((1416,1))*50,observed_prices=np.zeros((1416,1)),ember=np.zeros((12,1,1)))
        a,meta=features(source,data)
        data['observed_prices'][:]=1e9;data['ember'][:]=1e9
        b,other=features(source,data);np.testing.assert_array_equal(a,b);self.assertEqual(meta,other)
        data['capacity'][744:]*=10
        c,last=features(source,data);np.testing.assert_array_equal(a[:744],c[:744]);self.assertEqual(meta,last)

    def test_single_donor_exact_nodes_and_unsupported_neutral(self):
        rng=np.random.default_rng(42);theta=rng.normal(size=(744,2,6));capacity=np.ones((1416,2));capacity[:744,1]=0
        donors=np.arange(672)[:,None];neutral=np.zeros((2,6))
        raw,info=transfer(theta,capacity,donors,np.ones((672,1)),neutral)
        np.testing.assert_allclose(economic_nodes(raw)[:,0],economic_nodes(theta[:672])[:,0],atol=1e-12,rtol=0)
        np.testing.assert_allclose(economic_nodes(raw)[:,1],np.broadcast_to(economic_nodes(neutral)[1],(672,6)),atol=1e-12)
        self.assertEqual(info['neutral_fallback_hour_groups'],672)

    def test_neighbor_matching_keeps_zones_and_technology_identity(self):
        jan=np.repeat(np.arange(31),24)[:,None]*np.array([[1.,2.]])
        feb=jan[:672].copy();matrix=np.vstack([jan,feb])
        donors,weights,_=match_neighbor_days(matrix,[0,1],np.array([[0,1]]),[0,0,1],2)
        self.assertEqual(donors.shape,(672,3,1))
        np.testing.assert_array_equal(donors[:,0],donors[:,1])
        np.testing.assert_array_equal(donors[:,:,0],np.broadcast_to(np.arange(672)[:,None],(672,3)))
        theta=np.random.default_rng(5).normal(size=(744,3,6))
        raw,_=transfer(theta,np.ones((1416,3)),donors,weights,np.zeros((3,6)))
        np.testing.assert_allclose(economic_nodes(raw),economic_nodes(theta[:672]),atol=1e-12,rtol=0)


if __name__=='__main__':unittest.main()
