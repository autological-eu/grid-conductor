import unittest
import numpy as np
from residual_demand_audit_2025 import array_stats

class CoverageTests(unittest.TestCase):
    def test_missing_hours_are_not_zero_or_annualised(self):
        r=array_stats(np.array([100.,200.,300.]),np.array([np.nan,210.,np.nan]))
        self.assertEqual(r['known_hours'],1);self.assertEqual(r['available_on_known_hours_twh'],.0002)
        self.assertEqual(r['generated_on_known_hours_twh'],.00021)
    def test_generation_below_availability_is_not_an_excess(self):
        r=array_stats(np.array([100.,200.]),np.array([0.,100.]))
        self.assertEqual(r['excess_generation_twh'],0.);self.assertEqual(r['hours_generated_above_available_1mw'],0)
    def test_threshold_is_strict_and_constant_series_have_no_correlation(self):
        r=array_stats(np.array([100.,100.]),np.array([101.,102.]))
        self.assertEqual(r['hours_generated_above_available_1mw'],1);self.assertIsNone(r['shape_correlation'])
    def test_unavailable_stays_unknown(self):
        self.assertEqual(array_stats(np.array([1.]),np.array([np.nan])),dict(known_hours=0,status='unavailable_not_zero'))

if __name__=='__main__':unittest.main()
