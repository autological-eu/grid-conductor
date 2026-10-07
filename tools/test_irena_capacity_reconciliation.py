import unittest
from irena_capacity_reconciliation import extract,number

class CapacityTests(unittest.TestCase):
    def test_units_flags(self):
        self.assertEqual(number('25 456 e'),dict(mw=25456.,source_flag='e'))
        self.assertEqual(number('0.125 u')['mw'],.125)
        with self.assertRaises(ValueError):number('-10')
    def test_missing_columns_not_shifted_or_filled(self):
        header='Wind energy\nCAP (MW) 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025\n'
        rejected=[]
        rows=extract(header+'France  '+ '  '.join(['1']*10)+'\nSpain  1  2\n',{'France':'FR','Spain':'ES'},rejected)
        self.assertEqual(len(rows),1);self.assertEqual(len(rejected),1)
        self.assertEqual(rows[0]['capacity_2025']['mw'],1)
    def test_duplicate_tables_rejected(self):
        page='Wind energy\nCAP (MW) 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025\nFrance  '+'  '.join(['1']*10)
        with self.assertRaises(ValueError):extract(page+'\f'+page,{'France':'FR'})
if __name__=='__main__':unittest.main()
