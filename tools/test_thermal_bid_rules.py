import unittest
from thermal_bid_rules import (thermal_bid, oil_barrel_to_thermal_price,
                               generator_offers, compile_thermal_case)


class ThermalBids(unittest.TestCase):
    def market(self):
        return dict(sources={k: 'Synthetic test input, not observed' for k in
                             ('gas_eur_mwh_th', 'oil_eur_mwh_th', 'co2_eur_t')},
                    hours=[dict(utc=f'2025-01-01T0{t}:00:00Z', gas_eur_mwh_th=40+20*t,
                                oil_eur_mwh_th=50, co2_eur_t=80) for t in range(2)])

    def test_fuel_and_carbon_shocks_and_efficiency(self):
        bid = thermal_bid(40, .5, 80, .202, 3)
        self.assertAlmostEqual(bid['offer_eur_mwh_el'], 115.32)
        self.assertAlmostEqual(thermal_bid(60, .5, 80, .202, 3)['offer_eur_mwh_el'] -
                               bid['offer_eur_mwh_el'], 40)
        self.assertGreater(thermal_bid(40, .35, 80, .202, 3)['offer_eur_mwh_el'],
                           bid['offer_eur_mwh_el'])
        self.assertAlmostEqual(thermal_bid(40, .5, 100, .202, 3)['offer_eur_mwh_el'] -
                               bid['offer_eur_mwh_el'], 8.08)

    def test_replace_not_add_native_cost_preserve_nuclear_and_renewables(self):
        generators = [dict(name='g', carrier='CCGT', efficiency=.5),
                      dict(name='o', carrier='oil', efficiency=.4),
                      dict(name='n', carrier='nuclear'), dict(name='w', carrier='onwind')]
        original = [[999, 888, 12, -5], [999, 888, 12, -5]]
        assumptions = {c: dict(source='Synthetic test', variable_om_eur_mwh_el=3,
                               emissions_t_mwh_th=f) for c, f in [('CCGT', .202), ('oil', .267)]}
        costs, records = generator_offers(generators, ['2025-01-01 00:00:00',
                                         '2025-01-01 01:00:00'], original, self.market(), assumptions)
        self.assertAlmostEqual(costs[0][0], 115.32)
        self.assertAlmostEqual(costs[0][1], 181.4)
        self.assertEqual(costs[0][2:], [12, -5])
        self.assertEqual(original[0][0], 999)
        self.assertEqual(len(records), 2)

    def test_reject_price_gaps_and_undeclared_sources(self):
        for change in ('gap', 'source'):
            market = self.market()
            if change == 'gap': market['hours'][1]['utc'] = '2025-01-01T02:00:00Z'
            else: market['sources']['co2_eur_t'] = ''
            with self.assertRaises(ValueError):
                generator_offers([], ['2025-01-01 00:00:00', '2025-01-01 01:00:00'],
                                 [[], []], market, {})

    def test_unit_conversion_and_invalid_inputs(self):
        self.assertAlmostEqual(oil_barrel_to_thermal_price(80, .9, 1.7), 80*.9/1.7)
        for eta in (0, 1.1, float('nan')):
            with self.assertRaises(ValueError): thermal_bid(40, eta, 80, .202, 3)
        with self.assertRaises(ValueError): thermal_bid(float('inf'), .5, 80, .202, 3)
        with self.assertRaises(ValueError): oil_barrel_to_thermal_price(80, .9, 0)

    def test_compiled_dispatch_matches_native_with_replacement_costs(self):
        try:
            import numpy as np
            import pandas as pd
            import pypsa
            import highspy
        except ImportError:
            self.skipTest('Native integration requires the pinned PyPSA environment')
        from european_physical_bids_2025 import compile_model, solver
        n = pypsa.Network()
        n.set_snapshots(pd.date_range('2025-01-01', periods=2, freq='h'))
        n.add('Bus', 'b', carrier='AC', country='DE', v_nom=380)
        n.add('Generator', 'gas', bus='b', carrier='CCGT', p_nom=100,
              efficiency=.5, marginal_cost=999)
        n.add('Generator', 'gas-less-efficient', bus='b', carrier='CCGT', p_nom=100,
              efficiency=.35, marginal_cost=999)
        n.add('Generator', 'nuclear', bus='b', carrier='nuclear', p_nom=10,
              marginal_cost=6)
        n.add('Load', 'demand', bus='b', p_set=70)
        assumptions = dict(CCGT=dict(source='Synthetic test', emissions_t_mwh_th=.202,
                                     variable_om_eur_mwh_el=3))
        original_availability = n.get_switchable_as_dense('Generator', 'p_max_pu').copy()
        case, m, _ = compile_thermal_case(n, compile_model(n), [], None,
                                          self.market(), assumptions)
        self.assertEqual(m['ng'], 3)  # Different efficiencies must not merge.
        pd.testing.assert_frame_equal(original_availability,
                                      case.get_switchable_as_dense('Generator', 'p_max_pu'))
        h = solver(m)
        costs = []
        for t in range(2):
            cols = np.arange(m['ng'], dtype=np.int32)
            h.changeColsCost(m['ng'], cols, m['cost'][t])
            h.run()
            self.assertEqual(h.getModelStatus(), highspy.HighsModelStatus.kOptimal)
            costs.append(h.getObjectiveValue())
        p = case.copy()
        p.generators_t.marginal_cost = pd.DataFrame(m['native_cost'],
                                                   index=p.snapshots, columns=p.generators.index)
        status, condition = p.optimize(solver_name='highs',
                                       solver_options={'threads': 1, 'output_flag': False})
        self.assertEqual((status, condition), ('ok', 'optimal'))
        self.assertAlmostEqual(sum(costs), float(p.objective), places=5)
        self.assertAlmostEqual(costs[0], 60*115.32+10*6, places=5)
        self.assertAlmostEqual(costs[1]-costs[0], 60*40, places=5)


if __name__ == '__main__': unittest.main()
