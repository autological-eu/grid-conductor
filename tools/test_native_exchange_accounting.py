import unittest
from summarize_native_exchanges import totals

class ExchangeAccounting(unittest.TestCase):
    def test_signed_net_and_separate_positive_negative(self):
        r=totals([10,-20,5]);self.assertEqual(r['net_export_mwh'],-5)
        self.assertEqual(r['positive_net_export_mwh'],15);self.assertEqual(r['negative_net_import_mwh'],20)
        self.assertEqual(r['positive_net_export_hours'],2)
    def test_invalid_and_empty(self):
        self.assertEqual(totals([])['hours'],0)
        for values in [[float('nan')],[[1,2]]]:
            with self.assertRaises(ValueError):totals(values)
