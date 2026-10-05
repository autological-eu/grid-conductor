"""Bounded wait for finite-budget exhaustion, then one verified search continuation.

No old solve is restarted. A disappeared driver, failed job, met numerical gate,
or wait timeout stops for review. The continuation starts only after checked
preparation acquires original locks and confirms no live research workers.
"""
import fcntl
import os
from pathlib import Path
import sys
import time

from monthly_dispatch import digest, save
from prepare_submonthly_continuation import argument_parser, prepare, settings, source_signature
from submonthly_inventory_driver import active_jobs, read


def wait_action(statuses, jobs):
    if any(not row or row.get('status') in ['failed_requires_review', 'blocked_requires_review',
           'numerical_gap_gate_met_requires_annual_validation'] for row in statuses):
        return 'review'
    if jobs:
        return 'wait'
    if all(row.get('status') == 'candidate_limit_not_converged' for row in statuses):
        return 'prepare'
    # An executing status without a live worker is not an authorization to rerun.
    return 'review'


def run(args):
    settings(args.proposal_weight, args.max_candidates)
    if args.output.exists() or not 0 < args.wait_seconds <= 24*3600:
        raise ValueError('New output and positive bounded wait at most 24 hours required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    lock_path = args.output.with_suffix('.waiting.lock')
    status_path = args.output.with_suffix('.waiting.json')
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source = digest(args.input)
        domain = digest(args.workspace / 'master-workspace.json')
        signatures = [source_signature(root, source, domain) for root in args.source_root]
        started = time.monotonic()
        while True:
            if digest(args.workspace / 'master-workspace.json') != domain:
                raise ValueError('Waiting inventory domain changed')
            for root, signature in zip(args.source_root, signatures):
                if read(root / 'driver-manifest.json') != signature:
                    raise ValueError('Waiting source driver settings changed')
            statuses = [read(root / 'driver-status.json') for root in args.source_root]
            jobs = active_jobs()
            action = wait_action(statuses, jobs)
            save(status_path, dict(status='waiting_for_original_finite_pass' if action == 'wait' else action,
                                  pid=os.getpid(), active_research_pids=jobs,
                                  elapsed_seconds=time.monotonic()-started,
                                  proposal_weight=args.proposal_weight, max_candidates=args.max_candidates,
                                  source_input_sha256=source, producer_sha256=digest(Path(__file__))))
            if action == 'review':
                raise ValueError('Original pass requires review; no continuation started')
            if action == 'prepare':
                plan = prepare(args)
                save(status_path, dict(status='continuation_prepared_starting_driver', pid=os.getpid(),
                                      continuation_manifest_sha256=digest(args.output / 'continuation-manifest.json'),
                                      producer_sha256=digest(Path(__file__))))
                # Replace this supervisor with the unchanged driver. Its own
                # lock/frozen signature/worker gates protect the subsequent run.
                os.execv(sys.executable, [sys.executable]+plan['driver_arguments'])
            if time.monotonic()-started >= args.wait_seconds:
                save(status_path, dict(status='wait_limit_requires_review', pid=os.getpid(),
                                      producer_sha256=digest(Path(__file__))))
                raise ValueError('Wait budget exhausted; no continuation started')
            time.sleep(max(0., min(30., args.wait_seconds-(time.monotonic()-started))))


if __name__ == '__main__':
    parser = argument_parser()
    parser.description = __doc__
    parser.add_argument('--wait-seconds', type=float, default=6*3600)
    run(parser.parse_args())
