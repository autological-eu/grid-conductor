"""Partial and rejected evidence must not become annual feasible results."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from summarize_inventory_search import summarize


class SummaryTests(unittest.TestCase):
    def test_changed_actual_network_is_rejected_before_evidence(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with patch('summarize_inventory_search.read', return_value={'input_sha256': 'original'}), \
                    patch('summarize_inventory_search.digest', return_value='changed'), \
                    patch('summarize_inventory_search.source_signature') as signature:
                with self.assertRaisesRegex(ValueError, 'Actual network differs'):
                    summarize(root, root, root)
                signature.assert_not_called()

    def test_partial_lower_support_without_annual_upper(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            folder = root / 'candidate-001'
            folder.mkdir()
            (folder / 'master.dual-replay.json').touch()
            with patch('summarize_inventory_search.read', return_value={'input_sha256': 'source'}), \
                    patch('summarize_inventory_search.digest', return_value='source'), \
                    patch('summarize_inventory_search.source_signature'), \
                    patch('summarize_inventory_search.verify_master', return_value=10), \
                    patch('summarize_inventory_search.verify_annual') as annual:
                result = summarize(root, root, root)
                self.assertIsNone(result['best_feasible'])
                self.assertIsNone(result['numerical_gap_percent'])
                annual.assert_not_called()

    def test_failed_annual_verification_is_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            folder = root / 'candidate-001'
            folder.mkdir()
            (folder / 'master.dual-replay.json').touch()
            (folder / 'annual-replay.json').touch()
            with patch('summarize_inventory_search.read', return_value={'input_sha256': 'source'}), \
                    patch('summarize_inventory_search.digest', return_value='source'), \
                    patch('summarize_inventory_search.source_signature'), \
                    patch('summarize_inventory_search.verify_master', return_value=10), \
                    patch('summarize_inventory_search.verify_annual', side_effect=ValueError('Changed witness')):
                with self.assertRaisesRegex(ValueError, 'Changed witness'):
                    summarize(root, root, root)


if __name__ == '__main__':
    unittest.main()
