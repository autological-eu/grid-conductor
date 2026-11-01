"""Chronological battery mechanics on a small coupled-network LP."""
import unittest
from dataclasses import replace
import numpy as np

from baselines.compact.storage import Battery, clear_window, rolling_days
from tests.test_scenario_2025 import toy_model


class StorageWindowTest(unittest.TestCase):
    def test_zero_storage_preserves_the_network_lp(self):
        model, cost = toy_model()
        result = clear_window(model, cost, 0, 2)
        self.assertAlmostEqual(result['objective_eur'], 450)
        np.testing.assert_allclose(result['zonal_prices'][:, 0], [20, 25])
        self.assertLess(result['maximum_primal_residual'], 1e-8)

    def test_battery_is_lossy_and_stock_is_carried_between_hours(self):
        model, cost = toy_model()
        battery = Battery('AA', 5, 10, .95, .95, 5, 5)
        result = clear_window(model, cost, 0, 2, (battery,))
        charge, discharge, stock = result['storage'][0].T
        np.testing.assert_allclose(stock, [5 + .95 * charge[0] - discharge[0] / .95,
                                            stock[0] + .95 * charge[1] - discharge[1] / .95],
                                   atol=1e-8)
        self.assertAlmostEqual(stock[-1], 5)
        self.assertGreater(charge.sum(), discharge.sum())
        self.assertLess(result['objective_eur'], 450)
        self.assertLess(result['maximum_primal_residual'], 1e-8)

    def test_invalid_initial_stock_is_rejected(self):
        model, cost = toy_model()
        with self.assertRaisesRegex(ValueError, 'Invalid battery'):
            clear_window(model, cost, 0, 2, (Battery('AA', 5, 10, .95, .95, 11, 5),))

    def test_rolling_days_carry_actual_stock_across_midnight(self):
        model, cost = toy_model()
        for key in ('availability', 'link_min', 'link_max', 'load', 'island_rhs', 'flow'):
            model[key] = np.repeat(model[key], 24, axis=0)
        costs = np.repeat(cost, 24, axis=0)
        battery = Battery('AA', 5, 10, .95, .95, 5, 5)
        result = rolling_days(model, costs, 0, 2, battery)
        stock = result['storage'][:, 2]
        self.assertGreater(stock[23], 5)
        self.assertAlmostEqual(stock[-1], 5)
        self.assertLess(result['objective_eur'], float(np.sum(costs[:, 0] * model['load'][:, 0])))
        self.assertLess(result['maximum_primal_residual'], 1e-8)
        first = rolling_days(model, costs, 0, 1, battery, horizon_end=48)
        second = rolling_days(model, costs, 24, 1,
                              replace(battery, initial_mwh=float(first['storage'][-1, 2])),
                              horizon_end=48)
        np.testing.assert_allclose(np.vstack([first['storage'], second['storage']]),
                                   result['storage'], atol=1e-8)
        self.assertAlmostEqual(first['objective_eur'] + second['objective_eur'],
                               result['objective_eur'])


if __name__ == '__main__':
    unittest.main()
