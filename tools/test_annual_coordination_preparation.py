import unittest
import pandas as pd
import pypsa
from prepare_annual_coordination import validate_calendar
class PreparationTests(unittest.TestCase):
 def network(self):
  n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01','2026-01-01',freq='h',inclusive='left'))
  n.add('Bus','A');n.add('Generator','G',bus='A',p_nom=10)
  return n
 def test_complete_calendar_and_gaps(self):
  n=self.network();validate_calendar(n,2025)
  n.set_snapshots(n.snapshots.delete(50))
  with self.assertRaisesRegex(ValueError,'chronological'):validate_calendar(n,2025)
 def test_annual_budget_and_expansion_fail(self):
  n=self.network();n.generators.loc['G','e_sum_max']=100
  with self.assertRaisesRegex(ValueError,'budgets'):validate_calendar(n,2025)
  n.generators.loc['G','e_sum_max']=float('inf');n.generators.loc['G','p_nom_extendable']=True
  with self.assertRaisesRegex(ValueError,'Expansion'):validate_calendar(n,2025)
if __name__=='__main__':unittest.main()
