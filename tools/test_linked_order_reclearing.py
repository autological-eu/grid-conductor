import itertools
import unittest
from unittest.mock import patch
import numpy as np
from linked_profile_orders import compile_book,optimize,price_feasibility
from linked_order_reclearing import reclear
from test_linked_profile_orders import book,order


class Reclearing(unittest.TestCase):
    def test_rejects_paradoxical_acceptance_and_preserves_original_bound(self):
        lp=compile_book(book([100.]),[order('block',[100],40)])
        result=reclear(lp)
        self.assertEqual(result['status'],'price_checked_incumbent')
        self.assertEqual(len(result['history']),2)
        self.assertAlmostEqual(result['result']['ratios'][0],0,places=7)
        self.assertAlmostEqual(result['initial_allocation_lower_bound_eur'],4000,places=4)
        self.assertAlmostEqual(result['incumbent_eur'],5000,places=4)
        self.assertAlmostEqual(result['conservative_cost_gap_eur'],1000,places=4)
        self.assertFalse(result['global_optimality_claim'])

    def test_profitable_children_can_rescue_losing_parent(self):
        lp=compile_book(book([1.,10.],capacity=[[0,20],[0,20]]),[order('p',[1,0],120),order('c',[0,10],50,parents=['p'])])
        result=reclear(lp);self.assertEqual(len(result['history']),1)
        np.testing.assert_allclose(result['result']['ratios'],[1,1],atol=1e-7)

    def test_small_book_matches_exhaustive_price_checked_oracle(self):
        orders=[order('bad',[100],40,exclusive='g'),order('good',[40],10,exclusive='g')]
        lp=compile_book(book([100.]),orders);expected=[]
        for values in itertools.product([0,1],repeat=len(lp['integers'])):
            state=np.zeros(len(lp['c']));state[lp['integers']]=values
            try:
                x,_,info=optimize(lp,fixed=state);y,_=price_feasibility(lp,x,10)
                if y is not None:expected.append(info['objective_eur'])
            except RuntimeError:pass
        result=reclear(lp)
        self.assertEqual(result['status'],'price_checked_incumbent');self.assertAlmostEqual(result['incumbent_eur'],min(expected),places=4)

    def test_round_limit_returns_no_unverified_market_prices(self):
        lp=compile_book(book([100.]),[order('block',[100],40)])
        result=reclear(lp,max_rounds=1);self.assertIsNone(result['result'])
        self.assertEqual(result['status'],'round_or_wall_budget_exhausted')

    def test_numerical_failure_never_becomes_a_rejection_cut(self):
        lp=compile_book(book([100.]),[order('block',[100],40)])
        with patch('linked_order_reclearing.clear',side_effect=RuntimeError('time limit')):
            result=reclear(lp)
        self.assertEqual(result['status'],'solver_or_certificate_failure');self.assertIsNone(result['result']);self.assertFalse(result['history'])


if __name__=='__main__':unittest.main()
