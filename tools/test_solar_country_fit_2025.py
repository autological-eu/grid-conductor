"""Regression contract: no intercept, no missing-data fill, no hidden clipping."""
import unittest
import numpy as np
from solar_country_fit_2025 import monthly_factor


class FitContracts(unittest.TestCase):
    def test_known_scalar_and_zero_intercept(self):
        x=np.arange(1.,13);r=monthly_factor(x,.8*x)
        self.assertEqual(r['status'],'fitted');self.assertAlmostEqual(r['factor'],.8)
        # Offset data does not introduce a fitted intercept.
        r=monthly_factor(x,.5*x+1)
        self.assertAlmostEqual(r['raw_factor'],float(x@(.5*x+1)/(x@x)))

    def test_missing_or_zero_data_never_filled(self):
        x=np.ones(12);y=x.copy();y[3]=np.nan
        self.assertEqual(monthly_factor(x,y)['factor'],1.)
        self.assertIsNone(monthly_factor(x,np.zeros(12))['raw_factor'])

    def test_extreme_or_upward_fit_is_reported_not_clipped(self):
        for factor in [.1,1.1]:
            r=monthly_factor(np.ones(12),np.full(12,factor))
            self.assertEqual(r['factor'],1.);self.assertAlmostEqual(r['raw_factor'],factor)
            self.assertEqual(r['status'],'outside_reduction_guard_unchanged')


if __name__=='__main__':unittest.main()
