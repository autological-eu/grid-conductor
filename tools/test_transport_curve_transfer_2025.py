import unittest
import numpy as np
from transport_curve_physical_transfer_2025 import bids_from_anchors


class CurveTransferTests(unittest.TestCase):
    def test_exact_integrated_offer_and_monotonicity(self):
        nodes = np.array([[[2., 5., 17., 18., 31., 70.]]])
        for bins in [20, 100]:
            bids = bids_from_anchors(nodes, bins)
            self.assertTrue((np.diff(bids, axis=-1) > 0).all())
            # Integral of the learned PWL marginal offer over full output.
            self.assertAlmostEqual(float(bids.mean()),
                                   float(np.trapezoid(nodes[0, 0], dx=.2)), places=12)
            for k in range(5):
                self.assertAlmostEqual(float(bids[..., k*bins//5:(k+1)*bins//5].mean()),
                                       float(nodes[0, 0, k:k+2].mean()), places=12)

    def test_zero_bid_technical_slope_and_hour_identity(self):
        nodes = np.stack([np.linspace(0, .01, 6), np.linspace(10, 30, 6)])[:, None]
        bids = bids_from_anchors(nodes, 20)
        self.assertEqual(bids.shape, (2, 1, 20))
        np.testing.assert_allclose(bids[0, 0], .01*(np.arange(20)+.5)/20)
        self.assertGreater(bids[1].min(), bids[0].max())
        with self.assertRaises(ValueError):
            bids_from_anchors(nodes, 19)


if __name__ == '__main__':
    unittest.main()
