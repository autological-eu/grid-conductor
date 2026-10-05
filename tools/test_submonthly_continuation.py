"""Continuation must preserve evidence, locks and the unrestricted bound."""
import fcntl
from importlib.metadata import version
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse
from scipy.optimize import linprog

import prepare_submonthly_continuation as module
from grouped_storage_master import solve
from storage_coordinator import Block, solve_block
from submonthly_proposal import stabilise
from run_submonthly_continuation import wait_action


class ContinuationSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.donor = self.root / 'donor'
        self.donor.mkdir()
        self.output = self.root / 'next'
        self.args = SimpleNamespace(source_root=[self.donor], output=self.output)
        (self.donor / 'driver-status.json').write_text(json.dumps(dict(status='candidate_limit_not_converged')))

    def test_existing_output_is_preserved(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, 'Preserve existing'):
            module.prepare(self.args)

    def test_donor_tree_cannot_be_changed(self):
        self.args.output = self.donor / 'new'
        with self.assertRaisesRegex(ValueError, 'donor tree'):
            module.prepare(self.args)

    def test_actual_lock_overrides_terminal_status(self):
        with (self.donor / 'driver.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                module.prepare(self.args)
        self.assertFalse(self.output.exists())

    def test_live_worker_overrides_stale_terminal_status(self):
        with patch.object(module, 'active_jobs', return_value=[123]):
            with self.assertRaisesRegex(ValueError, 'worker is live'):
                module.prepare(self.args)
        self.assertFalse(self.output.exists())

    def test_failed_worker_is_not_budget_exhaustion(self):
        (self.donor / 'driver-status.json').write_text(json.dumps(dict(status='failed_requires_review')))
        with patch.object(module, 'active_jobs', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'finite-budget exhaustion'):
                module.prepare(self.args)

    def test_only_checked_donors_are_linked_without_copying(self):
        folder = self.donor / 'candidate-001'
        folder.mkdir()
        witness = folder / 'witness.npz'
        witness.write_bytes(b'preserve-original')
        plan = dict(donors=[dict(path=str(folder))], scope='not an annual optimum')
        with patch.object(module, 'active_jobs', return_value=[]), patch.object(module, 'inspect', return_value=plan):
            result = module.prepare(self.args)
        seed = self.output / 'candidate-seed-000'
        self.assertTrue(seed.is_symlink())
        self.assertEqual(seed.resolve(), folder)
        self.assertEqual((seed / 'witness.npz').read_bytes(), b'preserve-original')
        self.assertEqual(result['status'], 'replayed_continuation_prepared_not_started')
        self.assertFalse((self.output / 'driver-status.json').exists())

    def test_invalid_search_weights_rejected(self):
        for weight in [0, -1, 1.1, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                module.settings(weight, 10)

    def test_bounded_wait_cannot_restart_disappeared_or_failed_jobs(self):
        self.assertEqual(wait_action([dict(status='executing')], []), 'review')
        self.assertEqual(wait_action([dict(status='executing')], [123]), 'wait')
        self.assertEqual(wait_action([dict(status='candidate_limit_not_converged')], [123]), 'wait')
        self.assertEqual(wait_action([dict(status='candidate_limit_not_converged')], []), 'prepare')
        for status in ['failed_requires_review', 'blocked_requires_review', 'numerical_gap_gate_met_requires_annual_validation']:
            self.assertEqual(wait_action([dict(status=status)], [123]), 'review')
        self.assertEqual(wait_action([None], []), 'review')

    def test_source_and_seed_fingerprints_cannot_be_relabelled(self):
        tools = Path(module.__file__).parent
        record = dict(input_sha256='source', domain_sha256='domain',
                      producer_sha256=module.digest(tools/'submonthly_inventory_driver.py'),
                      dependencies={name: module.digest(tools/name) for name in module.FILES},
                      packages={name: version(name) for name in ['numpy', 'scipy', 'pypsa', 'highspy']},
                      seed_feasibility={}, seed_submonthly_feasibility={})
        path = self.donor/'driver-manifest.json'
        path.write_text(json.dumps(record))
        self.assertEqual(module.source_signature(self.donor, 'source', 'domain'), record)
        with self.assertRaisesRegex(ValueError, 'fingerprint differs'):
            module.source_signature(self.donor, 'another-source', 'domain')
        seed = self.donor/'seed.json'
        seed.write_text('{}')
        record['seed_feasibility'] = {str(seed): module.digest(seed)}
        path.write_text(json.dumps(record))
        seed.write_text('{"changed": true}')
        with self.assertRaisesRegex(ValueError, 'seed feasibility evidence changed'):
            module.source_signature(self.donor, 'source', 'domain')


class SearchStepReferenceTests(unittest.TestCase):
    def test_fixed_anchor_damping_can_stall_without_changing_the_bound(self):
        # Two chronological blocks: free energy first, expensive demand second.
        # Original generation availability is held fixed in every calculation.
        blocks = []
        for t, (price, demand) in enumerate([(0., 5.), (100., 15.)]):
            coupling = np.zeros((2, 3))
            coupling[1, t] = 1.
            coupling[1, t+1] = -1.
            blocks.append(Block(np.array([price, 0., 0.]), [(0., 20.), (0., 10.), (0., 10.)],
                                sparse.csr_matrix([[1., -1., 1.], [0., 1., -1.]]),
                                np.array([demand, 0.]), sparse.csr_matrix(coupling)))
        equality = sparse.csr_matrix([[1., 0., -1.]])
        bounds = [(0., 10.)] * 3
        anchor = np.zeros(3)
        cuts = []
        for index, block in enumerate(blocks):
            local, gradient = solve_block(block, anchor)
            self.assertIsNotNone(local)
            cuts.append(([index], gradient, local.fun - gradient @ anchor))
        master = solve(bounds, equality, [0.], sparse.csr_matrix((0, 3)), [], [0., 0.], cuts, anchor,
                       include_equalities=True)
        matrix = np.zeros((5, 9))
        rhs = np.zeros(5)
        for index, block in enumerate(blocks):
            matrix[2*index:2*index+2, 3*index:3*index+3] = block.equality.toarray()
            matrix[2*index:2*index+2, 6:] = block.coupling.toarray()
            rhs[2*index:2*index+2] = block.rhs
        matrix[-1, 6:] = equality.toarray()[0]
        mono = linprog(np.r_[blocks[0].cost, blocks[1].cost, np.zeros(3)], A_eq=matrix, b_eq=rhs,
                       bounds=blocks[0].bounds+blocks[1].bounds+bounds, method='highs')
        self.assertTrue(mono.success)
        self.assertAlmostEqual(mono.fun, 500.)
        self.assertLessEqual(master['lower_bound_eur'], mono.fun + 1e-7)
        costs = {}
        for weight in [.01, .1, .5, 1.]:
            point = stabilise(master['proposal_mwh'], anchor, weight, bounds, equality, [0.],
                              sparse.csr_matrix((0, 3)), [])
            costs[weight] = sum(solve_block(block, point)[0].fun for block in blocks)
        self.assertAlmostEqual(costs[1.], mono.fun)
        self.assertAlmostEqual(costs[.5], 1000.)
        self.assertAlmostEqual(costs[.01], 1490.)
        self.assertAlmostEqual(costs[.1], 1400.)
        # Changing proposal damping cannot relabel a persistent gap as optimal.
        self.assertGreater(costs[.01] - master['lower_bound_eur'], 989.)


if __name__ == '__main__':
    unittest.main()
