import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import Block, solve_block
from native_storage_solver import solve_native
from storage_objective_oracle import objective_oracle


class NativeSolverTests(unittest.TestCase):
    def make_block(self, rhs=3.):
        return Block(np.array([2.,5.]),[(0.,10.),(0.,10.)],sparse.csr_matrix([[1.,1.]]),np.array([rhs]),sparse.csr_matrix([[1.]]),sparse.csr_matrix([[1.,0.]]),np.array([1.]),sparse.csr_matrix([[0.]]))
    def test_cost_dual_support_and_coupling_match_independent_solver(self):
        b=self.make_block();state=np.array([.5])
        native=solve_native(b,state)
        reference,_=solve_block(b,state)
        upper,gradient,lower=objective_oracle(b,state,native)
        self.assertAlmostEqual(upper,reference.fun,places=7)
        self.assertAlmostEqual(lower,upper,places=7)
        self.assertAlmostEqual(gradient[0],-5.,places=7)
    def test_infeasible_is_not_an_objective_certificate(self):
        self.assertIsNone(solve_native(self.make_block(-1.),np.array([0.])))
    def test_invalid_time_limit_rejected(self):
        with self.assertRaises(ValueError):solve_native(self.make_block(),np.array([0.]),float('inf'))


if __name__ == '__main__':unittest.main()
