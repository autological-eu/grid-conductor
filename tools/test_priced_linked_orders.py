import unittest
from unittest.mock import patch
from linked_profile_orders import compile_book
from priced_linked_orders import clear,reclear
from test_linked_profile_orders import book,order


class ActualPriceCertificates(unittest.TestCase):
    def test_already_valid_duals_need_no_auxiliary_search(self):
        # The empty order book has no economic acceptance conditions.
        empty=compile_book(book([100.]),[])
        with patch('priced_linked_orders.price_feasibility',side_effect=AssertionError('unneeded search')):
            result=clear(empty)
        self.assertTrue(result['conditional_surplus_passed']);self.assertEqual(result['price_search']['status'],'fixed_integer_duals_verified')

    def test_bad_block_still_requires_reclearing(self):
        result=reclear(compile_book(book([100.]),[order('bad',[100],40)]))
        self.assertEqual(result['status'],'price_checked_incumbent');self.assertEqual(len(result['history']),2)
        self.assertAlmostEqual(result['conservative_cost_gap_eur'],1000,places=4)

    def test_preserve_parent_rescue(self):
        result=reclear(compile_book(book([1.,10.],capacity=[[0,20],[0,20]]),[order('p',[1,0],120),order('c',[0,10],50,parents=['p'])]))
        self.assertEqual(result['status'],'price_checked_incumbent');self.assertEqual(len(result['history']),1)


if __name__=='__main__':unittest.main()
