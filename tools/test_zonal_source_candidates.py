import json
from pathlib import Path
import tempfile
import unittest
from collect_zonal_source_candidates import inspect, collect


class SourceTests(unittest.TestCase):
    def test_no_2025_is_not_invented(self):
        report = inspect('owid', b'country,year\nFrance,2024\n')
        self.assertEqual(report['rows_2025'], 0)

    def test_monthly_dates_preserved_not_hourly_coverage(self):
        report = inspect('ember-monthly', b'Area,Date\nFrance,2025-01-01\nFrance,2025-02-01\n')
        self.assertEqual(report['dates_2025'], ['2025-01-01', '2025-02-01'])
        self.assertEqual(report['areas_2025'], 1)
        with self.assertRaises(ValueError): inspect('ember-monthly', b'wrong\n2025\n')

    def test_changed_cache_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); folder = root/'owid'; folder.mkdir()
            (folder/'provider-data').write_bytes(b'changed')
            (folder/'receipt.json').write_text(json.dumps(dict(source_url='wrong', sha256='wrong')))
            with self.assertRaises(ValueError): collect('owid', root)


if __name__ == '__main__': unittest.main()
