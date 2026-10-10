"""Check observed-price conversion and fail-closed calendar coverage."""
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from prepare_fuel_prices import compile_prices, MMBTU_MWH


class FuelInputs(unittest.TestCase):
    def test_conversion_calendar_and_missing_month(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            wb = root / 'prices.xlsx'; fx = root / 'fx.csv'
            table = pd.DataFrame({'Month': [f'2025M{m:02d}' for m in range(1, 13)],
                                  'Natural gas, Europe': [10.] * 12,
                                  'Crude oil, Brent': [80.] * 12})
            with pd.ExcelWriter(wb) as writer:
                table.to_excel(writer, sheet_name='Monthly Prices', startrow=4, index=False)
            exchange = pd.DataFrame({'KEY': ['EXR.D.USD.EUR.SP00.A'] * 24,
                                    'TIME_PERIOD': [f'2025-{m:02d}-{d:02d}' for m in range(1, 13) for d in (2, 3)],
                                    'OBS_VALUE': [1., 2.] * 12})
            exchange.to_csv(fx, index=False)
            x = compile_prices(wb, fx, 2025, 1.1, 2., 80.)
            self.assertEqual(len(x['hours']), 8760)
            self.assertAlmostEqual(x['hours'][0]['gas_eur_mwh_th'], 10 * .75 / MMBTU_MWH * 1.1)
            self.assertAlmostEqual(x['hours'][0]['oil_eur_mwh_th'], 30.)
            self.assertEqual(x['hours'][-1]['utc'], '2025-12-31T23:00:00Z')
            exchange.iloc[:-2].to_csv(fx, index=False)
            with self.assertRaises(ValueError):
                compile_prices(wb, fx, 2025, 1., 2., 80.)
            pd.concat([exchange, exchange.iloc[:1]]).to_csv(fx, index=False)
            with self.assertRaises(ValueError):
                compile_prices(wb, fx, 2025, 1., 2., 80.)


if __name__ == '__main__':
    unittest.main()
