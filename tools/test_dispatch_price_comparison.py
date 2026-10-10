"""Independent error-calculation and geography guard checks."""
import unittest
import numpy as np
from compare_daily_dispatch_prices import metrics, model_area


class PriceErrors(unittest.TestCase):
    def test_signed_negative_prices_missing_and_errors(self):
        result = metrics([-10, 30, 99, 10], [-20, 20, np.nan, 30])
        self.assertEqual(result['known_hours'], 3)
        self.assertAlmostEqual(result['bias_eur_mwh'], 0)
        self.assertAlmostEqual(result['mae_eur_mwh'], 40 / 3)
        self.assertAlmostEqual(result['rmse_eur_mwh'], np.sqrt(200))
        self.assertEqual(result['model_negative_hours'], 1)
        self.assertEqual(result['observed_negative_hours'], 1)

    def test_no_undefined_correlation_or_missing_fill(self):
        self.assertIsNone(metrics([1, 1], [2, 3])['correlation'])
        self.assertEqual(metrics([1], [np.nan]), {'known_hours': 0})

    def test_collapsed_geography_and_unknown_island(self):
        self.assertEqual(model_area('NO1')[0], model_area('NO4')[0])
        self.assertEqual(model_area('SE1')[0], model_area('SE4')[0])
        self.assertEqual(model_area('IT-North')[0], model_area('IT-SUD')[0])
        self.assertNotEqual(model_area('DK1')[0], model_area('DK2')[0])
        self.assertIsNone(model_area('IT-SARD')[0])
        self.assertEqual(model_area('DE-LU')[0], '0:DE')


if __name__ == '__main__':
    unittest.main()
