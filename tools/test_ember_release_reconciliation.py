from pathlib import Path
import tempfile
import unittest
from reconcile_ember_release import compare,read_generation

class ReleaseTests(unittest.TestCase):
    def test_changes_and_missing_are_distinct(self):
        a={('FRA','solar','2025-01-01'):1.,('FRA','wind','2025-01-01'):2.}
        b={('FRA','solar','2025-01-01'):1.003}
        r=compare(a,b);self.assertEqual(r['changed_records'],1);self.assertEqual(len(r['old_only']),1)
    def test_current_aggregates_excluded_and_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'data.csv'
            head='ISO 3 code,Date,Area type,Electricity source,Is aggregated source,Generation (TWh)\n'
            row='FRA,2025-01-01,Country,Solar,False,1.25\n'
            p.write_text(head+row+'FRA,2025-01-01,Country,Renewables,True,10\n')
            self.assertEqual(len(read_generation(p,True)),1)
            p.write_text(head+row+row)
            with self.assertRaises(ValueError):read_generation(p,True)
    def test_missing_generation_not_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'data.csv';p.write_text('ISO 3 code,Date,Area type,Electricity source,Is aggregated source,Generation (TWh)\nFRA,2025-01-01,Country,Solar,False,\n')
            self.assertEqual(read_generation(p,True),{})
if __name__=='__main__':unittest.main()
