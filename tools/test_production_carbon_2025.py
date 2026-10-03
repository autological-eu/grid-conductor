import unittest
from publish_production_carbon_2025 import accounting,DIRECT
class AccountingTests(unittest.TestCase):
 def test_unknown_biomass_blocks_full_estimate(self):
  r=accounting(dict(primary_generation_mwh=100,generation_mwh_by_type={"B04":80,"B01":20}),DIRECT)
  self.assertIsNone(r["full_intensity"]);self.assertAlmostEqual(r["mapped_share"],.8)
  self.assertAlmostEqual(r["mapped_mix_intensity"],403.92)
 def test_storage_not_primary(self):
  r=accounting(dict(primary_generation_mwh=100,generation_mwh_by_type={"B04":50,"B14":50,"B10":30}),DIRECT)
  self.assertAlmostEqual(r["full_intensity"],201.96)
 def test_missing_data_not_zero(self):
  r=accounting(dict(primary_generation_mwh=None,generation_mwh_by_type={"B14":100}),DIRECT)
  self.assertIsNone(r["full_intensity"]);self.assertIsNone(r["mapped_share"])
if __name__=="__main__":unittest.main()
