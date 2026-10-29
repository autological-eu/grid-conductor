"""Run fresh monthly fits with the compact, versioned research implementation."""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path

import numpy as np

from .fit import fit
from .network import transport_corridors
from .roots import ObservedPriceMultistartMarket
from .source import ROOT, digest, grouped_fit_inputs, observed_flow_snapshot

OUTPUT = ROOT / 'data/eu-market/flow-adjusted-clearing-2025/compact-fit-v1'


def run(months, output=OUTPUT):
    schema, data, _ = grouped_fit_inputs()
    edges, lower, upper = transport_corridors(schema['zones'], data)
    flow, mask, missing = observed_flow_snapshot(edges, schema['zones'])
    market = ObservedPriceMultistartMarket(
        schema['zones'], schema['groups'], lower, upper, edges,
        data['capacity'] / 1000, data['source_cost'], data['load'] / 1000,
        observed_prices=data['observed_prices'])
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'job.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        inputs = [
            ROOT / 'data/bidding-zone-network-2025/sigmoid-month-pairs-v1/inputs.npz',
            ROOT / 'data/bidding-zone-network-2025/sigmoid-month-pairs-v1/network.npz',
            ROOT / 'data/bidding-zone-network-2025/solar-country-fit-v1/delta.npz',
            ROOT / 'data/bidding-zone-network-2025/annual-solar-alignment-v1/inputs.npz',
            ROOT / 'data/bidding-zone-network-2025/annual-solar-alignment-v1/native.nc',
            ROOT / 'data/eu-market/flow-adjusted-clearing-2025/aligned-mixed-flow-observed-root-v1-u20-r1/audit.json',
        ] + [path for path in sorted(Path(__file__).parent.glob('*.py')) if path.name != 'verify.py']
        manifest = dict(protocol='compact-monthly-local-hour-u20-r1',
                        sources={str(path.relative_to(ROOT)): digest(path) for path in inputs})
        path = output / 'inputs.json'
        if path.exists() and json.loads(path.read_text()) != manifest:
            raise ValueError('Compact fit provenance changed')
        if not path.exists():
            path.write_text(json.dumps(manifest, indent=2) + '\n')
        for month in months:
            if month < 1 or month > 12:
                raise ValueError('Invalid month')
            folder = output / f'month-{month:02d}'
            if (folder / 'curves.npz').exists():
                raise ValueError(f'Month {month} already complete; refusing duplicate job')
            folder.mkdir(exist_ok=True)
            summary, weights, _ = fit(month, 20, 1.0, market, schema, data, flow, mask,
                                      missing, folder)
            np.savez_compressed(folder / 'curves.npz', weights=weights)
            summary['curves_sha256'] = digest(folder / 'curves.npz')
            (folder / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('months', nargs='+', type=int)
    args = parser.parse_args()
    run(args.months)
