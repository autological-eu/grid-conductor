import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import Block
from audit_submonthly_warm_calendar import merge_boundaries,primal_checks


class AnnualRestrictedReplayTests(unittest.TestCase):
    def test_boundaries_preserve_chronology_and_reject_gaps_or_conflicts(self):
        pieces=[([0,1],[[2.],[3.]]),([1,2],[[3.],[2.]])]
        np.testing.assert_array_equal(merge_boundaries(pieces,2,1),[[2.],[3.],[2.]])
        for bad in [[([0,1],[[2.],[3.]])],pieces[:1]+[([1,2],[[4.],[2.]])], [([0,0,2],[[2.],[3.],[2.]])], [([-1,0,2],[[2.],[3.],[2.]])]]:
            with self.assertRaises(ValueError):merge_boundaries(bad,2,1)

    def test_replay_checks_global_state_and_variable_bounds(self):
        block=Block(np.array([10.]),[(0.,3.)],sparse.csr_matrix([[1.]]),np.array([0.]),
                    sparse.csr_matrix([[1.,-1.]]),sparse.csr_matrix([[1.]]),np.array([2.]),sparse.csr_matrix((1,2)))
        self.assertEqual(primal_checks(block,np.array([1.,2.]),np.array([1.]))['cost_eur'],10.)
        for state,x in [(np.array([1.,3.]),np.array([1.])),(np.array([0.,4.]),np.array([4.])),(np.array([1.,2.]),np.array([np.nan]))]:
            with self.assertRaises(ValueError):primal_checks(block,state,x)
