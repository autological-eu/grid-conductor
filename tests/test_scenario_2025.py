"""Declared scenario deltas and their accounting, on synthetic fixtures.

These tests pin the mechanics only: no baseline data, solver or highspy is
required. The accepted-LP gates live in ``baselines.compact.run_scenario``.
"""

import unittest

import numpy as np
from scipy.sparse import csc_matrix

from baselines.compact.metrics import (
    binding_hours, branch_congestion, compare, emergency_mwh, generation_by_zone,
    generator_income, link_candidates, link_rent, welfare_gain_meur, zone_prices)
from baselines.compact.scenario import (
    GeneratorAddition, LinkUpgrade, Scenario, apply)


def toy_model():
    """Two zones, one offer, one link, one island, one branch row."""
    matrix = csc_matrix(np.array([
        [1.0, 0.0, -1.0, 0.0],
        [0.0, 0.0, 0.0, -1.0],
        [0.0, 0.0, 1.0, 1.0],
        [0.0, 1.0, 0.5, -0.5],
    ]))
    model = dict(
        A=matrix, zones=np.array(['AA', 'BB']), ng=1, nl=1, nz=2, islands=[None],
        ratings=np.array([100.0]), availability=np.array([[50.0], [40.0]]),
        link_min=np.array([[-10.0], [-5.0]]), link_max=np.array([[10.0], [5.0]]),
        load=np.array([[10.0, 0.0], [10.0, 0.0]]),
        island_rhs=np.zeros((2, 1)), flow=np.zeros((2, 1)),
        cost=np.array([[20.0], [25.0]]), offer_zones=np.array(['AA']),
        emergency_mask=np.array([False]))
    return model, model['cost']


class ScenarioApplyTest(unittest.TestCase):
    def test_zero_delta_is_identical_and_does_not_mutate(self):
        model, cost = toy_model()
        declared, declared_cost, description = apply(model, cost, Scenario(name='zero'))
        np.testing.assert_array_equal(declared['A'].toarray(), model['A'].toarray())
        np.testing.assert_array_equal(declared['availability'], model['availability'])
        np.testing.assert_array_equal(declared_cost, cost)
        np.testing.assert_array_equal(declared['link_min'], model['link_min'])
        self.assertEqual(declared['ng'], 1)
        self.assertEqual(description['generators'], [])
        np.testing.assert_array_equal(model['availability'], np.array([[50.0], [40.0]]))

    def test_generator_profile_can_use_sealed_technology_without_pure_old_offer(self):
        from baselines.compact.run_scenario import profile_sources

        model, _ = toy_model()
        schema = dict(groups=[dict(zone='AA', technology='solar')])
        data = dict(capacity=np.array([[20.0], [0.0]]))
        sources = profile_sources(schema, data, model)
        self.assertEqual(sources['AA', 'solar']['peak_mw'], 20.0)
        np.testing.assert_array_equal(sources['AA', 'solar']['capacity'], [20.0, 0.0])

    def test_generator_addition_appends_one_offer_column(self):
        model, cost = toy_model()
        profile = np.array([30.0, 0.0])
        declared, declared_cost, description = apply(model, cost, Scenario(
            name='gen', generators=(GeneratorAddition(
                name='wind-AA-100', zone='AA', capacity_mw=100.0,
                profile_mw=profile, bid_eur_mwh=0.0),)))
        self.assertEqual(declared['ng'], 2)
        self.assertEqual(declared['A'].shape, (4, 5))
        added = declared['A'].toarray()[:, 1]
        np.testing.assert_array_equal(added, np.array([1.0, 0.0, 0.0, 0.0]))
        np.testing.assert_array_equal(declared['availability'][:, 1], profile)
        np.testing.assert_array_equal(declared_cost[:, 1], np.zeros(2))
        np.testing.assert_array_equal(declared['offer_zones'], np.array(['AA', 'AA']))
        self.assertFalse(declared['emergency_mask'][1])
        self.assertEqual(description['generators'][0]['column'], 1)
        self.assertAlmostEqual(description['generators'][0]['annual_gwh'], 0.03)
        # The accepted solver reads columns as [offers, links, injections], so
        # the new offer must shift the link and injection blocks right.
        self.assertEqual(declared['A'].shape[1], declared['ng'] + declared['nl'] + declared['nz'])
        np.testing.assert_array_equal(declared['A'].toarray()[:, declared['ng']],
                                      model['A'].toarray()[:, model['ng']])

    def test_generator_profile_must_respect_capacity_and_zone(self):
        model, cost = toy_model()
        with self.assertRaises(ValueError):
            apply(model, cost, Scenario(name='bad', generators=(GeneratorAddition(
                name='x', zone='AA', capacity_mw=10.0, profile_mw=np.array([11.0, 0.0])),)))
        with self.assertRaises(ValueError):
            apply(model, cost, Scenario(name='bad', generators=(GeneratorAddition(
                name='x', zone='ZZ', capacity_mw=10.0, profile_mw=np.array([1.0, 0.0])),)))

    def test_link_scaling_keeps_the_observed_shape(self):
        model, cost = toy_model()
        declared, _, description = apply(model, cost, Scenario(
            name='line', links=(LinkUpgrade(link=0, factor=1.5, release_envelope=False),)))
        np.testing.assert_array_equal(declared['link_min'], model['link_min'] * 1.5)
        np.testing.assert_array_equal(declared['link_max'], model['link_max'] * 1.5)
        self.assertFalse(description['links'][0]['release_envelope'])
        self.assertAlmostEqual(description['links'][0]['baseline_peak_mw'], 10.0)

    def test_releasing_the_envelope_uses_the_declared_band(self):
        model, cost = toy_model()
        declared, _, _ = apply(model, cost, Scenario(
            name='line', links=(LinkUpgrade(link=0, factor=2.0, release_envelope=True),)))
        np.testing.assert_array_equal(declared['link_min'][:, 0], np.full(2, -20.0))
        np.testing.assert_array_equal(declared['link_max'][:, 0], np.full(2, 20.0))

    def test_unknown_link_is_rejected(self):
        model, cost = toy_model()
        with self.assertRaises(ValueError):
            apply(model, cost, Scenario(
                name='bad', links=(LinkUpgrade(link=5, factor=1.5, release_envelope=True),)))


class AccountingTest(unittest.TestCase):
    def test_prices_are_the_first_rows_in_zone_order(self):
        duals = np.array([[10.0, 20.0, 99.0], [11.0, 21.0, 99.0]])
        np.testing.assert_array_equal(zone_prices(duals, 2), np.array([[10.0, 20.0], [11.0, 21.0]]))

    def test_welfare_gain_is_the_annual_cost_reduction(self):
        result = welfare_gain_meur(np.array([1e6, 2e6]), np.array([1e6, 1e6]))
        self.assertAlmostEqual(result['gain_meur'], 1.0)

    def test_generator_income_is_revenue_minus_declared_bid(self):
        values = np.zeros((2, 3))
        values[:, 2] = [5.0, 0.0]
        prices = np.array([[10.0], [20.0]])
        result = generator_income(values, prices, 0, 2, 10.0, 2.0)
        self.assertAlmostEqual(result['revenue_meur'], 50e-6)
        self.assertAlmostEqual(result['bid_cost_meur'], 10e-6)
        self.assertAlmostEqual(result['income_meur'], 40e-6)
        self.assertAlmostEqual(result['capacity_factor'], 0.25)

    def test_link_rent_is_signed_by_the_price_gradient(self):
        values = np.zeros((2, 3))
        values[:, 1] = [1.0, -1.0]
        result = link_rent(values, ng=1, link=0, price_from=np.array([10.0, 10.0]),
                           price_to=np.array([20.0, 5.0]))
        self.assertAlmostEqual(result['signed_meur'], 15e-6)
        self.assertAlmostEqual(result['absolute_meur'], 15e-6)
        self.assertEqual(result['nonzero_hours'], 2)
        self.assertAlmostEqual(result['mean_abs_spread_eur_mwh'], 7.5)

    def test_binding_hours_and_emergency(self):
        values = np.zeros((2, 3))
        values[:, 1] = [10.0, 0.0]
        hours = binding_hours(values, ng=1, link=0,
                              link_min=np.array([[-10.0], [-10.0]]),
                              link_max=np.array([[10.0], [10.0]]))
        self.assertEqual(hours, 1)
        self.assertEqual(emergency_mwh(values, np.array([True, False, False]), 3), 0.0)
        self.assertEqual(emergency_mwh(values, np.array([False, True, False]), 3), 10.0)

    def test_generation_by_zone_includes_added_columns(self):
        model, _ = toy_model()
        model['ng'] = 2
        model['offer_zones'] = np.array(['AA', 'BB'])
        values = np.array([[10.0, 5.0, 0.0, 0.0], [20.0, 0.0, 0.0, 0.0]])
        result = generation_by_zone(model, values)
        self.assertAlmostEqual(result['AA'], 30e-6)
        self.assertAlmostEqual(result['BB'], 5e-6)


class RankingAndCompareTest(unittest.TestCase):
    def witness(self):
        values = np.zeros((2, 4))
        values[:, 1] = [10.0, 0.0]
        duals = np.array([[10.0, 20.0, 0.0, 5.0], [10.0, 20.0, 0.0, 5.0]])
        return dict(values=values, row_duals=duals, objectives=np.array([1e6, 1e6]))

    def test_link_candidates_rank_by_absolute_rent(self):
        model, _ = toy_model()
        ranked = link_candidates(model, self.witness(), [('AA', 'BB')], model['zones'])
        self.assertEqual(len(ranked), 1)
        self.assertAlmostEqual(ranked[0]['signed_meur'], 100e-6)
        self.assertEqual(ranked[0]['binding_hours'], 1)

    def test_branch_congestion_uses_the_shadow_price_proxy(self):
        model, _ = toy_model()
        ranked = branch_congestion(model, self.witness())
        self.assertEqual(ranked[0]['row'], 0)
        self.assertEqual(ranked[0]['binding_hours'], 2)
        self.assertAlmostEqual(ranked[0]['rent_proxy_meur'], 1e-3)

    def test_compare_pairs_base_and_scenario_on_the_same_coverage(self):
        model, cost = toy_model()
        base = self.witness()
        scenario = dict(values=base['values'].copy(),
                        row_duals=base['row_duals'].copy(),
                        objectives=base['objectives'].copy())
        scenario['objectives'] = scenario['objectives'] - 1e5
        declared, _, description = apply(model, cost, Scenario(
            name='line', links=(LinkUpgrade(link=0, factor=2.0, release_envelope=True),)))
        scenario['values'] = np.zeros((2, declared['A'].shape[1]))
        scenario['values'][:, 1] = 20.0
        scenario['row_duals'] = np.zeros((2, declared['A'].shape[0]))
        scenario['row_duals'][:, :2] = base['row_duals'][:, :2]
        result = compare(model, base, declared, scenario, description, [('AA', 'BB')])
        self.assertAlmostEqual(result['welfare']['gain_meur'], 0.2)
        self.assertAlmostEqual(result['links'][0]['scenario']['signed_meur'], 400e-6)
        self.assertAlmostEqual(result['links'][0]['baseline']['signed_meur'], 100e-6)
        self.assertEqual(result['emergency']['scenario_mwh'], 0.0)


class DriverTest(unittest.TestCase):
    """Plan resolution and reporting, with the solver import stubbed out."""

    @classmethod
    def setUpClass(cls):
        import sys
        import types

        if 'highspy' not in sys.modules:
            sys.modules['highspy'] = types.ModuleType('highspy')
        from baselines.compact import run_scenario

        cls.driver = run_scenario

    def evidence(self):
        model, cost = toy_model()
        witness = dict(values=np.zeros((2, 4)), row_duals=np.zeros((2, 4)),
                       objectives=np.array([1e6, 1e6]))
        witness['values'][:, 1] = [10.0, 0.0]
        witness['row_duals'][:, :2] = [[10.0, 20.0], [10.0, 20.0]]
        sources = {('AA', 'solar'): dict(group=0, column=0, peak_mw=10.0,
                                         annual_gwh=0.5, capacity=np.array([5.0, 10.0])),
                   ('BB', 'onshore_wind'): dict(group=1, column=0, peak_mw=8.0,
                                                annual_gwh=0.9, capacity=np.array([8.0, 4.0]))}
        return dict(model=model, cost=cost, witness=witness, sources=sources,
                    endpoints=[('AA', 'BB')])

    def test_default_plan_covers_zero_generator_and_link_ladders(self):
        plan = self.driver.default_plan(self.evidence())
        names = [entry['name'] for entry in plan['scenarios']]
        self.assertEqual(names[0], 'zero-delta')
        self.assertIn('gen-solar-AA-500', names)
        self.assertIn('gen-wind-BB-2000', names)
        self.assertIn('line-AA-BB-x1.5', names)
        link = [entry for entry in plan['scenarios'] if entry['kind'] == 'link'][0]
        self.assertEqual(link['link'], 0)
        self.assertTrue(link['release_envelope'])

    def test_build_scenario_resolves_each_declared_kind(self):
        evidence = self.evidence()
        sources, endpoints = evidence['sources'], evidence['endpoints']
        plan = self.driver.default_plan(evidence)
        by_name = {entry['name']: entry for entry in plan['scenarios']}
        none = self.driver.build_scenario(by_name['zero-delta'], sources, endpoints)
        self.assertEqual((none.generators, none.links), ((), ()))
        generator = self.driver.build_scenario(by_name['gen-solar-AA-1000'],
                                               sources, endpoints)
        addition = generator.generators[0]
        self.assertEqual((addition.zone, addition.capacity_mw), ('AA', 1000.0))
        self.assertAlmostEqual(float(addition.profile_mw.max()), 1000.0)
        self.assertAlmostEqual(float(addition.profile_mw.sum()), 1500.0)
        link = self.driver.build_scenario(by_name['line-AA-BB-x2.0'], sources, endpoints)
        self.assertEqual(link.links[0].link, 0)
        self.assertEqual(link.links[0].factor, 2.0)

    def test_build_scenario_rejects_a_mismatched_declared_link(self):
        entry = dict(name='bad', kind='link', link=3, from_zone='AA', to_zone='BB', factor=2.0)
        with self.assertRaises(ValueError):
            self.driver.build_scenario(entry, {}, [('AA', 'BB')])

    def test_zero_delta_gate_accepts_identical_and_rejects_drift(self):
        witness = dict(objectives=np.array([1.0, 2.0]),
                       row_duals=np.array([[10.0, 20.0, 5.0], [10.0, 20.0, 5.0]]))
        cleared = dict(objectives=witness['objectives'].copy(),
                       row_duals=witness['row_duals'].copy())
        self.driver.zero_delta_gate(cleared, witness, 2)
        cleared['row_duals'][0, 0] += 1e-3
        with self.assertRaises(ValueError):
            self.driver.zero_delta_gate(cleared, witness, 2)

    def test_report_renders_only_passed_summaries(self):
        import json
        import tempfile
        from pathlib import Path

        summary = dict(status='scenario_replay_passed',
                       scenario=dict(name='line-AA-BB-x1.5'),
                       emergency_mwh=0.0,
                       result=dict(
                           welfare=dict(gain_meur=12.5),
                           prices=dict(mean_abs_change_eur_mwh=0.25),
                           generators=[],
                           links=[dict(from_zone='AA', to_zone='BB', factor=1.5,
                                       baseline=dict(signed_meur=3.0),
                                       scenario=dict(signed_meur=2.0))]))
        with tempfile.TemporaryDirectory() as folder:
            passed = Path(folder) / 'line-AA-BB-x1.5'
            passed.mkdir()
            (passed / 'summary.json').write_text(json.dumps(summary))
            failed = Path(folder) / 'broken'
            failed.mkdir()
            (failed / 'summary.json').write_text(json.dumps(dict(status='failed')))
            text = self.driver.report(folder)
        self.assertIn('| line-AA-BB-x1.5 | 12.50 |', text)
        self.assertIn('3.0 -> 2.0 M EUR rent', text)
        self.assertIn('mean absolute price change (EUR/MWh)', text)
        self.assertNotIn('broken', text)


if __name__ == '__main__':
    unittest.main()
