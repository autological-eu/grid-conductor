import unittest
from compare_2025_generation_reference import reference,compare


class GenerationReference(unittest.TestCase):
    def row(self,**changes):
        return {'Year':'2025','Area type':'Country','Category':'Electricity generation','Unit':'TWh',
            'Subcategory':'Total','Variable':'Total Generation','Value':'65.02','ISO 3 code':'CHE','Area':'Switzerland',**changes}

    def zone(self,**changes):
        return {'zone':'CH','geographic_scope':'national area','verified_months':12,'complete_reported_primary_hours':8760,
            'full_reported_primary_energy_mwh':48040000.,**changes}

    def test_complete_national_comparison_keeps_boundary_caveat(self):
        row=compare([self.zone()],reference([self.row()]))[0]
        self.assertEqual(row['status'],'unreconciled_national_quantity_comparison')
        self.assertAlmostEqual(row['reported_to_reference_ratio'],48.04/65.02)

    def test_provider_country_or_economy_schema(self):
        self.assertEqual(reference([self.row(**{'Area type':'Country or economy'})])['CHE']['total_generation_twh'],65.02)

    def test_capacity_and_wrong_year_not_generation(self):
        self.assertEqual(reference([self.row(Category='Capacity',Unit='GW'),self.row(Year='2024')]),{})

    def test_no_annualisation_of_partial_year(self):
        row=compare([self.zone(complete_reported_primary_hours=8000,full_reported_primary_energy_mwh=None)],reference([self.row()]))[0]
        self.assertIsNone(row['reported_to_reference_ratio']);self.assertIsNone(row['difference_twh'])

    def test_reject_falsely_complete_year(self):
        with self.assertRaises(ValueError):compare([self.zone(complete_reported_primary_hours=8000)],reference([self.row()]))

    def test_split_zone_cannot_use_national_total(self):
        row=compare([self.zone(zone='SE3',geographic_scope='bidding zone')],reference([self.row()]))[0]
        self.assertEqual(row['status'],'no_national_comparison_for_bidding_zone')

    def test_duplicate_or_invalid_reference_rejected(self):
        with self.assertRaises(ValueError):reference([self.row(),self.row()])
        with self.assertRaises(ValueError):reference([self.row(Value='NaN')])

    def test_missing_reference_stays_unknown(self):
        self.assertEqual(compare([self.zone()],{})[0]['status'],'national_reference_unavailable')


if __name__=='__main__':unittest.main()
