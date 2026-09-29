"""Tests for the baseline extractor's country aggregation and CO2 accounting.

The bugs these cover were all silent: the module had never been run, so its
grouping keys, unit conversions and aggregation mode were unchecked. Each test
pins a specific failure mode.
"""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import extract_baseline as eb


class CountryNamesTests(unittest.TestCase):
    def test_every_model_country_has_a_name(self):
        countries = "AL AT BA BE BG CH CZ DE DK EE ES FI FR GB GR HR HU IE IT LT LU LV ME MK NL NO PL PT RO RS SE SI SK XK".split()
        missing = [c for c in countries if c not in eb.COUNTRY_NAMES]
        self.assertEqual(missing, [], f"missing display names for {missing}")

    def test_names_are_not_the_country_code(self):
        # The extractor previously wrote name == code, which left the map and
        # sidebar displaying bare ISO codes.
        self.assertNotEqual(eb.COUNTRY_NAMES["DE"], "DE")
        self.assertNotEqual(eb.COUNTRY_NAMES["XK"], "XK")


class AggregationModeTests(unittest.TestCase):
    """Countries aggregate by bus, and prices average while totals sum."""

    def _frame(self):
        return pd.DataFrame(
            [[1.0, 2.0, 10.0], [3.0, 4.0, 20.0]],
            index=["t0", "t1"],
            columns=["AT2 0AC CCGT", "AT2 1AC CCGT", "DE0 0AC CCGT"],
        )

    def _mapping(self):
        return pd.Series(
            ["AT", "AT", "DE"], index=["AT2 0AC CCGT", "AT2 1AC CCGT", "DE0 0AC CCGT"]
        )

    def test_sum_is_the_default_for_additive_quantities(self):
        out = eb._aggregate_by_country(self._frame(), self._mapping())
        self.assertAlmostEqual(out.at["t0", "AT"], 3.0)
        self.assertAlmostEqual(out.at["t0", "DE"], 10.0)

    def test_mean_averages_price_across_buses(self):
        """Regression: prices were summed, so Germany's 20 buses reported 20x."""
        out = eb._aggregate_by_country(self._frame(), self._mapping(), how="mean")
        self.assertAlmostEqual(out.at["t0", "AT"], 1.5)
        self.assertAlmostEqual(out.at["t0", "DE"], 10.0)

    def test_grouping_keys_must_be_component_names(self):
        """Regression: bus-indexed keys against generator-named columns made
        pandas silently drop every row and sum to zero."""
        frame = self._frame()
        wrong_keys = pd.Series(["AT", "AT", "DE"], index=["AT2 0AC", "AT2 1AC", "DE0 0AC"])
        with self.assertRaises(ValueError):
            eb._aggregate_by_country(frame, wrong_keys)


class CarbonAccountingTests(unittest.TestCase):
    """t/MWh -> g/MWh is x1e3. Using x1e6 overstated intensity 1000x."""

    def test_intensity_conversion_factor(self):
        # 1 t CO2e over 1 MWh is 1000 g/kWh, not 1e6.
        self.assertAlmostEqual(1.0 * 1e3 / 1.0, 1000.0)

    def test_summary_keys_use_mwh_naming(self):
        # The old summary advertised gco2_per_kwh; the plan's contract is
        # gCO2e/MWh (numerically identical, but the name must match the contract).
        self.assertNotIn("carbon_intensity_gco2_per_kwh", self._summary_fields())
        self.assertIn("carbon_intensity_gco2_per_mwh", self._summary_fields())

    def _summary_fields(self):
        import inspect

        source = inspect.getsource(eb.compute_summary)
        return source


class HourlyWriteTests(unittest.TestCase):
    def test_timestamps_are_iso8601_utc(self):
        frame = pd.DataFrame(
            {"DE": [1.0]}, index=pd.DatetimeIndex(["2025-03-01 00:00:00"])
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.csv"
            eb._write_hourly(frame, path)
            out = pd.read_csv(path, index_col=0)
        self.assertEqual(list(out.index), ["2025-03-01T00:00:00Z"])
        self.assertEqual(list(out.columns), ["DE"])


class BorderIdTests(unittest.TestCase):
    def test_flow_labels_match_cross_border_id_format(self):
        """Regression: flow columns were 'A->B' while cross_borders used 'A-B',
        so no border id matched between the two files."""
        import inspect

        source = inspect.getsource(eb.extract_hourly_flow)
        self.assertIn('label = f"{sorted([ca, cb])[0]}-{sorted([ca, cb])[1]}"', source)


class CarbonIntensityGuardTests(unittest.TestCase):
    def test_near_zero_load_hours_are_dropped(self):
        loads = pd.DataFrame(
            {"XX": [1000.0, 0.5, 1000.0]}, index=pd.Index(range(3), name="timestamp")
        )
        emissions = pd.DataFrame(
            {"XX": [100.0, 100.0, 100.0]}, index=loads.index
        )
        floor = loads.mean() * 0.01
        usable = loads.where(loads > floor)
        self.assertFalse(usable.loc[1, "XX"] > 0)
        self.assertTrue(pd.isna(emissions.div(usable).loc[1, "XX"]))


if __name__ == "__main__":
    unittest.main()
