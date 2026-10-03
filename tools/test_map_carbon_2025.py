import unittest
from publish_map_carbon_2025 import period_estimate
class ContestedHours(unittest.TestCase):
 def row(self,nuclear=1,other=0):
  return dict(primary_generation_mwh=nuclear+other,generation_mwh_by_type={'B14':nuclear,'B17':other})
 def test_unknown_not_zero(self):
  result=period_estimate({0:self.row(other=1)},[0]);self.assertIsNone(result['full_lifecycle_gco2e_kwh']);self.assertEqual(result['mapped_subset_gco2e_kwh'],12);self.assertEqual(result['mapped_generation_share'],.5)
 def test_missing_contested_hour_blocks_full(self):
  self.assertIsNone(period_estimate({0:self.row()},[0,1])['full_lifecycle_gco2e_kwh'])
 def test_only_requested_hours(self):
  result=period_estimate({0:self.row(),1:self.row(other=1)},[0]);self.assertEqual(result['full_lifecycle_gco2e_kwh'],12)
 def test_empty_selection_is_unknown(self):
  self.assertIsNone(period_estimate({},[])['full_lifecycle_gco2e_kwh'])
if __name__=='__main__':unittest.main()
