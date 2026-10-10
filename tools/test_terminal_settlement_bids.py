"""Terminal policy must preserve exclusive modes and reject loss cycles."""
import unittest
import numpy as np
from terminal_settlement_bids import select_modes


class TerminalModes(unittest.TestCase):
    def test_exclusive_directions_and_power_limits(self):
        charge = np.array([[4., 0.], [0., 2.]])
        discharge = np.array([[0., 3.], [5., 0.]])
        c, d = select_modes(charge, discharge, np.array([10., 20.]), np.array([30., 40.]))
        np.testing.assert_array_equal(c, [[10., 0.], [0., 20.]])
        np.testing.assert_array_equal(d, [[0., 40.], [30., 0.]])
        self.assertFalse(np.any((c > 0) & (d > 0)))

    def test_reject_cycling_and_nonfinite_witness(self):
        with self.assertRaises(ValueError):
            select_modes(np.array([[1.]]), np.array([[1.]]), [2.], [2.])
        with self.assertRaises(ValueError):
            select_modes(np.array([[np.nan]]), np.array([[0.]]), [2.], [2.])


if __name__ == '__main__':
    unittest.main()
