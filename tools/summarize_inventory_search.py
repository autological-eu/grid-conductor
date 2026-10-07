"""Read-only verified numerical search evidence; not an optimum certificate.

Partial candidates may supply independently replayed lower supports, never an
annual feasible cost. Existing verifier equations and frozen inputs are reused.
"""
import argparse
import json
from pathlib import Path

from monthly_dispatch import digest
from prepare_submonthly_continuation import source_signature
from submonthly_inventory_driver import read, verify_annual, verify_master


def summarize(root, workspace):
    domain_path = workspace / 'master-workspace.json'
    domain = read(domain_path)
    source_signature(root, domain['input_sha256'], digest(domain_path))
    rows = []
    seen = set()
    for folder in sorted(root.glob('candidate-*')):
        if not folder.is_dir() or folder.resolve() in seen:
            continue
        seen.add(folder.resolve())
        master = folder / 'master.json'
        if not master.with_suffix('.dual-replay.json').exists():
            continue
        lower = verify_master(master, domain['input_sha256'])
        upper = verify_annual(folder, domain) if (folder / 'annual-replay.json').exists() else None
        rows.append(dict(candidate=folder.name, lower_support_eur=lower,
                         annual_feasible_cost_eur=upper))
    if not rows:
        raise ValueError('No independently replayable master evidence')
    feasible = [row for row in rows if row['annual_feasible_cost_eur'] is not None]
    best = min(feasible, key=lambda row: row['annual_feasible_cost_eur']) if feasible else None
    lower = max(rows, key=lambda row: row['lower_support_eur'])
    upper_value = best['annual_feasible_cost_eur'] if best else None
    return dict(scope='Verified numerical support and annual witness chains; no interval, optimum or empirical certificate.',
                input_sha256=domain['input_sha256'], candidates=rows,
                best_feasible=best, strongest_lower_support=lower,
                numerical_gap_percent=100 * (upper_value - lower['lower_support_eur']) / upper_value
                if upper_value is not None and upper_value > 0 else None,
                liveness='Not inspected; use inspect_inventory_processes.py separately.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(summarize(args.root, args.workspace), indent=2))
