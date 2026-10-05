import unittest
import pandas as pd
import pypsa
from audit_submonthly_equivalence import compare, permutation


class SubmonthlyEquivalenceTests(unittest.TestCase):
    def test_losses_inflow_and_internal_inventory_match_monolith(self):
        n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=4,freq='h'))
        n.add('Bus','A');n.add('Load','L',bus='A',p_set=[2.,3.,4.,5.])
        n.add('Generator','G',bus='A',p_nom=20.,marginal_cost=[10.,20.,30.,40.])
        n.add('StorageUnit','S',bus='A',p_nom=10.,max_hours=2.,efficiency_store=.9,efficiency_dispatch=.8,
              standing_loss=.01,cyclic_state_of_charge=True,inflow=[1.,0.,2.,0.])
        result=compare(n,n.snapshots,2)
        self.assertEqual(result['status'],'coefficient_equivalence_passed')
        self.assertEqual(max(result['maximum_differences'].values()),0.)

    def test_label_domain_mismatches_rejected(self):
        for actual,expected in [(['a','a'],['a','b']),(['a'],['b'])]:
            with self.assertRaises(ValueError):permutation(actual,expected)
