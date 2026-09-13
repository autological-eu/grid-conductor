import datetime as dt
import unittest
from carbon_pilot import iso, timestamp
from market_model import validate, dispatch
from build_market_pilot import assemble, NEIGHBORS

UTC=dt.timezone.utc
START=timestamp('2026-08-10T00:00:00Z')


def hourly_samples(values,start=START):
    return {start+dt.timedelta(hours=h,minutes=15*q):v for h,v in enumerate(values) for q in range(4)}


def flows_map():
    pairs={(a,b) for z,ns in NEIGHBORS.items() for o in ns for a,b in [(z,o),(o,z)]}
    return {p:hourly_samples([5,5] if p==('FR','CH') else [0,0]) for p in pairs}


def fixture(generation=None,charge=None,loads=None,observed=None,headroom=1.25):
    generation=generation or {'FR':{'B04':hourly_samples([40,40]),'B12':hourly_samples([30,30]),
        'B16':hourly_samples([10,10]),'B19':hourly_samples([20,20])},
        'CH':{'B04':hourly_samples([20,20]),'B12':hourly_samples([50,50])}}
    charge=charge or {}
    loads=loads or {'FR':hourly_samples([95,95]),'CH':hourly_samples([75,75])}
    caps={('FR','CH'):hourly_samples([5,5]),('CH','FR'):hourly_samples([0,0])}
    observed=observed or {('FR',iso(START)):60,('FR',iso(START+dt.timedelta(hours=1))):65,
        ('CH',iso(START)):70}
    return assemble(START,2,generation,charge,loads,caps,flows_map(),observed,headroom)


class AssembleTests(unittest.TestCase):
    def test_input_validates_and_prices_join_with_missing(self):
        data=fixture()
        validate(data)
        self.assertEqual(data['zones'],['FR','CH'])
        self.assertEqual(data['interval_hours'],1)
        self.assertEqual(data['timestamps'],[iso(START),iso(START+dt.timedelta(hours=1))])
        self.assertEqual(data['observed_price_eur_mwh']['FR'],[60,65])
        self.assertEqual(data['observed_price_eur_mwh']['CH'],[70,None])

    def test_thermal_blocks_headroom_bands_and_costs(self):
        data=fixture()
        fr_gas=[g for g in data['generators'] if g['id'].startswith('FR-B04')]
        self.assertEqual([g['cost_eur_mwh'] for g in fr_gas],[100,120,140])
        self.assertEqual([g['max_mw'] for g in fr_gas],[[25,25],[15,15],[10,10]])
        self.assertEqual({g['co2_t_per_mwh'] for g in fr_gas},{0.49})
        self.assertTrue(all(g['availability_basis']=='assumed_multiple_of_monthly_observed_peak' for g in fr_gas))

    def test_hydro_budget_and_fixed_blocks(self):
        data=fixture()
        fr_hydro=next(g for g in data['generators'] if g['id']=='FR-B12')
        self.assertEqual(fr_hydro['max_mw'],[30,30]);self.assertEqual(fr_hydro['energy_budget_mwh'],60)
        self.assertEqual(fr_hydro['cost_eur_mwh'],5);self.assertAlmostEqual(fr_hydro['co2_t_per_mwh'],.024)
        fr_wind=next(g for g in data['generators'] if g['id']=='FR-B19')
        self.assertEqual(fr_wind['min_mw'],fr_wind['max_mw']);self.assertEqual(fr_wind['cost_eur_mwh'],0)
        self.assertAlmostEqual(fr_wind['co2_t_per_mwh'],.011)

    def test_unmapped_fuel_has_no_emission_factor(self):
        gen={'FR':{'B04':hourly_samples([40,40]),'B12':hourly_samples([30,30])},
             'CH':{'B04':hourly_samples([20,20]),'B06':hourly_samples([10,10]),'B12':hourly_samples([50,50])}}
        data=fixture(generation=gen)
        ch_other=[g for g in data['generators'] if g['id'].startswith('CH-B06')]
        self.assertTrue(ch_other)
        self.assertTrue(all(g['co2_t_per_mwh'] is None for g in ch_other))

    def test_storage_net_injection_folded_into_external_imports(self):
        gen={'FR':{'B04':hourly_samples([40,40]),'B12':hourly_samples([30,30]),'B10':hourly_samples([8,8])},
             'CH':{'B04':hourly_samples([20,20]),'B12':hourly_samples([50,50])}}
        charge={'FR':{'B10':hourly_samples([3,3])}}
        data=fixture(generation=gen,charge=charge,loads={'FR':hourly_samples([70,70]),'CH':hourly_samples([75,75])})
        self.assertEqual(data['external_net_import_mw']['FR'],[5,5])
        self.assertEqual(data['external_net_import_mw']['CH'],[0,0])
        self.assertFalse(any(g['id'].endswith('-B10') for g in data['generators']))

    def test_observed_diagnostics_carried(self):
        data=fixture()
        self.assertEqual(data['observed_flow_mw'],{'FR-CH':[5,5]})
        self.assertEqual(data['observed_generation_mw']['FR']['B19'],[20,20])
        self.assertEqual(data['observed_price_eur_mwh']['FR'],[60.0,65.0])
        self.assertIsNone(data['observed_price_eur_mwh']['CH'][1])

    def test_missing_required_hour_data_rejected(self):
        broken=hourly_samples([95,95]);del broken[START+dt.timedelta(minutes=15)]
        with self.assertRaises(ValueError):
            fixture(loads={'FR':broken,'CH':hourly_samples([75,75])})

    def test_audit_flags_and_balance_check(self):
        data=fixture();audit=data['provenance']['audit']
        for z in ['FR','CH']:
            self.assertLess(audit[z]['balance_residual_mae_mw'],1e-9)
            self.assertFalse(audit[z]['generator_installed_capacity_available'])

    def test_dispatch_solves_deterministic_case(self):
        data=fixture()
        r=dispatch(data)
        self.assertEqual(r['unserved_mwh'],0)
        self.assertEqual(sum(x['spill_mwh'] for x in r['hourly']),0)
        self.assertEqual(r['hourly'][0]['flow_mw']['FR-CH'],5)
        fr_gas=[g for g in data['generators'] if g['id'].startswith('FR-B04')]
        self.assertAlmostEqual(sum(r['hourly'][0]['generation_mw'][g['id']] for g in fr_gas),40)
        # Per hour: FR wind .011*20 + solar .048*10 + hydro .024*30 + gas .49*40;
        # CH hydro .024*50 + gas .49*20. Two identical fixture hours.
        self.assertAlmostEqual(r['total_co2_t'],2*((0.011*20+0.048*10+0.024*30+0.49*40)+(0.024*50+0.49*20)),places=4)


if __name__=='__main__':unittest.main()