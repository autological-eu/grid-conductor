import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import Block
from storage_objective_floor import nonnegative_objective_floor


class ObjectiveFloorTests(unittest.TestCase):
    def block(self,cost=1.,coupling=0.,limit=0.):
        return Block(np.array([cost]),[(None,None)],sparse.csr_matrix((0,1)),np.zeros(0),sparse.csr_matrix((0,1)),sparse.csr_matrix([[-1.]]),np.array([limit]),sparse.csr_matrix([[coupling]]))
    def test_source_nonnegative_constraint_establishes_zero_floor(self):
        self.assertEqual(nonnegative_objective_floor(self.block()),0.)
    def test_boundary_dependent_lower_bound_cannot_establish_global_floor(self):
        with self.assertRaises(ValueError):nonnegative_objective_floor(self.block(coupling=1.))
    def test_negative_cost_and_negative_lower_bound_rejected(self):
        with self.assertRaises(ValueError):nonnegative_objective_floor(self.block(cost=-1.))
        with self.assertRaises(ValueError):nonnegative_objective_floor(self.block(limit=1.))
    def test_uncosted_free_variables_do_not_block_zero_floor(self):
        self.assertEqual(nonnegative_objective_floor(self.block(cost=0.,coupling=1.)),0.)


if __name__=='__main__':unittest.main()
