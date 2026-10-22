import datetime as dt
import unittest
import numpy as np
from january_supply_balance_2025 import interval_indices,annual_capacity

class SourceContracts(unittest.TestCase):
    def test_hour_ending_moves_to_matching_hour_start_across_midnight(self):
        clock=np.arange(np.datetime64('2025-01-01T22','h'),np.datetime64('2025-01-02T03','h'))
        np.testing.assert_array_equal(interval_indices(clock,clock[:-1]),[1,2,3,4])
    def test_year_endpoint_cannot_be_wrapped_or_filled(self):
        with self.assertRaisesRegex(ValueError,'endpoint'):
            interval_indices(['2025-12-31T23'],['2025-12-31T23'])
    def test_reported_year_uses_source_timezone(self):
        timestamp=int(dt.datetime(2024,12,31,23,tzinfo=dt.timezone.utc).timestamp()*1000)
        self.assertEqual(annual_capacity([[timestamp,15951]],2025),15951)
        with self.assertRaises(ValueError):annual_capacity([[timestamp,15951]],2024)
    def test_missing_or_duplicate_capacity_year_is_rejected(self):
        with self.assertRaises(ValueError):annual_capacity([],2025)
        t=int(dt.datetime(2025,1,1,tzinfo=dt.timezone.utc).timestamp()*1000)
        with self.assertRaises(ValueError):annual_capacity([[t,10],[t+1000,20]],2025)

if __name__=='__main__':unittest.main()
