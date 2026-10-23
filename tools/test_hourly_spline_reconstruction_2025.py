import unittest
import numpy as np
from hourly_spline_reconstruction_2025 import expand, initialize, penalties, should_keep, joint_loss
from sigmoid_month_pairs_2025 import FAMILIES


class HourlySplineTests(unittest.TestCase):
    def test_initialization_preserves_hourly_midpoint_and_shapes(self):
        sealed = dict(groups=[dict(zone_id=0, technology='gas'), dict(zone_id=1, technology='solar')])
        data = dict(features=np.arange(30.).reshape(3, 2, 5) / 20, capacity=np.ones((3, 2)))
        shared = np.arange(20.).reshape(2, 10) / 10
        theta, active = initialize(sealed, data, np.array([0, 1, 2]), shared)
        for t in range(3):
            state = expand(theta[t])
            np.testing.assert_allclose(state[:, 0], (data['features'][t] * shared[:, :5]).sum(axis=1))
            np.testing.assert_array_equal(state[:, 5:], shared[:, 5:])
        self.assertTrue(active[:, 0].all())
        self.assertFalse(active[:, 1].any())

    def test_shrinkage_and_temporal_gradient_no_wrap_or_inactive_leak(self):
        rng = np.random.default_rng(72)
        initial = rng.normal(size=(4, 3, 6))
        theta = initial + rng.normal(size=initial.shape)
        active = np.array([[1, 1, 0], [1, 0, 0], [1, 1, 0], [1, 1, 0]], dtype=bool)
        design = dict(hourly_shrinkage=.01, temporal_penalty=.01)
        _, grad, _ = penalties(theta, initial, active, design)
        direction = rng.normal(size=theta.shape)
        eps = 1e-5
        finite = (penalties(theta + eps * direction, initial, active, design)[0] - penalties(theta - eps * direction, initial, active, design)[0]) / (2 * eps)
        self.assertAlmostEqual(finite, float((grad * direction).sum()), delta=1e-10)
        self.assertEqual(float(abs(grad[~active]).max()), 0)

    def test_stopping_retains_best_and_three_consecutive_failures(self):
        design = dict(minimum_price_improvement_eur_mwh=1e-6)
        best, stale, selected = float('inf'), 0, None
        scores = [30., 27., 28., 26., 26.5, 26.1, 27.]
        for t, score in enumerate(scores):
            if should_keep(score, best, design):
                best, stale, selected = score, 0, t
            else:
                stale += 1
            if stale == 3:
                break
        self.assertEqual((t, selected, best), (6, 3, 26.))

    def test_full_batch_generation_is_actual_sum_not_sample_expansion(self):
        sealed = dict(original_groups=[dict(country_id=0, family='Gas')], mapping=[0])
        data = dict(capacity=np.full((4, 1), 1000.))
        original = data['capacity'].copy()
        design = dict(price_smooth_absolute_epsilon=1, price_scale_eur_mwh=40, generation_floor_twh=.25, generation_smooth_absolute_epsilon=.01, ridge=0)
        prices = np.full((4, 1), 50.)
        values = np.full((4, 1), .5)
        ember = np.full((1, len(FAMILIES)), np.nan)
        ember[0, FAMILIES.index('Gas')] = .002  # 4 hours × .5 GW / 1000
        target = dict(prices=prices.copy(), ember=ember)
        z = np.zeros((1, 10))
        loss, gx, gp, _, parts = joint_loss(sealed, data, original, design, z, z, prices, values, np.arange(4), 4, target, np.zeros_like(ember))
        self.assertEqual(loss, 0.)
        self.assertEqual(parts['generation_loss'], 0.)
        self.assertEqual(float(abs(gx).max()), 0.)
        # A nonzero monthly mismatch must distribute a genuine coupled gradient
        # to every contributing hour, not silently train separate hourly totals.
        values += .1
        def objective(q):
            return joint_loss(sealed, data, original, design, z, z, prices, q, np.arange(4), 4, target, np.zeros_like(ember))
        _, gx, _, _, _ = objective(values)
        direction = np.array([[.4], [-.1], [.8], [.2]])
        eps = 1e-5
        finite = (objective(values + eps * direction)[0] - objective(values - eps * direction)[0]) / (2 * eps)
        self.assertGreater(float(gx.sum()), 0)
        self.assertAlmostEqual(finite, float((gx * direction).sum()), delta=1e-10)


if __name__ == '__main__':
    unittest.main()
