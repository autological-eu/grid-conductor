"""Prepare a new search run from immutable, independently replayed donor evidence.

This changes search settings only. It does not solve dispatch, alter storage
physics, relax convergence gates, or treat candidate exhaustion as convergence.
Seed directories are local symlinks: large witnesses stay outside Git and are
not copied. The existing driver rechecks donor hashes before every adoption.
"""
import argparse
from contextlib import ExitStack
import fcntl
from importlib.metadata import version
import json
from pathlib import Path

import numpy as np

from monthly_dispatch import digest, save
from submonthly_inventory_driver import FILES, active_jobs, read, verify_annual, verify_master
from submonthly_objective_donor import load as load_objective
from submonthly_feasibility_donor import load as load_feasibility


def settings(weight, candidates):
    if not np.isfinite(weight) or not 0 < weight <= 1 or not 1 <= candidates <= 200:
        raise ValueError('Finite positive search weight and finite candidate budget required')


def source_signature(root, source, domain_hash):
    record = read(root / 'driver-manifest.json')
    tools = Path(__file__).parent
    expected = {name: digest(tools / name) for name in FILES}
    if (not record or record['input_sha256'] != source
            or record['domain_sha256'] != domain_hash
            or record['producer_sha256'] != digest(tools / 'submonthly_inventory_driver.py')
            or record['dependencies'] != expected
            or record['packages'] != {name: version(name) for name in ['numpy', 'scipy', 'pypsa', 'highspy']}):
        raise ValueError('Donor source, calculation or package fingerprint differs')
    for field in ['seed_feasibility', 'seed_submonthly_feasibility']:
        for path, value in record[field].items():
            if digest(Path(path)) != value:
                raise ValueError('Original seed feasibility evidence changed')
    return record


def inspect(args):
    """Read stable replayed evidence only; inspection never authorizes a new job."""
    settings(args.proposal_weight, args.max_candidates)
    source = digest(args.input)
    domain_path = args.workspace / 'master-workspace.json'
    domain = read(domain_path)
    if not domain or domain['input_sha256'] != source or domain['year'] != 2025:
        raise ValueError('Source-matched 2025 domain required')
    with np.load(args.workspace / 'master-state.npz', allow_pickle=False) as state:
        anchor = state['warm_state_mwh'].copy()
    folders = []
    roots = []
    seen = set()
    lower = 0.
    upper = float(domain['annual_feasible_cost_eur'])
    seed_feasibility = {}
    seed_submonthly_feasibility = {}
    for root in args.source_root:
        signature = source_signature(root, source, digest(domain_path))
        roots.append(dict(path=str(root.resolve()), manifest_sha256=digest(root / 'driver-manifest.json'),
                          observed_status=read(root / 'driver-status.json'), proposal_weight=signature['proposal_weight']))
        for field, target in [('seed_feasibility', seed_feasibility),
                              ('seed_submonthly_feasibility', seed_submonthly_feasibility)]:
            target.update(signature[field])
        for folder in sorted(root.glob('candidate-*')):
            if not folder.is_dir() or folder.resolve() in seen:
                continue
            # A master alone supplies a lower support, never a dispatch witness.
            master = folder / 'master.json'
            if not master.with_suffix('.dual-replay.json').exists():
                continue
            bound = verify_master(master, source)
            lower = max(lower, bound)
            evidence = {}
            objective_count = feasibility_count = 0
            for path in sorted(folder.glob('[0-9][0-9]/independent-replay.json')):
                _, donor = load_objective(path, domain)
                if read(path)['master_sha256'] != digest(master):
                    raise ValueError('Donor economic witness uses another master')
                evidence[str(path.relative_to(folder))] = donor['sha256']
                objective_count += 1
            for path in sorted(folder.glob('phase-*/independent-replay.json')):
                _, _, donor = load_feasibility(path, domain, anchor)
                evidence[str(path.relative_to(folder))] = donor['sha256']
                feasibility_count += 1
            annual_cost = None
            if (folder / 'annual-replay.json').exists():
                annual_cost = verify_annual(folder, domain)
                upper = min(upper, annual_cost)
                evidence['annual-replay.json'] = digest(folder / 'annual-replay.json')
            # Partial *replayed* supports may be adopted, but not an annual cost.
            if objective_count or feasibility_count:
                folders.append(dict(path=str(folder.resolve()), master_sha256=digest(master),
                                    lower_support_eur=bound, objective_cuts=objective_count,
                                    feasibility_cuts=feasibility_count, annual_feasible_cost_eur=annual_cost,
                                    evidence=evidence))
                seen.add(folder.resolve())
    if not folders or not any(row['annual_feasible_cost_eur'] is not None for row in folders):
        raise ValueError('At least one independently replayed complete annual donor required')
    if lower > upper + 1e-7:
        raise ValueError('Replayed lower support exceeds annual feasible incumbent')
    # Keep the exact old convergence gates; a changed search step is no waiver.
    signatures = [read(root / 'driver-manifest.json') for root in args.source_root]
    gates = {(row['absolute_gap'], row['relative_gap']) for row in signatures}
    if len(gates) != 1:
        raise ValueError('Donors have different convergence settings')
    absolute, relative = gates.pop()
    if not 0 <= absolute < 1 or not 0 <= relative <= 1e-9:
        raise ValueError('Unsupported donor convergence gates')
    command = [str(Path(__file__).parent / 'submonthly_inventory_driver.py')]
    for name in ['input', 'workspace', 'calendar', 'monthly', 'support', 'warm', 'annual']:
        command += ['--' + name, str(getattr(args, name).resolve())]
    command += ['--root', str(args.output.resolve()), '--proposal-weight', str(args.proposal_weight),
                '--max-candidates', str(args.max_candidates), '--absolute-gap', str(absolute),
                '--relative-gap', str(relative)]
    for field, flag in [(seed_feasibility, '--feasibility'),
                        (seed_submonthly_feasibility, '--submonthly-feasibility')]:
        for path in sorted(field):
            command += [flag, path]
    return dict(status='replayed_continuation_plan_not_started', input_sha256=source,
                domain_sha256=digest(domain_path), roots=roots, donors=folders,
                prior_lower_support_eur=lower, prior_annual_feasible_cost_eur=upper,
                prior_gap_eur=upper-lower, proposal_weight=args.proposal_weight,
                max_candidates=args.max_candidates, absolute_gap=absolute, relative_gap=relative,
                driver_arguments=command, producer_sha256=digest(Path(__file__)),
                scope='Search continuation only; same original availability, chronological domain and convergence gates. No annual optimum, empirical validation or investment result.')


def prepare(args):
    if args.output.exists():
        raise ValueError('Preserve existing continuation evidence; use a new output')
    if any(args.output.resolve().is_relative_to(path.resolve()) for path in args.source_root):
        raise ValueError('Continuation must not modify a donor tree')
    # Acquire the original drivers' actual locks. Stale status never proves idle.
    with ExitStack() as stack:
        for root in sorted(set(path.resolve() for path in args.source_root)):
            lock = stack.enter_context((root / 'driver.lock').open('a+'))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if active_jobs():
            raise ValueError('A research worker is live; no continuation prepared')
        for root in args.source_root:
            status = read(root / 'driver-status.json')
            if not status or status.get('status') != 'candidate_limit_not_converged':
                raise ValueError('Only reviewed finite-budget exhaustion may seed a continuation')
        plan = inspect(args)
        args.output.mkdir(parents=True, exist_ok=False)
        for index, donor in enumerate(plan['donors']):
            (args.output / f'candidate-seed-{index:03d}').symlink_to(donor['path'], target_is_directory=True)
        plan['status'] = 'replayed_continuation_prepared_not_started'
        save(args.output / 'continuation-manifest.json', plan)
    return plan


def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['input', 'workspace', 'calendar', 'monthly', 'support', 'warm', 'annual', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--source-root', type=Path, action='append', required=True)
    parser.add_argument('--proposal-weight', type=float, required=True)
    parser.add_argument('--max-candidates', type=int, default=10)
    return parser


if __name__ == '__main__':
    parser = argument_parser()
    parser.add_argument('--inspect-only', action='store_true', help='Read-only verification; never prepares or starts another job')
    args = parser.parse_args()
    result = inspect(args) if args.inspect_only else prepare(args)
    print(json.dumps({key: result[key] for key in ['status', 'proposal_weight', 'max_candidates',
          'prior_lower_support_eur', 'prior_annual_feasible_cost_eur', 'prior_gap_eur']}))
