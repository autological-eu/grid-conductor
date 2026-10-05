import json,tempfile,unittest
from pathlib import Path
from monthly_dispatch import digest
from prepare_submonthly_dual_calendar import verify


class SupportCalendarTests(unittest.TestCase):
    def fixture(self,folder):
        tools=Path(__file__).parent
        record=dict(status='transferred_dual_supports_checked',month=1,input_sha256='source',
          producer_sha256=digest(tools/'audit_submonthly_dual_support.py'),
          dependencies={name:digest(tools/name) for name in ['submonthly_dual_mapping.py','submonthly_primal_mapping.py','native_coordinate_restriction.py','audit_submonthly_warm_calendar.py','check_storage_dual_bounds.py']},rows=[])
        for index in range(5):
            path=folder/f'{index:02d}-dual.npz';path.write_bytes(b'fingerprinted witness')
            record['rows'].append(dict(index=index,dual_sha256=digest(path)))
        (folder/'verified.json').write_text(json.dumps(record))
        replay=dict(status='independently_replayed_transferred_supports',month=1,input_sha256='source',
          producer_receipt_sha256=digest(folder/'verified.json'),replay_tool_sha256=digest(tools/'replay_submonthly_dual_witness.py'),
          dependencies={name:digest(tools/name) for name in ['audit_monthly_dispatch_witnesses.py','check_storage_dual_bounds.py','disk_storage_blocks.py']},rows=[dict(index=i) for i in range(5)])
        (folder/'independent-replay.json').write_text(json.dumps(replay))
        (folder/'status.json').write_text(json.dumps(dict(status='transferred_support_check_complete')))

    def test_changed_duals_and_source_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);self.fixture(folder);verify(folder,1,'source')
            with self.assertRaises(ValueError):verify(folder,1,'wrong')
            (folder/'00-dual.npz').write_bytes(b'changed')
            with self.assertRaises(ValueError):verify(folder,1,'source')

    def test_missing_dependencies_and_unverified_status_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);self.fixture(folder)
            path=folder/'independent-replay.json';record=json.loads(path.read_text());record['dependencies']={};path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):verify(folder,1,'source')
            self.fixture(folder);(folder/'status.json').write_text(json.dumps(dict(status='running')))
            with self.assertRaises(ValueError):verify(folder,1,'source')
