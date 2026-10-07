import json
from pathlib import Path
import tempfile
import unittest
from report_hourly_renewables import verified_summary

class ReportReplayTests(unittest.TestCase):
    def test_changed_hourly_file_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'hourly.npz').write_bytes(b'changed evidence')
            (root/'summary.json').write_text(json.dumps(dict(year=2025,hours=8760,hourly_sha256='old hash')))
            with self.assertRaisesRegex(ValueError,'identity'): verified_summary(root)
if __name__=='__main__':unittest.main()
