import unittest
import numpy as np
from prepare_damped_annual_candidate import interpolate


class DampedTrialTests(unittest.TestCase):
    def test_convex_step_and_endpoints(self):
        np.testing.assert_allclose(interpolate([0., 10.], [10., 0.], .05), [.5, 9.5])
        np.testing.assert_equal(interpolate([0.], [10.], 1.), [10.])

    def test_invalid_fraction_and_state_rejected(self):
        for fraction in [0., -1., 1.1, float('nan')]:
            with self.assertRaises(ValueError):
                interpolate([0.], [1.], fraction)
        for proposal in [[1., 2.], [float('nan')]]:
            with self.assertRaises(ValueError):
                interpolate([0.], proposal, .1)
