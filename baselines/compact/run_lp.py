"""Clear a fresh compact-fit annual LP without changing the retained baseline."""
from __future__ import annotations

import argparse
import fcntl
import json
import time
from pathlib import Path

import numpy as np

from .evaluation import physical_lp, transferred_costs
from .lp import clear_hour, solver
from .network import transport_corridors
from .roots import ObservedPriceMultistartMarket
from .source import ROOT, digest, grouped_fit_inputs

OUTPUT = ROOT / 'data/bidding-zone-network-2025/compact-joint-lp-v1'


def run(fit_dir, output=OUTPUT):
    schema, data, _ = grouped_fit_inputs()
    edges, lower, upper = transport_corridors(schema['zones'], data)
    market = ObservedPriceMultistartMarket(
        schema['zones'], schema['groups'], lower, upper, edges,
        data['capacity'] / 1000, data['source_cost'], data['load'] / 1000,
        observed_prices=data['observed_prices'])
    model = physical_lp()
    fit_manifest = json.loads((fit_dir / 'inputs.json').read_text())
    if fit_manifest['protocol'] != 'compact-monthly-local-hour-u20-r1':
        raise ValueError('Unrecognized fit protocol')
    for relative, expected in fit_manifest['sources'].items():
        path = ROOT / relative
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f'Changed fitted source: {relative}')
    curve_paths = [fit_dir / f'month-{month:02d}/curves.npz' for month in range(1, 13)]
    for path in curve_paths:
        summary = json.loads((path.parent / 'summary.json').read_text())
        if digest(path) != summary['curves_sha256']:
            raise ValueError(f'Changed monthly curve: {path}')
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'job.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (output / 'annual.npz').exists():
            raise ValueError('Annual output exists; refusing duplicate solve')
        costs = transferred_costs(schema, data, market, model, fit_dir)
        highs = solver(model, costs)
        values = np.empty((8760, model['A'].shape[1]))
        duals = np.empty((8760, model['A'].shape[0]))
        objectives = np.empty(8760)
        maximum_residual = 0.0
        started = time.perf_counter()
        for hour in range(8760):
            values[hour], duals[hour], objectives[hour], error = clear_hour(highs, model, costs, hour)
            maximum_residual = max(maximum_residual, error)
        np.savez_compressed(output / 'annual.npz', values=values, row_duals=duals,
                            objectives=objectives, optimal=np.ones(8760, bool), hours=np.arange(8760))
        summary = dict(status='research_candidate_not_accepted', hours=8760,
                       maximum_primal_residual_mw=maximum_residual,
                       solve_seconds=time.perf_counter() - started,
                       witness_sha256=digest(output / 'annual.npz'),
                       fit_manifest_sha256=digest(fit_dir / 'inputs.json'),
                       curves_sha256={str(path.relative_to(fit_dir)): digest(path) for path in curve_paths})
        (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('fit_dir', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.fit_dir), indent=2))
