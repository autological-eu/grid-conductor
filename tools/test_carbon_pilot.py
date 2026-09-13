import datetime as dt
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from carbon_pilot import calculate, comparison, parse_generation, timestamp

START = timestamp("2026-08-01T00:00Z")
END = START + dt.timedelta(hours=1)


def samples(values):
    return {START + dt.timedelta(minutes=15*i): value for i, value in enumerate(values)}


def document(points, curve="A03", unit="MAW", direction="in", kind="B04"):
    return f'''<GL_MarketDocument xmlns="urn:test"><TimeSeries>
    <businessType>A01</businessType><objectAggregation>A08</objectAggregation>
    <{direction}BiddingZone_Domain.mRID>TEST</{direction}BiddingZone_Domain.mRID>
    <quantity_Measure_Unit.name>{unit}</quantity_Measure_Unit.name>
    <curveType>{curve}</curveType><MktPSRType><psrType>{kind}</psrType></MktPSRType>
    <Period><timeInterval><start>2026-08-01T00:00Z</start><end>2026-08-01T01:00Z</end></timeInterval>
    <resolution>PT15M</resolution>{points}</Period></TimeSeries></GL_MarketDocument>'''


def point(pos, value):
    return f"<Point><position>{pos}</position><quantity>{value}</quantity></Point>"


class CarbonTests(unittest.TestCase):
    def test_energy_weighted_hour_not_average_of_intensities(self):
        row = calculate({"B04": samples([100, 0, 0, 0]), "B19": samples([0, 10, 10, 10])}, "X", START, END)[0]
        self.assertAlmostEqual(row["carbon_intensity"], (100*490 + 30*11)/130)
        self.assertEqual(row["primary_generation_mwh"], 32.5)

    def test_missing_quarter_does_not_become_zero(self):
        row = calculate({"B04": samples([100, None, 100, 100])}, "X", START, END)[0]
        self.assertEqual(row["status"], "missing_generation")
        self.assertIsNone(row["sensitivity_low"])

    def test_unknown_fuel_has_no_central_estimate(self):
        row = calculate({"B04": samples([100]*4), "B20": samples([100]*4)}, "X", START, END)[0]
        self.assertIsNone(row["carbon_intensity"])
        self.assertEqual(row["mapped_generation_share"], 0.5)
        self.assertEqual((row["sensitivity_low"], row["sensitivity_high"]), (245, 995))

    def test_storage_not_counted_as_zero_carbon_generation(self):
        row = calculate({"B04": samples([100]*4), "B10": samples([100]*4)}, "X", START, END)[0]
        self.assertEqual(row["carbon_intensity"], 490)
        self.assertEqual(row["storage_discharge_mwh"], 100)

    def test_zero_generation_returns_null(self):
        row = calculate({"B04": samples([0]*4)}, "X", START, END)[0]
        self.assertEqual(row["status"], "zero_generation")
        self.assertIsNone(row["carbon_intensity"])

    def test_a03_step_curve_and_a01_gap(self):
        points = point(1, 10) + point(3, 30)
        stepped = parse_generation(document(points), "TEST")["B04"]
        self.assertEqual(list(stepped.values()), [10, 10, 30, 30])
        discrete = parse_generation(document(points, "A01"), "TEST")["B04"]
        self.assertEqual(list(discrete.values()), [10, None, 30, None])

    def test_bad_units_and_conflicting_overlap_rejected(self):
        with self.assertRaises(ValueError):
            parse_generation(document(point(1, 10), unit="MWH"), "TEST")
        xml = document(point(1, 10))
        other = document(point(1, 20)).split("<TimeSeries>")[1].split("</TimeSeries>")[0]
        xml = xml.replace("</GL_MarketDocument>", "<TimeSeries>" + other + "</TimeSeries></GL_MarketDocument>")
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            parse_generation(xml, "TEST")

    def test_consumption_excluded(self):
        with self.assertRaisesRegex(ValueError, "No production"):
            parse_generation(document(point(1, 10), direction="out"), "TEST")

    def test_coarser_resolutions_and_leading_gap(self):
        for resolution in ["PT30M", "PT60M"]:
            xml = document(point(1, 80)).replace("PT15M", resolution)
            data = parse_generation(xml, "TEST")
            self.assertEqual(list(data["B04"].values()), [80]*4)
        data = parse_generation(document(point(3, 80)), "TEST")
        self.assertEqual(list(data["B04"].values()), [None, None, 80, 80])

    def test_negative_invalidates_and_utc_window_clips(self):
        data = parse_generation(document(point(1, -1)), "TEST")
        self.assertTrue(all(v is None for v in data["B04"].values()))
        rows = calculate({"B04": samples([10]*8)}, "X", START, END)
        self.assertEqual(len(rows), 1)
        self.assertEqual(timestamp("2026-08-01T02:00+02:00"), START)

    def test_benchmark_join_is_by_zone_and_hour(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.sqlite"
            with closing(sqlite3.connect(path)) as db:
                db.execute("CREATE TABLE observations(zone,metric,start,value,estimated)")
                db.executemany("INSERT INTO observations VALUES(?,?,?,?,?)", [
                    ("X", "carbon", "2026-08-01T00:00:00Z", 200, 1),
                    ("Y", "carbon", "2026-08-01T00:00:00Z", 900, 0),
                    ("X", "price", "2026-08-01T00:00:00Z", 40, 0)])
                db.commit()
            result = comparison(calculate({"B04": samples([100]*4)}, "X", START, END), path)["X"]
            self.assertEqual(result["electricity_maps_mean"], 200)
            self.assertEqual(result["matched_hours"], 1)
            self.assertEqual(result["estimated_benchmark_hours"], 1)


if __name__ == "__main__":
    unittest.main()
