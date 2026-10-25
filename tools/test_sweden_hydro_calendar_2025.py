import unittest
from sweden_hydro_calendar_2025 import parse
TEXT='''Kraftläget Vecka05 27jan -2feb år2025
energiinnehåll är beräknat 10 till24 027 GWh denna vecka
blev826 GWh
 SE1 71,3 10 559
 SE2 74,2 11 623
 SE3 50,4 1 674
 SE4 77,7 171
'''
class Checks(unittest.TestCase):
 def test_source_text_column_noise(self):
  r=parse(TEXT.replace('Vecka05','Vecka 05').replace('år2025','år 2025').replace('till24','till 24').replace('blev826','blev 826'))
  self.assertEqual(r['stock_gwh'],24027);self.assertEqual(r['inflow_gwh'],826);self.assertEqual(r['week'],5)
 def test_missing_values_are_not_zero(self):
  with self.assertRaises(ValueError):parse('Vecka 05 år 2025')
if __name__=='__main__':unittest.main()
