import unittest
from audit_2025_cluster_geography import summarize, compose_membership


class GeographyTests(unittest.TestCase):
    def test_extent_preserves_constituents_without_zone_guess(self):
        rows = summarize({'a': ('SE', 10., 55.), 'b': ('SE', 20., 65.)}, {'cluster': 'SE'}, [('a', 'cluster'), ('b', 'cluster')])
        self.assertEqual(rows[0]['latitude_min'], 55.)
        self.assertEqual(rows[0]['latitude_max'], 65.)
        self.assertIsNone(rows[0]['bidding_zone'])

    def test_cross_country_cluster_flagged(self):
        rows = summarize({'a': ('DE', 10., 50.), 'b': ('FR', 9., 49.)}, {'c': 'DE'}, [('a', 'c'), ('b', 'c')])
        self.assertFalse(rows[0]['country_consistent'])

    def test_invalid_membership_fails_closed(self):
        for membership in [[], [('a', 'c'), ('a', 'c')], [('missing', 'c')], [('a', 'unknown')]]:
            with self.assertRaises(ValueError):
                summarize({'a': ('DE', 10., 50.)}, {'c': 'DE'}, membership)

    def test_nonfinite_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            summarize({'a': ('DE', float('nan'), 50.)}, {'c': 'DE'}, [('a', 'c')])

    def test_simplification_chain_is_explicit(self):
        self.assertEqual(compose_membership([('original', 'simplified')], [('simplified', 'cluster')]), [('original', 'cluster')])
        with self.assertRaises(ValueError):
            compose_membership([('original', 'missing')], [('simplified', 'cluster')])
