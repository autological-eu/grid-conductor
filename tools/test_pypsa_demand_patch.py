import unittest
from patch_pypsa_demand import patch, OLD, ANCHOR, CHECK


class DemandPatchTests(unittest.TestCase):
    def test_moves_gate_after_window_selection(self):
        source = 'prefix\n'+OLD+'    fixed_year = False\n'+ANCHOR+'suffix\n'
        result = patch(source)
        self.assertNotIn(OLD, result)
        self.assertLess(result.index(ANCHOR), result.index(CHECK))
        self.assertEqual(patch(result), result)

    def test_unknown_upstream_fails_closed(self):
        with self.assertRaises(ValueError):
            patch('changed upstream code')


if __name__ == '__main__':
    unittest.main()
