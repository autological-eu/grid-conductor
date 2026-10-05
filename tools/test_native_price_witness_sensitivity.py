import copy
import unittest

from compare_native_price_witnesses import differences


class PriceSensitivityTests(unittest.TestCase):
    def report(self):
        return dict(status='provisional_fixed_inventory_price_diagnostic_not_validation', year=2025, hours=8760,
                    input_sha256='source', price_manifest_sha256='observed', observed_price_sha256={'FR':'prices'},
                    nodes=[dict(node='FR1', status='conditional_nodal_vs_observed_zonal_diagnostic_not_validation',
                                country='FR', provisional_observed_zone='FR', matched_hours=8759,
                                bias_eur_mwh=-30., mae_eur_mwh=40., rmse_eur_mwh=50., correlation=None),
                           dict(node='missing', status='native_nodal_price_row_absent')])

    def test_signed_metric_changes_and_unknowns_are_preserved(self):
        first = self.report()
        second = copy.deepcopy(first)
        second['nodes'][0]['bias_eur_mwh'] = -25.
        rows = differences(first, second)
        self.assertEqual(rows[0]['metrics']['bias_eur_mwh']['difference'], 5.)
        self.assertIsNone(rows[0]['metrics']['correlation']['difference'])
        self.assertNotIn('metrics', rows[1])

    def test_other_observations_or_coverage_cannot_be_compared(self):
        first = self.report()
        for mutate in [lambda x:x.update(input_sha256='changed'),
                       lambda x:x.update(hours=8759),
                       lambda x:x.update(observed_price_sha256={'FR':'changed'}),
                       lambda x:x['nodes'][0].update(matched_hours=8760),
                       lambda x:x['nodes'][0].update(provisional_observed_zone='PL')]:
            second = copy.deepcopy(first)
            mutate(second)
            with self.assertRaises(ValueError):
                differences(first, second)

    def test_duplicate_missing_or_nonfinite_nodes_fail(self):
        first = self.report()
        for mutate in [lambda x:x['nodes'].append(copy.deepcopy(x['nodes'][0])),
                       lambda x:x['nodes'].pop(),
                       lambda x:x['nodes'][0].update(bias_eur_mwh=float('nan')),
                       lambda x:x['nodes'][0].update(status='native_nodal_price_row_absent')]:
            second = copy.deepcopy(first)
            mutate(second)
            with self.assertRaises(ValueError):
                differences(first, second)


if __name__ == '__main__':
    unittest.main()
