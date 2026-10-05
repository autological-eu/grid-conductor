import unittest
from compare_native_exchange_reference import reference,compare

class ExchangeReference(unittest.TestCase):
    def row(self,value='19.54'):
        return {'Year':'2025','Area type':'Country','Category':'Electricity imports','Variable':'Net Imports','Unit':'TWh','Value':value,'ISO 3 code':'DEU','Area':'Germany'}
    def model(self):
        return dict(status='fixed_inventory_native_country_exchange_diagnostic_not_validation',year=2025,hours=8760,
            countries=[dict(country='DE',hours=8760,net_export_mwh=156e6),dict(country='XX',hours=8760,net_export_mwh=1e6)])
    def test_import_export_sign_and_unknown(self):
        rows=compare(self.model(),reference([self.row()]))
        self.assertEqual(rows[0]['reference_net_export_twh'],-19.54)
        self.assertAlmostEqual(rows[0]['difference_net_export_twh'],175.54)
        self.assertIsNone(rows[1]['reference_net_export_twh'])
    def test_duplicate_invalid_and_unsupported(self):
        for rows in [[self.row(),self.row()],[self.row('nan')],[]]:
            with self.assertRaises(ValueError):reference(rows)
    def test_reject_partial_year(self):
        m=self.model();m['countries'][0]['hours']=744
        with self.assertRaises(ValueError):compare(m,reference([self.row()]))
