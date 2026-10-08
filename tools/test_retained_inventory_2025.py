import unittest
import copy
import numpy as np
from audit_retained_inventory_2025 import check_boundaries, check_calendar

class BoundaryTests(unittest.TestCase):
    def test_nonempty_cyclic_state_and_roundoff_preserved(self):
        state=np.array([[4., 0.], [2., -1e-14], [4., 0.]])
        result=check_boundaries(state,np.array([5.,0.]),np.array([True,True]))
        self.assertEqual(result['cyclic_closure_residual_mwh'],0.)
        self.assertEqual(state[0,0],4.)
    def test_broken_closure_capacity_and_missing_state_rejected(self):
        for state in [np.array([[4.],[3.]]),np.array([[6.],[6.]]),np.array([[-1.],[-1.]]),np.array([[np.nan],[np.nan]])]:
            with self.subTest(state=state),self.assertRaises(ValueError):
                check_boundaries(state,np.array([5.]),np.array([True]))

class CalendarTests(unittest.TestCase):
    def test_full_chronological_boundaries(self):
        blocks=[dict(index=0,start_hour=0,end_hour_exclusive=4000,hours=4000),
                dict(index=1,start_hour=4000,end_hour_exclusive=8760,hours=4760)]
        self.assertEqual(check_calendar(blocks),[0,4000,8760])
    def test_gaps_overlaps_reordering_and_truncation_rejected(self):
        base=[dict(index=0,start_hour=0,end_hour_exclusive=4000,hours=4000),
              dict(index=1,start_hour=4000,end_hour_exclusive=8760,hours=4760)]
        for field,value in [('start_hour',4001),('start_hour',3999),('index',0),('hours',1),('end_hour_exclusive',8759)]:
            blocks=copy.deepcopy(base);blocks[1][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):check_calendar(blocks)
        with self.assertRaises(ValueError):check_calendar([])

if __name__=='__main__' :unittest.main()
