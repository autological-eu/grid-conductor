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
 def test_energy_weighting(self):
  other=dict(primary_generation_mwh=3,generation_mwh_by_type={'B16':3})
  self.assertEqual(period_estimate({0:self.row(),1:other},[0,1])['full_lifecycle_gco2e_kwh'],39)
 def test_tiny_positive_unknown_not_zero(self):
  self.assertIsNone(period_estimate({0:self.row(other=1e-12)},[0])['full_lifecycle_gco2e_kwh'])
 def test_map_registry_geography(self):
  from collect_map_carbon_2025 import registry
  areas=registry();self.assertEqual(len(areas),39)
  self.assertNotEqual(areas['SE3']['eic'],areas['SE4']['eic'])
  self.assertIn('excludes Luxembourg',areas['DE-LU']['scope'])
 def test_empty_selection_is_unknown(self):
  self.assertIsNone(period_estimate({},[])['full_lifecycle_gco2e_kwh'])
if __name__=='__main__':unittest.main()
