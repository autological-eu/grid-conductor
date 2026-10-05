import unittest
import numpy as np
from scipy import sparse
from grouped_storage_master import solve,cut_rows
from annual_inventory_master import solve_cut_master


class GroupedMasterTests(unittest.TestCase):
    def test_monthly_support_is_sum_not_each_subblock(self):
        result=solve([(0.,0.)],sparse.csr_matrix((0,1)),[],sparse.csr_matrix((0,1)),[],[0.,0.],
                     [([0,1],[0.],20.)],[0.])
        self.assertAlmostEqual(result['master_objective_eur'],20.)
        self.assertAlmostEqual(result['lower_bound_eur'],20.)
        with self.assertRaises(ValueError):cut_rows(1,2,[([0,0],[0.],20.)])

    def test_singleton_layout_equals_existing_master(self):
        bounds=[(0.,10.)];eq=sparse.csr_matrix((0,1));ub=sparse.csr_matrix((0,1));cuts=[(0,[2.],5.),(1,[-1.],10.)]
        old=solve_cut_master(bounds,eq,[],ub,[],[0.,0.],cuts,warm=np.array([3.]))
        new=solve(bounds,eq,[],ub,[],[0.,0.],[([i],g,c) for i,g,c in cuts],[3.])
        self.assertAlmostEqual(new['master_objective_eur'],old['master_objective_eur'])
        self.assertAlmostEqual(new['lower_bound_eur'],old['lower_bound_eur'])

    def test_cyclic_link_and_invalid_anchor_are_not_ignored(self):
        eq=sparse.csr_matrix([[1.,-1.]])
        result=solve([(0.,10.)]*2,eq,[0.],sparse.csr_matrix((0,2)),[],[0.],[([0],[1.,0.],5.)],[2.,2.])
        self.assertAlmostEqual(result['proposal_mwh'][0],result['proposal_mwh'][1])
        with self.assertRaises(ValueError):solve([(0.,10.)]*2,eq,[0.],sparse.csr_matrix((0,2)),[],[0.],[],[2.,3.])
