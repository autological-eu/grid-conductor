import unittest
from compare_native_price_observations import metrics

class PriceObservations(unittest.TestCase):
    def test_signed_bias_and_missing(self):
        r=metrics([-10,999,30],[-20,None,20]);self.assertEqual(r['matched_hours'],2)
        self.assertEqual(r['bias_eur_mwh'],10);self.assertEqual(r['mae_eur_mwh'],10)
    def test_empty_and_constant(self):
        self.assertIsNone(metrics([1],[None])['bias_eur_mwh'])
        self.assertIsNone(metrics([1,1],[2,3])['correlation'])
    def test_invalid_or_unmatched(self):
        for a,b in [([1],[]),([float('nan')],[2]),([1],[True]),([1],[float('inf')])]:
            with self.assertRaises(ValueError):metrics(a,b)
