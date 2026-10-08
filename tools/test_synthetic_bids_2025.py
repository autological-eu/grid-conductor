import unittest
import numpy as np
from synthetic_bids_2025 import clear

class ClearingTests(unittest.TestCase):
    def test_negative_offers_partial_acceptance_and_objective(self):
        price,cost,order,accepted=clear([10,20,30],[100,-5,50],25)
        self.assertEqual(price,50);self.assertEqual(cost,150)
        self.assertAlmostEqual(accepted.sum(),25)
    def test_scarcity_is_explicit(self):
        price,cost,_,_=clear([10,20],[50,10000],15)
        self.assertEqual(price,10000);self.assertEqual(cost,50500)
        with self.assertRaises(ValueError):clear([10],[50],15)
    def test_missing_and_negative_capacity_rejected(self):
        for capacity in [[float('nan')],[-1]]:
            with self.assertRaises(ValueError):clear(capacity,[50],10)

if __name__=='__main__':unittest.main()
