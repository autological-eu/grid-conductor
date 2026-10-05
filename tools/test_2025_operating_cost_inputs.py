import unittest
from audit_2025_operating_cost_inputs import summarize


class OperatingCostInputs(unittest.TestCase):
    def test_efficiency_converts_fuel_factor_to_electrical_slope(self):
        rows=summarize(['coal','coal'],[20.,25.],[100.,200.],[.4,.5],{'coal':.336})
        self.assertEqual(rows[0]['nominal_capacity_mw'],300.)
        self.assertAlmostEqual(rows[0]['carbon_price_slope_tco2_per_mwh_electric_min'],.672)
        self.assertAlmostEqual(rows[0]['carbon_price_slope_tco2_per_mwh_electric_max'],.84)
        self.assertEqual(rows[0]['static_marginal_cost_eur_mwh_min'],20.)

    def test_missing_factor_remains_unknown(self):
        row=summarize(['other'],[5.],[10.],[1.],{})[0]
        self.assertIsNone(row['carbon_price_slope_tco2_per_mwh_electric_min'])

    def test_zero_capacity_asset_does_not_define_sensitivity_range(self):
        row=summarize(['gas','gas'],[30.,50.],[10.,0.],[.5,.1],{'gas':.2})[0]
        self.assertAlmostEqual(row['carbon_price_slope_tco2_per_mwh_electric_max'],.4)

    def test_invalid_efficiency_rejected(self):
        with self.assertRaises(ValueError):summarize(['gas'],[5.],[10.],[0.],{'gas':.2})

    def test_nonfinite_cost_or_factor_rejected(self):
        with self.assertRaises(ValueError):summarize(['gas'],[float('nan')],[10.],[.5],{'gas':.2})
        with self.assertRaises(ValueError):summarize(['gas'],[5.],[10.],[.5],{'gas':float('nan')})


if __name__=='__main__':unittest.main()
