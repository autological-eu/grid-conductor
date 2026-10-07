import unittest
import json
import tempfile
from pathlib import Path
from audit_smard_2025_gas import aggregate, cached, BASE, START, END, HOUR
from monthly_dispatch import digest


class SMARDGasTests(unittest.TestCase):
    def test_cached_source_identity_and_bytes_are_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'index_hour.json'
            path.write_text('{"timestamps": []}')
            receipt = path.with_suffix('.json.receipt.json')
            receipt.write_text(json.dumps(dict(source_url=BASE+path.name, sha256=digest(path), bytes=path.stat().st_size)))
            self.assertEqual(cached(Path(folder), path.name, False)[0], {'timestamps': []})
            path.write_text('{"timestamps": [0]}')
            with self.assertRaises(ValueError):
                cached(Path(folder), path.name, False)

    def test_exact_utc_year_and_interval_energy(self):
        rows = [[timestamp, 2.] for timestamp in range(START-HOUR, END+HOUR, HOUR)]
        result = aggregate(rows)
        self.assertEqual(result['observed_hours'], 8760)
        self.assertEqual(result['complete_reported_energy_mwh'], 17520.)
        self.assertEqual(result['monthly'][0]['expected_hours'], 744)
        self.assertEqual(result['monthly'][2]['expected_hours'], 744)
        self.assertEqual(result['monthly'][9]['expected_hours'], 744)

    def test_missing_null_duplicate_and_invalid_values(self):
        result = aggregate([[START, None], [START+HOUR, 0.]])
        self.assertEqual(result['observed_hours'], 1)
        self.assertIsNone(result['complete_reported_energy_mwh'])
        for rows in [[[START, 1.], [START, 1.]], [[START+1, 1.]],
                     [[START, float('nan')]], [[START, -1.]], [[START, True]]]:
            with self.assertRaises(ValueError):
                aggregate(rows)


if __name__ == '__main__':
    unittest.main()
