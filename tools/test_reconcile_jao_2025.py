import unittest
from reconcile_jao_2025 import hull

class ReconciliationTests(unittest.TestCase):
    def test_direct_domain_and_lta_extension(self):
        rows=[dict(ptdf={'A':.5,'B':-.5},ram_mw=50)]
        direct=hull(rows,{'A':40,'B':-40},{'border_A_B':100})
        self.assertAlmostEqual(direct['lta_weight'],0)
        extended=hull(rows,{'A':75,'B':-75},{'border_A_B':100})
        self.assertAlmostEqual(extended['lta_weight'],.5)
        self.assertLessEqual(extended['maximum_equality_residual_mw'],1e-6)
        failed=hull(rows,{'A':101,'B':-101},{'border_A_B':100})
        self.assertEqual(failed['status'],'hypothesis_infeasible')

    def test_unmapped_capacity_and_missing_position_rejected(self):
        rows=[dict(ptdf={'A':.5,'B':-.5},ram_mw=50)]
        with self.assertRaisesRegex(ValueError,'Missing positions'):
            hull(rows,{'A':0},{})
        with self.assertRaisesRegex(ValueError,'Unmapped positive'):
            hull(rows,{'A':0,'B':0},{'border_A_C':1})

if __name__=='__main__':unittest.main()
