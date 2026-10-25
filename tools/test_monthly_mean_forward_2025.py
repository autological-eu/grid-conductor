import unittest
import numpy as np
from monthly_mean_forward_2025 import monthly_mean
from independent_hourly_transport_2025 import economic_nodes


class MonthlyMeanTests(unittest.TestCase):
    def test_mean_functions_not_raw_and_no_clock(self):
        theta = np.random.default_rng(9).normal(size=(8, 3, 6))
        neutral = np.zeros((3, 6)); available = np.ones((8, 3))
        raw, support = monthly_mean(theta, available, neutral)
        np.testing.assert_allclose(economic_nodes(raw), economic_nodes(theta).mean(axis=0), atol=1e-12)
        self.assertGreater(abs(raw-theta.mean(axis=0)).max(), .01)
        np.testing.assert_array_equal(support, [8, 8, 8])
        perm = np.array([7, 2, 0, 3, 6, 5, 4, 1])
        shuffled, _ = monthly_mean(theta[perm], available[perm], neutral)
        np.testing.assert_allclose(shuffled, raw, atol=1e-12)

    def test_support_fallback_and_future_isolation(self):
        theta = np.random.default_rng(17).normal(size=(5, 2, 6)); neutral = np.zeros((2, 6))
        available = np.zeros((5, 2)); available[:2, 0] = [1, 999]
        raw, count = monthly_mean(theta, available, neutral)
        np.testing.assert_allclose(economic_nodes(raw[0]), economic_nodes(theta[:2, 0]).mean(axis=0), atol=1e-12)
        np.testing.assert_allclose(raw[1], neutral[1], atol=1e-12)
        theta[2:, 0] = 40; theta[:, 1] = -20
        again, _ = monthly_mean(theta, available, neutral)
        np.testing.assert_allclose(again, raw, atol=1e-12)
        np.testing.assert_array_equal(count, [2, 0])

    def test_shape_guard(self):
        with self.assertRaises(ValueError):
            monthly_mean(np.zeros((2, 3, 6)), np.ones((3, 2)), np.zeros((3, 6)))


if __name__ == '__main__':
    unittest.main()
