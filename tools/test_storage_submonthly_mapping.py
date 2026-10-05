import unittest
import numpy as np
from prepare_submonthly_blocks import partitions
from submonthly_inventory_mapping import boundary_positions,project_state,lift_gradient,month_blocks


class SubmonthlyMappingTests(unittest.TestCase):
    def test_lifted_cut_value_matches_monthly_projection(self):
        rows=partitions(2025,168);state=np.arange(120,dtype=float);gradient=np.arange(26,dtype=float)-13.
        self.assertEqual(lift_gradient(gradient,2,rows)@state,gradient@project_state(state,2,rows))
        self.assertEqual(boundary_positions(rows)[-1],59)
        self.assertEqual(month_blocks(2,rows),[5,6,7,8])
        self.assertEqual(sum(len(month_blocks(m,rows)) for m in range(1,13)),59)

    def test_internal_states_do_not_change_monthly_cut_value(self):
        rows=partitions(2025,168);state=np.zeros(60);state[1]=100.
        self.assertEqual(lift_gradient(np.ones(13),1,rows)@state,0.)
        self.assertTrue(np.array_equal(project_state(state,1,rows),np.zeros(13)))

    def test_tampered_partition_and_dimensions_rejected(self):
        rows=partitions(2025,168);rows[1]['start_hour']+=1
        with self.assertRaises(ValueError):boundary_positions(rows)
        rows=partitions(2025,168)
        with self.assertRaises(ValueError):lift_gradient(np.ones(12),1,rows)
        with self.assertRaises(ValueError):project_state(np.ones(59),1,rows)
        with self.assertRaises(ValueError):month_blocks(13,rows)
