import json
from pathlib import Path
import tempfile
import unittest
from inspect_inventory_processes import inspect, matches_process


class InventoryProcessTests(unittest.TestCase):
    def test_zombie_reused_pid_wrong_root_and_relative_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            process = base/'123'
            process.mkdir()
            (process/'cwd').symlink_to(base, target_is_directory=True)
            (process/'status').write_text('State:\tS (sleeping)\n')
            (process/'cmdline').write_bytes(b'python\0tools/submonthly_inventory_driver.py\0--root\0original\0')
            self.assertTrue(matches_process(process, 'submonthly_inventory_driver.py', '--root', base/'original'))
            self.assertFalse(matches_process(process, 'submonthly_inventory_driver.py', '--root', base/'other'))
            (process/'status').write_text('State:\tZ (zombie)\n')
            self.assertFalse(matches_process(process, 'submonthly_inventory_driver.py', '--root', base/'original'))
            (process/'status').write_text('State:\tS (sleeping)\n')
            (process/'cmdline').write_bytes(b'python\0unrelated.py\0--root\0original\0')
            self.assertFalse(matches_process(process, 'submonthly_inventory_driver.py', '--root', base/'original'))

    def test_stale_executing_receipt_does_not_establish_liveness(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base/'original'
            root.mkdir()
            (root/'driver-status.json').write_text(json.dumps(dict(status='executing', pid=123)))
            proc = base/'proc'
            proc.mkdir()
            report = inspect(root, base/'continuation', proc)
            row = report['processes'][0]
            self.assertEqual(row['live_pids'], [])
            self.assertFalse(row['saved_pid_matches_live_process'])
            self.assertEqual(row['interpretation'], 'no_matching_live_process_receipt_is_not_progress')


if __name__ == '__main__':
    unittest.main()
