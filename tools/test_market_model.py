import copy
import unittest
from market_model import dispatch, experiment


def fixture():
    return dict(timestamps=['2026-08-01T00:00:00Z','2026-08-01T01:00:00Z'],interval_hours=1,
        zones=['A','B'],load_mw={'A':[0,0],'B':[100,100]},external_net_import_mw={'A':[0,0],'B':[0,0]},
        generators=[dict(id='cheap',zone='A',max_mw=[100,100],cost_eur_mwh=20),
                    dict(id='dear',zone='B',max_mw=[100,100],cost_eur_mwh=100)],
        edges=[dict(id='AB',a='A',b='B',ab_mw=[50,50],ba_mw=[50,50])],storage=[],unserved_cost_eur_mwh=10000)


class DispatchTests(unittest.TestCase):
    def test_known_welfare_integral_and_input_unchanged(self):
        data=fixture();before=copy.deepcopy(data)
        r=experiment(data,'AB',50)
        self.assertAlmostEqual(r['period_opportunity_meur'],.008)
        self.assertEqual(data,before)
        self.assertIsNone(r['annual_opportunity_meur'])
        self.assertAlmostEqual(sum(h['benefit_eur'] for h in r['hourly_difference']),8000)

    def test_zero_relaxation(self):
        self.assertAlmostEqual(experiment(fixture(),'AB',0)['period_opportunity_meur'],0)

    def test_energy_budget_and_ramp(self):
        d=fixture();d['generators'][0]['energy_budget_mwh']=50
        d['generators'][0]['ramp_mw_per_hour']=0
        r=dispatch(d)
        self.assertAlmostEqual(r['hourly'][0]['generation_mw']['cheap'],25)
        self.assertAlmostEqual(r['hourly'][1]['generation_mw']['cheap'],25)

    def test_linked_storage_terminal_and_efficiency(self):
        d=fixture();d['zones']=['A'];d['load_mw']={'A':[0,80]};d['external_net_import_mw']={'A':[0,0]};d['edges']=[]
        d['generators']=[dict(id='cheap',zone='A',max_mw=[100,0],cost_eur_mwh=10),dict(id='dear',zone='A',max_mw=[0,100],cost_eur_mwh=100)]
        d['storage']=[dict(id='battery',zone='A',power_mw=100,energy_mwh=100,initial_mwh=0,terminal_mwh=0,
                          charge_efficiency=.8,discharge_efficiency=1,throughput_cost_eur_mwh=.1)]
        r=dispatch(d)
        self.assertAlmostEqual(r['hourly'][0]['storage']['battery']['end_mwh'],80)
        self.assertAlmostEqual(r['hourly'][1]['storage']['battery']['end_mwh'],0)
        self.assertAlmostEqual(r['hourly'][1]['generation_mw']['dear'],0)
        self.assertEqual(r['simultaneous_storage_intervals'],0)

    def test_quarter_hour_units_and_model_price(self):
        d=fixture();d['interval_hours']=.25;d['timestamps'][1]='2026-08-01T00:15:00Z'
        r=experiment(d,'AB',50)
        self.assertAlmostEqual(r['period_opportunity_meur'],.002)
        self.assertAlmostEqual(r['baseline']['hourly'][0]['price_eur_mwh']['B'],100)

    def test_missing_and_negative_capacity_rejected(self):
        d=fixture();d['load_mw']['A'][0]=None
        with self.assertRaises(ValueError):dispatch(d)
        d=fixture();d['edges'][0]['ab_mw'][0]=-1
        with self.assertRaises(ValueError):dispatch(d)

    def test_shortage_is_explicit(self):
        d=fixture();d['generators']=[]
        self.assertAlmostEqual(dispatch(d)['unserved_mwh'],200)

    def test_emissions_hand_calc_and_experiment(self):
        d=fixture()
        d['generators'][0]['co2_t_per_mwh']=.49
        d['generators'][1]['co2_t_per_mwh']=.82
        d['emission_basis']='fixture_basis'
        base=dispatch(d)
        # Per hour cheap exports 50 to B, dear supplies the rest; two hours.
        self.assertAlmostEqual(base['total_co2_t'],2*(50*.49+50*.82))
        self.assertEqual(experiment(d,'AB',50)['emission_basis'],'fixture_basis')
        self.assertAlmostEqual(experiment(d,'AB',0)['co2_change_t'],0)
        relaxed=experiment(d,'AB',50)
        self.assertAlmostEqual(relaxed['co2_change_t'],2*(50*.49+50*.82)-2*(100*.49))
        self.assertAlmostEqual(sum(h['co2_benefit_t'] for h in relaxed['hourly_difference']),relaxed['co2_change_t'])

    def test_invalid_emission_factor_rejected(self):
        d=fixture();d['generators'][0]['co2_t_per_mwh']=-1
        with self.assertRaises(ValueError):dispatch(d)


if __name__=='__main__':unittest.main()
