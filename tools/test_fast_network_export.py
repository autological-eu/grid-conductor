"""Fail-closed export checks; run with the existing offline SciPy environment."""
import json
from pathlib import Path
import tempfile
import unittest
from export_fast_network import export

ROOT = Path(__file__).resolve().parents[1]

class FastNetworkExportTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT/'tests/fixtures/network.json').read_text())
        for key in ['schema_version', 'dataset_id']:
            self.data.pop(key)
        self.temp = tempfile.TemporaryDirectory()
        self.source = Path(self.temp.name)/'input.json'

    def tearDown(self):
        self.temp.cleanup()

    def publish(self):
        self.source.write_text(json.dumps(self.data))
        return export(self.source, 'test-only', ['Explicit analytical fixture'])

    def test_content_hash_and_inputs_preserved(self):
        result = self.publish()
        self.assertEqual(len(result['provenance']['source_sha256']), 64)
        self.assertEqual(result['generators'], self.data['generators'])
        self.assertEqual(result['schema_version'], 1)

    def test_unknown_physics_not_dropped(self):
        self.data['generators'][0]['unit_commitment'] = True
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            self.publish()

    def test_missing_availability_not_reconstructed(self):
        del self.data['generators'][0]['max_mw']
        with self.assertRaises(KeyError):
            self.publish()

    def test_incomplete_profile_not_filled(self):
        self.data['generators'][0]['max_mw'].pop()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.publish()

if __name__ == '__main__':
    unittest.main()
