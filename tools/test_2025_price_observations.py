import unittest
import json
import tempfile
from pathlib import Path
from audit_2025_price_observations import summarize, audit


class ObservationTests(unittest.TestCase):
    def test_months_use_exact_utc_calendar_and_keep_gaps(self):
        values=[10.]*8760;values[744]=None
        report=summarize(values,8759)
        self.assertEqual(sum(r['hours'] for r in report['monthly']),8760)
        self.assertEqual(report['monthly'][0]['observed_hours'],744)
        self.assertEqual(report['monthly'][1]['observed_hours'],671)
        self.assertEqual(report['first_missing_hour_index'],744)

    def test_negative_prices_are_valid(self):
        report=summarize([-1.]*8760,8760)
        self.assertEqual(report['mean_price_eur_mwh'],-1.)
        self.assertEqual(report['monthly'][0]['negative_price_hours'],744)

    def test_unknown_period_stays_null(self):
        report=summarize([None]*8760,0)
        self.assertIsNone(report['mean_price_eur_mwh'])
        self.assertIsNone(report['monthly'][0]['mean_price_eur_mwh'])

    def test_invalid_values_and_coverage_fail_closed(self):
        for bad in [True,float('nan'),float('inf'),'10']:
            with self.assertRaises(ValueError):summarize([bad]*8760,8760)
        with self.assertRaises(ValueError):summarize([0.]*8760,8759)
        with self.assertRaises(ValueError):summarize([0.]*8759,8759)

    def test_publication_year_and_fingerprint_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'manifest.json').write_text('{}')
            for coverage in [{'year':2024,'manifest_sha256':'wrong'}, {'year':2025,'manifest_sha256':'wrong'}]:
                (root/'coverage.json').write_text(json.dumps(coverage))
                with self.assertRaises(ValueError):audit(root)
