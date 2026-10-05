import json,tempfile,unittest
from pathlib import Path
from submonthly_inventory_driver import block_action


class DriverActionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)/'block'

    def put(self,name,value):
        self.folder.mkdir(exist_ok=True);(self.folder/name).write_text(json.dumps(value))

    def test_new_block_can_solve(self):self.assertEqual(block_action(self.folder),'solve')

    def test_stale_running_receipt_blocks_restart(self):
        self.put('status.json',dict(status='solving_conditional_submonthly_candidate',pid=123))
        self.assertEqual(block_action(self.folder),'blocked')

    def test_resource_failure_blocks_identical_retry(self):
        self.put('status.json',dict(status='stopped_memory_guard'))
        self.assertEqual(block_action(self.folder),'blocked')

    def test_native_infeasible_requires_phase_one(self):
        self.put('unresolved.json',dict(status='native_reported_infeasible_no_verified_cut'))
        self.assertEqual(block_action(self.folder),'infeasible')

    def test_success_requires_independent_replay(self):
        self.put('verified.json',dict(status='conditional_submonthly_candidate_verified'))
        self.assertEqual(block_action(self.folder),'replay')
        self.put('independent-replay.json',dict(status='independently_replayed_submonthly_economic_witness'))
        self.assertEqual(block_action(self.folder),'complete')


if __name__=='__main__':unittest.main()
