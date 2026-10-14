import unittest
import numpy as np
from residual_price_benchmark_2025 import fit_curve

class CurveTests(unittest.TestCase):
    def test_monotone_pooling(self):
        x,y=fit_curve(np.array([0.,1.,2.]),np.array([0.,10.,0.]));np.testing.assert_array_equal(y,[0,5,5])
    def test_duplicate_inputs_preserve_weights(self):
        x,y=fit_curve(np.array([0.,0.,1.]),np.array([0.,10.,20.]));np.testing.assert_array_equal(x,[0,1]);np.testing.assert_array_equal(y,[5,20])
    def test_negative_prices_retained(self):
        x,y=fit_curve(np.array([0.,1.]),np.array([-50.,100.]));self.assertEqual(y[0],-50.)
    def test_missing_training_prices_not_zero_filled(self):
        x,y=fit_curve(np.array([0.,1.,2.]),np.array([0.,np.nan,20.]));np.testing.assert_array_equal(x,[0,2])
    def test_unseen_inputs_clip_without_using_evaluation_targets(self):
        x,y=fit_curve(np.array([0.,1.]),np.array([10.,20.]));np.testing.assert_array_equal(np.interp([-1,2],x,y),[10,20])

if __name__=='__main__':unittest.main()
