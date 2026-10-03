import unittest
from collect_annual_production_carbon import aggregate
class AnnualAccounting(unittest.TestCase):
 def row(self,t='a',energy=2,intensity=12):
  return dict(start=t,primary_generation_mwh=energy,carbon_intensity=intensity,generation_mwh_by_type={'B14':energy or 0})
 def test_weighted_not_mean(self):
  a=self.row();b=self.row('b',8,24)
  self.assertEqual(aggregate([a,b],2)['annual_lifecycle_gco2e_kwh'],21.6)
 def test_missing_blocks_annual(self):
  self.assertIsNone(aggregate([self.row()],2)['annual_lifecycle_gco2e_kwh'])
  self.assertIsNone(aggregate([self.row(),self.row('b',None,None)],2)['annual_lifecycle_gco2e_kwh'])
 def test_unknown_blocks(self):
  self.assertIsNone(aggregate([self.row(intensity=None)],1)['annual_lifecycle_gco2e_kwh'])
 def test_tiny_unknown_still_blocks(self):
  row=self.row();row['generation_mwh_by_type']['B17']=1e-12
  self.assertIsNone(aggregate([row],1)['annual_lifecycle_gco2e_kwh'])
 def test_duplicates_fail(self):
  with self.assertRaises(ValueError):aggregate([self.row(),self.row()],2)
if __name__=='__main__':unittest.main()
