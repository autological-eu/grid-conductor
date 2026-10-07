import unittest
import numpy as np
from hourly_renewable_estimates import reconstruct

class ReconstructionTests(unittest.TestCase):
    def test_capacity_cap_energy_and_night(self):
        values,status = reconstruct([0,1,8],10,18)
        self.assertAlmostEqual(values.sum(),18)
        self.assertEqual(values[0],0)
        self.assertLessEqual(values.max(),10)
        self.assertEqual(status,'monthly_constrained_shape_not_availability')
    def test_unreachable_not_filled(self):
        values,status = reconstruct([0,1],10,11)
        self.assertIsNone(values)
    def test_invalid_inputs(self):
        for shape,target in [([float('nan')],1),([-1],1),([11],1),([1],-1)]:
            with self.assertRaises(ValueError): reconstruct(shape,10,target)
    def test_zero_output_does_not_change_input(self):
        shape=np.array([1.,2.]); values,status=reconstruct(shape,10,0)
        np.testing.assert_equal(shape,[1,2]);np.testing.assert_equal(values,[0,0])
if __name__ == '__main__': unittest.main()
