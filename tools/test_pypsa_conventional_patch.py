import unittest
from patch_pypsa_conventional import patch, OLD, NEW


class ConventionalPatchTests(unittest.TestCase):
    def test_adds_keyerror_fallback(self):
        result = patch(OLD)
        self.assertIn('except (ValueError, TypeError, KeyError):', result)
        self.assertNotIn(OLD, result)
        self.assertEqual(patch(result), result)

    def test_noop_when_already_patched(self):
        source = 'prefix\n' + NEW + 'suffix\n'
        self.assertEqual(patch(source), source)

    def test_unknown_upstream_fails_closed(self):
        with self.assertRaises(ValueError):
            patch('changed upstream code')


if __name__ == '__main__':
    unittest.main()