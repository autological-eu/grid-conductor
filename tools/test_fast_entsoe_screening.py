"""Unit tests for the ENTSO-E fast screening ladder (fast_entsoe_screening)."""
import unittest

import numpy as np

import fast_entsoe_screening as tool


def fixture():
    """Small real bank slice: AT/DE/CH/NL/FR-ish zones, 4 borders, 24 samples."""
    qh = 24
    s3 = lambda *v: v * qh
    zones = ["AT", "DE", "CH", "NL", "FR"]
    caps = {"AT>DE": s3(2200), "DE>AT": s3(2200), "DE>CH": s3(3000),
            "CH>DE": s3(2500), "NL>DE": s3(5000), "DE>NL": s3(5000),
            "FR>DE": s3(4000), "DE>FR": s3(4800)}
    flows = {"AT>DE": s3(1100), "DE>AT": s3(1200), "DE>CH": s3(1500),
             "CH>DE": s3(1700), "NL>DE": s3(1800), "DE>NL": s3(1400),
             "FR>DE": s3(2100), "DE>FR": s3(1800)}
    prices = {"AT": [9 * i for i in range(qh)], "DE": [8 * i for i in range(qh)],
              "CH": [7 * i for i in range(qh)], "NL": [10 * i for i in range(qh)],
              "FR": [12 * i for i in range(qh)]}
    return dict(schema_version=2, month="2026-08",
                interior_borders=[["AT", "DE"], ["DE", "CH"], ["NL", "DE"], ["FR", "DE"]],
                exterior_borders=[], zone_domains={z: dict(price=z) for z in zones},
                prices=prices, flows_mw=flows, caps_mw=caps)


def make_bank(month, qh, offset=0):
    zones = ["A", "B"]
    s3 = lambda *v: ((v * qh) * 3)[offset:offset + qh]
    b = dict(schema_version=2, month=month,
             interior_borders=[["A", "B"]], exterior_borders=[],
             zone_domains={z: dict(price=z) for z in zones},
             prices={"A": s3(20), "B": s3(30)},
             flows_mw={"A>B": s3(450), "B>A": s3(0)}, caps_mw={"A>B": s3(1000), "B>A": s3(1000)},
             caps_synthetic=[])
    return b


class FastEntsoeScreeningTests(unittest.TestCase):
    def test_realized_rent_and_opportunity(self):
        bank = make_bank("2026-08", 24)
        # B prices +10 on top of the 30 baseline -> pa=20, pb=40, spread=20
        bank["prices"]["B"] = [v + 10 for v in bank["prices"]["B"]]
        bank["flows_mw"]["A>B"] = [300] * 24
        bank["caps_mw"]["A>B"] = [1000] * 24
        rows = [r for r in tool.screening([bank]) if r["border"] == "A>B"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        h = tool.HOURS_PER_SAMPLE
        # realized = 1e-6 * 0.25 * sum_t F_AB * (P_B-P_A) = 300*20*24*0.25*1e-6
        self.assertAlmostEqual(row["realized_rent_meur_month"], 300 * 20 * 24 * h / 1e6, places=6)
        self.assertAlmostEqual(row["positive_rent_meur_month"], 300 * 20 * 24 * h / 1e6, places=6)
        # opportunity_dc = 1e-6 * 0.25 * sum_t max(0,P_B-P_A) * dc
        self.assertAlmostEqual(row["opportunity_meur_month"][500], 20 * 24 * 500 * h / 1e6, places=6)
        self.assertAlmostEqual(row["opportunity_meur_month"][1000], 20 * 24 * 1000 * h / 1e6, places=6)
        self.assertEqual(row["congested_quarters"], 24)  # spread 20 > 5 EUR/MWh everywhere

    def test_both_directions_emitted(self):
        bank = make_bank("2026-08", 24)
        rows = tool.screening([bank])
        self.assertEqual({r["border"] for r in rows}, {"A>B", "B>A"})

    def test_reverse_congested_direction_has_opportunity(self):
        bank = make_bank("2026-08", 24)
        # Congestion runs B>A instead: A prices above B, flow from B into A.
        bank["prices"]["A"] = [50] * 24
        bank["prices"]["B"] = [30] * 24
        bank["flows_mw"]["A>B"] = [0] * 24
        bank["flows_mw"]["B>A"] = [400] * 24
        rows = tool.screening([bank])
        fwd = {r["border"]: r for r in rows}
        h = tool.HOURS_PER_SAMPLE
        self.assertAlmostEqual(fwd["A>B"]["opportunity_meur_month"][1000], 0.0, places=6)
        self.assertAlmostEqual(fwd["B>A"]["opportunity_meur_month"][1000], 20 * 24 * 1000 * h / 1e6, places=6)
        self.assertAlmostEqual(fwd["B>A"]["realized_rent_meur_month"], 400 * 20 * 24 * h / 1e6, places=6)

    def test_negative_slope_clamps_to_zero(self):
        bank = make_bank("2026-08", 24)
        # Inflow into A moves with flow A>B; make price fall as flow rises -> raw slope < 0.
        bank["prices"]["A"] = [50 - 1.5 * i for i in range(24)]
        bank["flows_mw"]["A>B"] = [100 + 2 * i for i in range(24)]
        bank["flows_mw"]["B>A"] = [0] * 24
        rows = [r for r in tool.screening([bank]) if r["border"] == "A>B"]
        row = rows[0]
        self.assertIsNotNone(row["slope_raw_a"])
        self.assertLess(row["slope_raw_a"], 0)
        self.assertEqual(row["slope_a"], 0)

    def test_raw_positive_slope_kept(self):
        raw = tool.price_response_slope(
            [20 + 2 * i for i in range(30)], [100 + 3 * i for i in range(30)])
        self.assertIsNotNone(raw)
        self.assertGreater(raw, 0)
        self.assertEqual(tool.effective_slope(raw), raw)

    def test_directed_row_slopes_follow_the_row_orientation(self):
        bank = make_bank("2026-08", 24)
        # A: inflow rises with flow A>B (net += +flow) -> price rising => slope_A > 0.
        # B: inflow falls with flow A>B (net += -flow) -> price rising => slope_B < 0.
        bank["prices"]["A"] = [10 + i for i in range(24)]
        bank["prices"]["B"] = [50 + 2 * i for i in range(24)]
        bank["flows_mw"]["A>B"] = [100 + 2 * i for i in range(24)]
        bank["flows_mw"]["B>A"] = [0] * 24
        rows = {r["border"]: r for r in tool.screening([bank])}
        slopes = tool.zone_slopes(bank)
        self.assertGreater(slopes["A"], 0)
        self.assertLess(slopes["B"], 0)
        # A>B carries A's slope as slope_a, B's as slope_b; B>A swaps them.
        for border, fwd, rev in (("A>B", "A", "B"), ("B>A", "B", "A")):
            row = rows[border]
            self.assertEqual(row["slope_a"], tool.effective_slope(slopes[fwd]))
            self.assertEqual(row["slope_b"], tool.effective_slope(slopes[rev]))
            self.assertEqual(row["slope_raw_a"], slopes[fwd])
            self.assertEqual(row["slope_raw_b"], slopes[rev])


if __name__ == "__main__":
    unittest.main()