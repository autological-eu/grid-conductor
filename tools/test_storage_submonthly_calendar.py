import unittest
import tempfile
import json
from pathlib import Path
from prepare_submonthly_calendar import verify_block
from prepare_submonthly_blocks import partitions
from monthly_dispatch import digest,save


class CalendarPreparationTests(unittest.TestCase):
    def fixture(self,root):
        row=partitions(2025,168)[0]
        (root/'block.npz').write_bytes(b'fingerprint fixture')
        save(root/'status.json',dict(status='prepared_requires_equivalence_audit'))
        tools=Path(__file__).parent
        data=dict(**row,input_sha256='source',block_count=59,year=2025,storage_ids=['S'],shared_variables=60,
                  block_sha256=digest(root/'block.npz'),producer_sha256=digest(tools/'prepare_submonthly_blocks.py'),
                  dependencies={name:digest(tools/name) for name in ['pypsa_storage_blocks.py','prepare_annual_coordination.py','disk_storage_blocks.py']})
        save(root/'block.json',data)
        return row,data

    def test_changed_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);row,data=self.fixture(root)
            verify_block(root,row,'source',59)
            (root/'block.npz').write_bytes(b'changed')
            with self.assertRaises(ValueError):verify_block(root,row,'source',59)

    def test_calendar_source_and_dependency_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);row,data=self.fixture(root)
            with self.assertRaises(ValueError):verify_block(root,row,'other source',59)
            for change in [dict(index=1),dict(shared_variables=59),dict(dependencies={})]:
                save(root/'block.json',dict(data,**change))
                with self.assertRaises(ValueError):verify_block(root,row,'source',59)
