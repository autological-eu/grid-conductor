import unittest
from compare_2025_generation_reference import reference,compare,hydro_diagnostic


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

    def hydro_zone(self,**changes):
        months=[dict(status='raw_interval_energy_replayed',by_reported_type={
            'B11':dict(reported_energy_mwh=1e6,observed_hours=730),
            'B12':dict(reported_energy_mwh=1e6,observed_hours=730),
            'B10':dict(reported_energy_mwh=.5e6,observed_hours=730)}) for _ in range(12)]
        return self.zone(monthly=months,**changes)

    def test_hydro_alternatives_do_not_change_primary_generation(self):
        zone=self.hydro_zone();ref=dict(by_reported_fuel_twh={'Hydro':33.})
        d=hydro_diagnostic(zone,ref)
        self.assertEqual(d['reported_primary_hydro_twh'],24.)
        self.assertEqual(d['reported_hydro_including_pumped_discharge_twh'],30.)
        self.assertEqual(zone['full_reported_primary_energy_mwh'],48040000.)

    def test_partial_hydro_not_annualised(self):
        zone=self.hydro_zone();zone['monthly'][0]['by_reported_type']['B11']['observed_hours']=729
        self.assertEqual(hydro_diagnostic(zone,dict(by_reported_fuel_twh={}))['status'],
            'incomplete_reported_primary_hydro_not_annualised')

    def test_missing_discharge_and_reference_not_zero(self):
        zone=self.hydro_zone()
        for m in zone['monthly']:del m['by_reported_type']['B10']
        d=hydro_diagnostic(zone,dict(by_reported_fuel_twh={}))
        self.assertIsNone(d['reported_pumped_storage_discharge_twh'])
        self.assertIsNone(d['reference_hydro_twh'])
        self.assertIsNone(d['including_discharge_difference_twh'])


if __name__=='__main__':unittest.main()
