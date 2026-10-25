import unittest
import numpy as np
from dispatch_error_budget_2025 import budget
class Checks(unittest.TestCase):
 def test_disjoint_contributions_with_negative_extremes(self):
  train=np.arange(100).reshape(50,2)-30;truth=np.array([[-500,2000],[0,0],[15,20.]])
  predicted=truth+np.array([[100,-300],[5,10],[-20,30]])
  rows=budget(predicted,truth,train)
  self.assertEqual(sum(x['hours'] for x in rows),truth.size)
  np.testing.assert_allclose(sum(x['contribution'] for x in rows),abs(predicted-truth).mean())
  np.testing.assert_allclose(sum(x['error_share'] for x in rows),1)
 def test_tied_thresholds_and_empty_cohorts(self):
  rows=budget(np.ones((3,2)),np.zeros((3,2)),np.zeros((5,2)))
  self.assertEqual([r['hours'] for r in rows],[0,6,0]);self.assertIsNone(rows[0]['mae'])
if __name__=='__main__':unittest.main()
