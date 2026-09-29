import unittest

import numpy as np

from baseline_opportunity import (
    DUAL_EPS,
    build_target,
    kkt_gaps_ok,
    marginal_value_eur_mw,
    rent_meur,
    share_weights,
    spread_stats,
    window_years,
)


class SpreadStatsTests(unittest.TestCase):
    def test_uniform_gap(self):
        stats = spread_stats(np.full((4, 1), 30.0))
        self.assertEqual(stats["mean_abs_spread_eur_mwh"], 30.0)
        self.assertEqual(stats["max_abs_spread_eur_mwh"], 30.0)
        self.assertEqual(stats["spread_hours"], 4)

    def test_hours_count_any_asset(self):
        gap = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 0.0]])
        stats = spread_stats(gap)
        self.assertEqual(stats["spread_hours"], 1)
        self.assertAlmostEqual(stats["mean_abs_spread_eur_mwh"], round(1 / 3, 2))

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            spread_stats(np.empty((0, 0)))


class RentTests(unittest.TestCase):
    def test_gap_times_flow(self):
        self.assertAlmostEqual(rent_meur(np.array([[20.0]]), np.array([[1000.0]])), 20 * 1000 / 1e6)

    def test_hourly_weights(self):
        gap = np.full((2, 1), 10.0)
        flow = np.full((2, 1), 100.0)
        weights = np.array([1.0, 2.0])
        self.assertAlmostEqual(rent_meur(gap, flow, weights), (10 * 100 + 10 * 100 * 2) / 1e6)

    def test_shape_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            rent_meur(np.zeros((2, 1)), np.zeros((2, 2)))


class ShareWeightTests(unittest.TestCase):
    def test_proportional(self):
        np.testing.assert_allclose(share_weights([25, 75]), [0.25, 0.75])

    def test_nonpositive_rejected(self):
        with self.assertRaises(ValueError):
            share_weights([0, 10])

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            share_weights([float("nan"), 10])


class MarginalValueTests(unittest.TestCase):
    def test_shares_weight_the_duals(self):
        mu_u = np.array([[-30.0, -60.0]])
        mu_l = np.zeros_like(mu_u)
        self.assertAlmostEqual(marginal_value_eur_mw(mu_u, mu_l, [0.5, 0.5]), 45.0)
        self.assertAlmostEqual(marginal_value_eur_mw(mu_u, mu_l, [1.0, 0.0]), 30.0)

    def test_weights_scale_hours(self):
        mu_u = np.array([[-10.0], [-10.0]])
        mu_l = np.zeros_like(mu_u)
        self.assertAlmostEqual(marginal_value_eur_mw(mu_u, mu_l, [1.0], [1.0, 2.0]), 30.0)

    def test_both_bounds_accumulate(self):
        mu_u = np.array([[-20.0]])
        mu_l = np.array([[5.0]])
        self.assertAlmostEqual(marginal_value_eur_mw(mu_u, mu_l, [1.0]), 25.0)

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            marginal_value_eur_mw(np.array([[np.nan]]), np.zeros((1, 1)), [1.0])

    def test_pypsa_sign_convention_direction_agnostic(self):
        m1 = marginal_value_eur_mw(np.array([[-40.0]]), np.array([[0.0]]), [1.0])
        m2 = marginal_value_eur_mw(np.array([[0.0]]), np.array([[40.0]]), [1.0])
        self.assertAlmostEqual(m1, 40.0)
        self.assertAlmostEqual(m2, 40.0)


class KktGapTests(unittest.TestCase):
    def test_identity_holds(self):
        ok, residual = kkt_gaps_ok(np.array([[52.0]]), np.array([[52.0]]), np.zeros((1, 1)))
        self.assertTrue(ok)
        self.assertLessEqual(residual, DUAL_EPS)

    def test_opposite_sign_accepted(self):
        ok, _ = kkt_gaps_ok(np.array([[52.0]]), np.zeros((1, 1)), np.array([[52.0]]))
        self.assertTrue(ok)

    def test_mismatch_fails(self):
        ok, _ = kkt_gaps_ok(np.array([[52.0]]), np.array([[1.0]]), np.zeros((1, 1)))
        self.assertFalse(ok)

    def test_lossy_network_residual_accepted(self):
        ok, residual = kkt_gaps_ok(np.array([[52.0]]), np.array([[52.058]]), np.zeros((1, 1)))
        self.assertTrue(ok)
        self.assertGreater(residual, DUAL_EPS)

    def test_large_loss_component_fails(self):
        ok, _ = kkt_gaps_ok(np.array([[52.0]]), np.array([[58.0]]), np.zeros((1, 1)))
        self.assertFalse(ok)

    def test_nonfinite_fails(self):
        ok, _ = kkt_gaps_ok(np.array([[np.nan]]), np.zeros((1, 1)), np.zeros((1, 1)))
        self.assertFalse(ok)


class WindowYearsTests(unittest.TestCase):
    def test_calendar_year(self):
        self.assertEqual(window_years("2025-01-01", "2026-01-01"), 1.0)

    def test_month_window_less_than_one(self):
        self.assertLess(window_years("2025-03-01", "2025-04-01"), 1.0)


class SchemaTests(unittest.TestCase):
    def test_target_row_fields_and_null_opportunity(self):
        border = {
            "id": "FR-IT",
            "a": "FR",
            "b": "IT",
            "assets": [{"component": "Link", "id": "L1", "nominal_mw": 1200}],
        }
        diagnostic = {
            "rent_meur": 114.25,
            "mean_abs_spread_eur_mwh": 19.1,
            "max_abs_spread_eur_mwh": 84.1,
            "spread_hours": 744,
            "congested_hours": 700,
        }
        target = build_target(border, diagnostic, 48.2)
        self.assertEqual(target["status"], "baseline_diagnostic")
        self.assertEqual(target["baseline_rent_meur"], 114.25)
        self.assertEqual(target["marginal_value_eur_mw"], 48.2)
        self.assertIsNone(target["opportunity_meur"])
        self.assertIsNone(target["modelled_opportunity_meur"])
        self.assertIsNone(target["modelled_climate_opportunity_tonnes"])


class MirrorDriftTests(unittest.TestCase):
    def test_bundled_mirror_matches_public_dataset(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        public = root / "public" / "research" / "pypsa-targets.json"
        mirror = root / "src" / "data" / "baseline-targets.json"
        if not public.exists() or not mirror.exists():
            self.skipTest("Baseline dataset not generated yet")
        self.assertEqual(mirror.read_bytes(), public.read_bytes())


if __name__ == "__main__":
    unittest.main()