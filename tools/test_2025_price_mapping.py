import unittest
from audit_2025_price_mapping import candidate


class MappingTests(unittest.TestCase):
    def test_split_zones_never_guessed_from_country(self):
        for country in ['SE', 'NO', 'DK', 'IT']:
            self.assertIsNone(candidate(country, {'SE4', 'NO1', 'DK1', 'IT-North'})[0])
    def test_missing_observation_remains_unresolved(self):
        self.assertIsNone(candidate('FR', set())[0])
        self.assertIsNone(candidate('GB', {'FR'})[0])
    def test_combined_zone_keeps_explicit_market_identity(self):
        for country in ['DE', 'LU']:
            self.assertEqual(candidate(country, {'DE-LU'})[0], 'DE-LU')
        self.assertEqual(candidate('FR', {'FR'})[0], 'FR')


if __name__ == '__main__':
    unittest.main()
