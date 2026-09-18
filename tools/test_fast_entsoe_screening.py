"""Unit tests for the ENTSO-E fast screening ladder (fast_entsoe_screening)."""
import copy
import json
import unittest
from pathlib import Path

import fast_entsoe_screening as tool


def fixture():
    """Small real bank slice: AT/DE/CH/NL/FR-ish zones, 4 borders, 24 samples (1 h)."""
    qh = 24
    s3 = lambda *v: v * qh
    zones = ["AT", "DE", "CH", "NL", "FR"]
    caps = {"AT>DE": s3(2200), "DE>AT": s3(2200), "DE>CH": s3(3000),
            "CH>DE": s3(2500), "NL>DE": s3(5000), "DE>NL": s3(5000),
            "FR>DE": s3(4000), "DE>FR": s3(4800)}
    flows = {"AT>DE": s3(1100), "DE>AT": s3(1200), "DE>CH": s3(1500),
             "CH>DE": s3(1700), "NL>DE": s3(1800), "DE>NL": s3(1400),
             "FR>DE": s3(2100), "DE>FR": s3(1800)}
    prices = {"AT": [9*i for i in range(qh)], "DE": [8*i for i in range(qh)],
              "CH": [7*i for i in range(qh)], "NL": [10*i for i in range(qh)],
              "FR": [12*i for i in range(qh)]}
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
             flows_mw={"A>B": s3(450)}, caps_mw={"A>B": s3(1000)},
             caps_synthetic=[])
    return b


class FastEntsoeScreeningTests(unittest.TestCase):
    def test_realized_rent_and_opportunity(self):
        bank = make_bank("2026-08", 24)
        # B prices +10 on top of the 30 baseline -> pa=20, pb=40, spread=20
        bank["prices"]["B"] = [v + 10 for v in bank["prices"]["B"]]
        bank["flows_mw"]["A>B"] = [300] * 24
        bank["caps_mw"]["A>B"] = [1000] * 24
        bank["flows_mw"]["B>A"] = [0] * 24
        bank["caps_mw"]["B>A"] = [1000] * 24
        rows = tool.screening([bank])
        row = rows[0]
        # realized = 1e-6 * sum_t F_AB * (P_B-P_A) = 300*20*24*1e-6
        self.assertAlmostEqual(row["realized_rent_meur_yr"], 300 * 20 * 24 / 1e6, places=6)
        self.assertAlmostEqual(row["positive_rent_meur_yr"], 300 * 20 * 24 / 1e6, places=6)
        # opportunity_dc = 1e-6 * sum_t max(0,P_B-P_A) * dc
        self.assertAlmostEqual(row["opportunity_meur_yr"][500], 20 * 24 * 500 / 1e6, places=6)
        self.assertAlmostEqual(row["opportunity_meur_yr"][1000], 20 * 24 * 1000 / 1e6, places=6)
        self.assertEqual(row["congested_hours"], 24)  # spread 20 > 5 EUR/MWh everywhere


if __name__ == "__main__":
    unittest.main()
