import json,tempfile,unittest
from pathlib import Path
from monthly_dispatch import digest
from prepare_submonthly_warm_calendar import verify


class RestrictedCalendarTests(unittest.TestCase):
    def fixture(self,folder):
        (folder/'boundary-state.npz').write_bytes(b'inventory')
        (folder/'00-primal.npz').write_bytes(b'primal')
        (folder/'status.json').write_text(json.dumps(dict(status='restricted_witness_complete')))
        record=dict(status='restricted_monthly_primal_verified',month=1,input_sha256='source',
                    producer_sha256=digest(Path(__file__).with_name('prepare_submonthly_warm_witness.py')),
                    dependencies={'submonthly_primal_mapping.py':digest(Path(__file__).with_name('submonthly_primal_mapping.py'))},
                    boundary_state_sha256=digest(folder/'boundary-state.npz'),
                    rows=[dict(index=0,primal_sha256=digest(folder/'00-primal.npz'))])
        (folder/'verified.json').write_text(json.dumps(record))

    def test_changed_witness_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);self.fixture(folder);verify(folder,1,'source')
            (folder/'00-primal.npz').write_bytes(b'changed')
            with self.assertRaises(ValueError):verify(folder,1,'source')

    def test_status_source_and_month_must_match(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);self.fixture(folder)
            for month,source in [(2,'source'),(1,'wrong')]:
                with self.assertRaises(ValueError):verify(folder,month,source)
            (folder/'status.json').write_text(json.dumps(dict(status='still_running')))
            with self.assertRaises(ValueError):verify(folder,1,'source')
