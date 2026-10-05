import tempfile
from pathlib import Path
import unittest
from annual_inventory_driver import choose_action,driver_lock,live_jobs

class DriverTests(unittest.TestCase):
 def record(self,**updates):
  row=dict(audit=None,objective=None,phase=None,cut=None);row.update(updates)
  return [(Path('001'),row)]
 def test_live_job_prevents_duplicate_dispatch(self):
  self.assertEqual(choose_action(self.record(),[123],200)[0],'wait')
 def test_solver_failure_requires_diagnostic_not_feasibility_claim(self):
  self.assertEqual(choose_action(self.record(objective=dict(status='failed',month=2)),[],200),('phase_one',(Path('001'),2)))
 def test_phase_failure_selects_separate_probe_once(self):
  self.assertEqual(choose_action(self.record(phase=dict(status='stopped_memory_guard',month=1)),[],200)[0],'probe')
  self.assertEqual(choose_action(self.record(phase=dict(status='failed',month=1),probe=dict(status='failed')),[],200)[0],'blocked')
 def test_replay_precedes_cut_use(self):
  self.assertEqual(choose_action(self.record(phase=dict(status='cut_requires_independent_replay',month=2)),[],200)[0],'replay_cut')
 def test_limit_is_not_convergence(self):
  rows=self.record(cut=dict(status='independently_replayed_numerical_feasibility_cut'))
  self.assertEqual(choose_action(rows,[],1)[0],'limit')
 def test_second_driver_cannot_acquire_lock(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'driver.lock'
   with driver_lock(path):
    with self.assertRaises(BlockingIOError):
     with driver_lock(path):pass
 def test_unrelated_live_process_is_not_a_dispatch_job(self):
  import os
  self.assertNotIn(os.getpid(),live_jobs([Path('.')]))
