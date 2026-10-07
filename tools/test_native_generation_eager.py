import unittest
import numpy as np
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from compare_native_generation_eager import audit
from test_native_generation_observations import NativeObservations
from summarize_annual_native_generation import energy as original
from summarize_native_generation_eager import energy
from test_annual_native_generation import NativeGenerationAccounting


class CountingArrays(dict):
    def __init__(self, values):
        super().__init__(values)
        self.reads = {}

    def __getitem__(self, name):
        self.reads[name] = self.reads.get(name, 0) + 1
        return super().__getitem__(name)


class EagerGenerationTests(unittest.TestCase):
    def test_observation_audit_rejects_changed_producer_and_dependencies(self):
        native, observed = NativeObservations().fixture()
        for item in [native, observed]:
            item.update(producer_sha256='current', dependencies={'dependency.py': 'current'})
        native.update(input_sha256='source')
        with tempfile.TemporaryDirectory() as folder:
            args = SimpleNamespace(native=Path(folder)/'native.json', observed=Path(folder)/'observed.json')
            for field, value in [('native', native), ('observed', observed)]:
                getattr(args, field).write_text(json.dumps(value))
            with patch('compare_native_generation_eager.digest', return_value='current'):
                result = audit(args)
                self.assertEqual(result['comparisons'][0]['difference_mwh'], 24.)
                for change in ['producer_sha256', 'dependencies']:
                    modified = dict(native)
                    modified[change] = 'changed' if change == 'producer_sha256' else {'dependency.py': 'changed'}
                    args.native.write_text(json.dumps(modified))
                    with self.assertRaises(ValueError):
                        audit(args)

    def test_equations_match_original_and_arrays_load_once(self):
        arrays, record = NativeGenerationAccounting().fixture()
        counted = CountingArrays(arrays)
        self.assertEqual(energy(counted, record), original(arrays, record))
        self.assertEqual(counted.reads, {name: 1 for name in arrays})

    def test_invalid_or_oversized_blocks_fail(self):
        for change in ['nonfinite', 'shape', 'oversized']:
            arrays, record = NativeGenerationAccounting().fixture()
            if change == 'nonfinite':
                arrays['generation_mw'][0, 0] = np.nan
            elif change == 'shape':
                arrays['storage_charge_mw'] = np.zeros((2, 1))
            else:
                arrays = {name: np.repeat(value[:1], 169, axis=0) for name, value in arrays.items()}
            with self.assertRaises(ValueError):
                energy(arrays, record)


if __name__ == '__main__':
    unittest.main()
