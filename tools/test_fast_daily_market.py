"""Check the performance adapter against the independent original LP builder."""
import unittest
from unittest.mock import Mock
import numpy as np
import highspy
import test_simple_resource_bids as fixtures
from simple_resource_bids import configuration, prepare_storage, storage_bids
from simple_daily_market import daily_lp, clear_day as original_clear
from fast_daily_market import cached_daily_lp, clear_day, timed_optimal


class FastDailyTests(unittest.TestCase):
    def test_cached_coefficients_match_original_on_changed_day_and_inventory(self):
        for carrier in ('battery', 'PHS', 'hydro'):
            n, m, forecast = fixtures.SimpleRules().fixture(carrier)
            initial = np.array([0.]); terminal = initial.copy()
            prep = prepare_storage(n, m, forecast, initial, terminal, configuration())
            cache = None
            for start, current in ((0, initial), (24, np.array([1.]))):
                bids = storage_bids(n, m, start, start+24, current, terminal, prep, configuration())
                p, cache = cached_daily_lp(n, m, start, start+24, current, terminal, bids, cache)
                reference = daily_lp(n, m, start, start+24, current, terminal, bids)
                self.assertEqual((p['A'] != reference['A']).nnz, 0)
                for key, value in reference.items():
                    if isinstance(value, np.ndarray):
                        np.testing.assert_array_equal(p[key], value, err_msg=carrier+' '+key)

    def test_chronological_objectives_and_inventory_match_original(self):
        n, m, forecast = fixtures.SimpleRules().fixture()
        current = np.array([0.]); terminal = current.copy()
        prep = prepare_storage(n, m, forecast, current, terminal, configuration())
        cache = old_cache = None
        for start in (0, 24):
            bids = storage_bids(n, m, start, start+24, current, terminal, prep, configuration())
            result, cache = clear_day(n, m, start, start+24, current, terminal, bids, cache)
            reference, old_cache = original_clear(n, m, start, start+24, current, terminal, bids, old_cache)
            self.assertAlmostEqual(result['bid_objective_eur'], reference['bid_objective_eur'], places=7)
            np.testing.assert_allclose(result['values'], reference['values'], atol=1e-8, rtol=0)
            current = result['values'][-1, cache['template']['nb']+2:cache['template']['nb']+3]
        np.testing.assert_allclose(current, terminal, atol=1e-8)

    def test_each_retry_receives_a_fresh_cumulative_clock_budget(self):
        h = Mock()
        h.getRunTime.side_effect = [100., 102.]
        h.getModelStatus.side_effect = [highspy.HighsModelStatus.kTimeLimit, highspy.HighsModelStatus.kOptimal]
        h.getInfo.return_value.simplex_iteration_count = 1
        h.getInfo.return_value.ipm_iteration_count = 0
        _, attempts = timed_optimal(h, {}, 3)
        deadlines = [call.args[1] for call in h.setOptionValue.call_args_list if call.args[0] == 'time_limit']
        self.assertEqual(deadlines, [103., 105.])
        self.assertEqual(len(attempts), 2)
        h.clearSolver.assert_called_once()


    def test_adapter_provenance_and_exception_restore_original_producer(self):
        import json
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch
        import fast_daily_market as adapter
        original_clear = adapter.producer.clear_day
        original_write = adapter.producer.write_json
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            def interrupted(args):
                adapter.producer.write_json(args.output/'manifest.json', {'dependencies': {}})
                raise ValueError('injected producer failure')
            with patch.object(adapter.producer, 'run', side_effect=interrupted):
                with self.assertRaisesRegex(ValueError, 'injected producer failure'):
                    adapter.run(SimpleNamespace(output=output))
            manifest = json.loads((output/'manifest.json').read_text())
            self.assertEqual(manifest['execution_driver']['file'], 'fast_daily_market.py')
            self.assertEqual(manifest['dependencies']['fast_daily_market.py'],
                             manifest['execution_driver']['sha256'])
        self.assertIs(adapter.producer.clear_day, original_clear)
        self.assertIs(adapter.producer.write_json, original_write)


if __name__ == '__main__':
    unittest.main()
