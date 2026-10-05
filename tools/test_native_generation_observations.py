import unittest
from compare_native_generation_observations import compare


class NativeObservations(unittest.TestCase):
    def fixture(self):
        native=dict(status='annual_fixed_inventory_generation_accounting_diagnostic_not_validation',year=2025,hours=8760,
            countries=[dict(country='CH',primary_generation_mwh=120.,monthly=[dict(month=m,primary_generation_mwh_by_model_carrier={'nuclear':10.}) for m in range(1,13)])])
        observed=dict(status='raw_generation_observations_replayed_not_model_validation',year=2025,
            zones=[dict(zone='CH',geographic_scope='national area',monthly=[dict(month=m,status='raw_interval_energy_replayed',
            full_reported_primary_energy_mwh=8.,complete_reported_primary_hours=1,expected_hours=1,by_reported_type={'B14':dict(reported_energy_mwh=8.,observed_hours=1)}) for m in range(1,13)])])
        return native,observed

    def test_unreconciled_difference_is_not_validation(self):
        n,o=self.fixture();r=compare(n,o)[0]
        self.assertEqual(r['difference_mwh'],24.);self.assertEqual(r['relative_difference'],.25)
        self.assertEqual(r['status'],'unreconciled_fixed_inventory_national_generation_diagnostic')

    def test_no_annualisation_or_missing_category_zero(self):
        n,o=self.fixture();o['zones'][0]['monthly'][0]['full_reported_primary_energy_mwh']=None
        r=compare(n,o)[0];self.assertIsNone(r['difference_mwh'])
        self.assertIsNone(r['monthly'][0]['components'][0]['reported_energy_mwh'])

    def test_split_country_not_inferred(self):
        n,o=self.fixture();n['countries'][0]['country']='SE'
        self.assertEqual(compare(n,o)[0]['status'],'no_supported_national_observation_comparison')

    def test_rejects_wrong_year_or_partial_native_calendar(self):
        n,o=self.fixture();n['hours']=2
        with self.assertRaises(ValueError):compare(n,o)


if __name__=='__main__':unittest.main()
