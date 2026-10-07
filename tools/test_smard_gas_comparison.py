import copy
import unittest
from audit_smard_2025_gas import aggregate, START, END, HOUR
from compare_smard_2025_gas import compare


class GasComparisonTests(unittest.TestCase):
    def fixture(self):
        reference = aggregate([[t, 2.] for t in range(START, END, HOUR)])
        reference['year'] = 2025
        observed = dict(zones=[dict(zone='DE-LU', monthly=[dict(month=m['month'], expected_hours=m['expected_hours'],
                        status='raw_interval_energy_replayed', by_reported_type={'B04': dict(observed_hours=m['expected_hours'],
                        reported_energy_mwh=float(m['expected_hours']))}) for m in reference['monthly']])])
        native = dict(hours=8760, countries=[dict(country='DE', monthly=[dict(month=m['month'],
                      primary_generation_mwh_by_model_carrier={'CCGT': .5*m['expected_hours'], 'OCGT': 0.}) for m in reference['monthly']])])
        return reference, observed, native

    def test_exact_interval_sums_and_signed_consistency_difference(self):
        report = compare(*self.fixture())
        self.assertEqual(report['annual']['smard_mwh'], 17520.)
        self.assertEqual(report['annual']['entsoe_reported_mwh'], 8760.)
        self.assertEqual(report['annual']['native_ccgt_ocgt_mwh'], 4380.)
        self.assertEqual(report['annual']['smard_minus_entsoe_mwh'], 8760.)

    def test_missing_partial_or_changed_calendar_is_rejected(self):
        for failure in ['null', 'partial', 'calendar', 'carrier']:
            r, o, n = copy.deepcopy(self.fixture())
            if failure == 'null':
                r['monthly'][0]['complete_reported_energy_mwh'] = None
            elif failure == 'partial':
                o['zones'][0]['monthly'][0]['by_reported_type']['B04']['observed_hours'] -= 1
            elif failure == 'calendar':
                n['countries'][0]['monthly'][0]['month'] = 2
            else:
                del n['countries'][0]['monthly'][0]['primary_generation_mwh_by_model_carrier']['CCGT']
            with self.assertRaises(ValueError):
                compare(r, o, n)


if __name__ == '__main__':
    unittest.main()
