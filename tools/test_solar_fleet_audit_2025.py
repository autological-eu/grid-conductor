"""Prevent loss double counting, false national coverage and false dispatch precision."""
import unittest
import numpy as np
from solar_fleet_audit_2025 import replace_losses,combine_regions,allocate


class SolarContracts(unittest.TestCase):
    def test_losses_replace_existing_inverter_factor(self):
        np.testing.assert_allclose(replace_losses(np.array([0.,90.])),[0.,86.])
        with self.assertRaises(ValueError):replace_losses([1.],retention=1.1)

    def test_national_missingness_propagates(self):
        a=np.ones(8760);b=a.copy();b[3]=np.nan
        self.assertTrue(np.isnan(combine_regions({'A':a},['A','B'])).all())
        values=combine_regions({'A':a,'B':b},['A','B'])
        self.assertTrue(np.isnan(values[3]));self.assertEqual(values[4],2.)

    def test_mixed_offer_allocations_retain_identification_bounds(self):
        # 40 MW solar plus 60 MW wind, with 50 MW pooled dispatch.
        point,lower,upper=allocate(np.array([[50.]]),np.array([[100.]]),np.array([[40.]]))
        np.testing.assert_array_equal(point,[20.]);np.testing.assert_array_equal(lower,[0.]);np.testing.assert_array_equal(upper,[40.])
        np.testing.assert_array_equal(replace_losses(np.zeros(3)),np.zeros(3))
        with self.assertRaises(ValueError):allocate(np.array([[1.]]),np.array([[1.]]),np.array([[2.]]))


if __name__=='__main__':unittest.main()
