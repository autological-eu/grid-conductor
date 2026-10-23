"""Meaningful curve, fold-isolation, and LP certificate unit checks."""
import copy
import unittest
import numpy as np
from scipy.sparse import csc_matrix
from sigmoid_month_pairs_2025 import (split, offer_costs, inverse_fit, certify)


class Curves(unittest.TestCase):
    def test_monotone_exact_volume_quantiles(self):
        theta = np.array([[20., 0, 0, 0, 0, np.log(10)]])
        groups = [dict(parameter=0, zone_id=0)]
        c = offer_costs(theta, groups, np.array([[50.]]), np.ones((1, 1, 5)), 8)
        self.assertTrue((np.diff(c[0]) > 0).all())
        self.assertAlmostEqual(float(c.mean()), 70)
        self.assertAlmostEqual(float(np.repeat(np.array([[800.]])/8, 8).sum()), 800)
        self.assertLess(c[0, 0], 70); self.assertGreater(c[0, -1], 70)

    def test_forward_pairs_no_overlap(self):
        tests = []
        for month in [1, 3, 5, 7, 9, 11]:
            train, test = split(month, month+1)
            self.assertLess(train[-1], test[0]); self.assertEqual(len(np.intersect1d(train, test)), 0)
            tests.extend(test)
        self.assertEqual(len(set(tests)), 4344)
        with self.assertRaises(ValueError): split(2, 3)

    def test_initializer_ignores_test_target_mutation(self):
        sealed = dict(design=dict(spread_prior_eur_mwh=12, ridge=.03, inverse_max_evaluations=20), parameters=[['DE', 'Gas']],
                      groups=[dict(parameter=0, zone_id=0)], countries=['DE'], technologies=['gas'], zones=['DE-LU'])
        T = 8
        data = dict(observed_prices=np.full((T, 1), 80.), observed_generation=np.full((T, 1, 1), 500.),
                    fixed_generation=np.zeros((T, 1, 1)), capacity=np.full((T, 1), 1000.), source_cost=np.full((T, 1), 70.),
                    features=np.ones((T, 1, 5)), ember=np.full((12, 1, 9), np.nan))
        # This mock uses the real Gas index without fabricating additional targets.
        from sigmoid_month_pairs_2025 import FAMILIES
        data['ember'][0, 0, FAMILIES.index('Gas')] = .002
        hours = np.arange(4); control = np.full((4, 1), 80.)
        a = inverse_fit(sealed, data, hours, control, 1)[0]
        other = copy.deepcopy(data)
        other['observed_prices'][4:] = -9999; other['observed_generation'][4:] = 9999999
        other['ember'][1:] = 9999999
        b = inverse_fit(sealed, other, hours, control, 1)[0]
        np.testing.assert_array_equal(a, b)

    def test_certificate_rejects_wrong_price_and_dispatch(self):
        # One generator and one free network variable fixed to zero by island row.
        A = csc_matrix([[1., -1.], [0., 1.]])
        data = dict(load=np.array([[5.]]), island_rhs=np.zeros((1, 1)), ratings=np.array([]), flow=np.zeros((1, 0)),
                    link_min=np.zeros((1, 0)), link_max=np.zeros((1, 0)))
        x = np.array([[5., 0.]]); y = np.array([[10., 10.]])
        certify(A, np.array([[10.]]), np.array([[20.]]), data, np.array([0]), x, y, np.array([50.]), 1, 0, 1)
        with self.assertRaises(ValueError):
            certify(A, np.array([[10.]]), np.array([[20.]]), data, np.array([0]), x+np.array([[1., 0.]]), y, np.array([60.]), 1, 0, 1)
        with self.assertRaises(ValueError):
            certify(A, np.array([[10.]]), np.array([[20.]]), data, np.array([0]), x, y+1, np.array([50.]), 1, 0, 1)


if __name__ == '__main__': unittest.main()
