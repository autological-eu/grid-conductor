"""Calendar boundaries, expansion/retirement, missing dates and duplicate batches."""
import unittest
import pandas as pd
from norway_wind_geography_2025 import dated_capacity

def farm(zone,batches):return dict(ElspotomraadeNummer=zone,Turbiner=batches)
def batch(key,start,end=None,mw=1):return dict(TurbinID=key,DatoIdriftsatt=start,DatoUtavdrift=end,AntallTurbiner=1,TurbinStorrelse_kW=mw*1000)

class Dates(unittest.TestCase):
    def setUp(self):self.times=pd.date_range('2025-01-01',periods=3,freq='h')
    def test_expansion_and_retirement_boundaries(self):
        rows=[farm(1,[batch(1,'2024-01-01',mw=2),batch(2,'2025-01-01T01:00:00','2025-01-01T02:00:00',3)])]
        self.assertEqual(dated_capacity(rows,self.times).NO1.tolist(),[2,5,2])
    def test_missing_date(self):
        with self.assertRaisesRegex(ValueError,'Missing'):dated_capacity([farm(1,[batch(1,None)])],self.times)
    def test_duplicate_batch(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):dated_capacity([farm(1,[batch(1,'2024-01-01')]*2)],self.times)
    def test_retirement_before_commissioning(self):
        with self.assertRaisesRegex(ValueError,'precedes'):dated_capacity([farm(1,[batch(1,'2025-01-02','2025-01-01')])],self.times)
    def test_unknown_zone(self):
        with self.assertRaisesRegex(ValueError,'Unknown'):dated_capacity([farm(6,[batch(1,'2024-01-01')])],self.times)

if __name__=='__main__':unittest.main()
