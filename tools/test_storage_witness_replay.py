import copy
import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import Block,solve_block
from check_storage_dual_bounds import objective_support
from audit_monthly_dispatch_witnesses import replay


class WitnessReplayTests(unittest.TestCase):
    def setUp(self):
        self.block=Block(np.array([2.,5.]),[(0.,10.),(0.,10.)],sparse.csr_matrix([[1.,1.]]),np.array([3.]),sparse.csr_matrix([[1.]]),sparse.csr_matrix([[1.,0.]]),np.array([1.]),sparse.csr_matrix([[0.]]))
        self.state=np.array([.5]);r,_=solve_block(self.block,self.state)
        gradient,intercept=objective_support(self.block,self.state,r)
        self.receipt=dict(cost_eur=r.fun,gradient_eur_per_mwh=gradient.tolist(),dual_intercept_eur=intercept,dual_support_eur=float(intercept+gradient@self.state))
        self.arrays=dict(primal=r.x,equality_duals=r.eqlin.marginals,inequality_duals=r.ineqlin.marginals,lower_marginals=r.lower.marginals,upper_marginals=r.upper.marginals)
    def test_replays_feasibility_cost_and_affine_support(self):
        result=replay(self.block,self.state,self.arrays,self.receipt)
        self.assertEqual(result['cost_eur'],self.receipt['cost_eur'])
        self.assertLessEqual(result['max_equality_residual'],1e-7)
    def test_invalid_primal_and_nonfinite_arrays_rejected(self):
        for value in [2.,float('nan')]:
            arrays=copy.deepcopy(self.arrays);arrays['primal'][0]=value
            with self.assertRaises(ValueError):replay(self.block,self.state,arrays,self.receipt)
    def test_tampered_cost_and_cut_rejected(self):
        for name,value in [('cost_eur',999.),('gradient_eur_per_mwh',[999.]),('dual_support_eur',999.)]:
            receipt=copy.deepcopy(self.receipt);receipt[name]=value
            with self.assertRaises(ValueError):replay(self.block,self.state,self.arrays,receipt)
    def test_dual_shape_drift_rejected(self):
        arrays=copy.deepcopy(self.arrays);arrays['equality_duals']=np.zeros(2)
        with self.assertRaises(ValueError):replay(self.block,self.state,arrays,self.receipt)


if __name__=='__main__':unittest.main()
