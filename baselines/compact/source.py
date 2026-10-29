"""Load and aggregate the retained 2025 fit inputs without experiment drivers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import hstack, load_npz

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'data/bidding-zone-network-2025/sigmoid-month-pairs-v1'
SOLAR = ROOT / 'data/bidding-zone-network-2025/solar-country-fit-v1/delta.npz'
PHYSICAL = ROOT / 'data/bidding-zone-network-2025/annual-solar-alignment-v1/inputs.npz'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grouped_fit_inputs():
    """Return the 326 zonal technology groups and original physical columns.

    This is a new loader for an unchanged source snapshot. It does not modify
    historical source-hashed producers or promote a new research baseline.
    """
    sealed = json.loads((SOURCE / 'inputs.json').read_text())
    for field, file in [('input_sha256', 'inputs.npz'), ('network_sha256', 'network.npz')]:
        if digest(SOURCE / file) != sealed[field]:
            raise ValueError(f'Changed fit source {file}')
    with np.load(SOURCE / 'inputs.npz') as archive:
        data = {key: archive[key] for key in archive.files}
    old_matrix = load_npz(SOURCE / 'network.npz')
    original = sealed['groups']
    keys = sorted({(g['zone'], g['technology']) for g in original})
    mapping = np.array([keys.index((g['zone'], g['technology'])) for g in original])
    count = len(keys)
    capacity = np.zeros((8760, count))
    weighted = np.zeros_like(capacity)
    columns = []
    segments = sealed['design']['segments']
    groups = []
    for group_id, key in enumerate(keys):
        ids = np.flatnonzero(mapping == group_id)
        first = int(ids[0]) * segments
        columns.append(first)
        for j in ids[1:]:
            if (old_matrix[:, int(j) * segments] - old_matrix[:, first]).nnz:
                raise ValueError('Cannot merge groups with different network columns')
        group = original[ids[0]].copy()
        group['parameter'] = group_id
        groups.append(group)
        capacity[:, group_id] = data['capacity'][:, ids].sum(axis=1)
        weighted[:, group_id] = (data['capacity'][:, ids] * data['source_cost'][:, ids]).sum(axis=1)
    source_cost = np.divide(weighted, capacity, out=np.zeros_like(weighted), where=capacity > 0)
    with np.load(SOLAR) as archive:
        solar_delta = archive['delta']
    with np.load(PHYSICAL) as archive:
        offer_zones = archive['offer_zones'].astype(str)
    for zone in sealed['zones']:
        ids = [i for i, g in enumerate(groups) if g['zone'] == zone and g['technology'] == 'solar']
        delta = solar_delta[:, offer_zones == zone].sum(axis=1)
        if not ids:
            if np.max(abs(delta)) > 1e-7:
                raise ValueError(f'Unmatched solar correction {zone}')
            continue
        if len(ids) != 1:
            raise ValueError(f'Ambiguous solar group {zone}')
        capacity[:, ids[0]] += delta
    if capacity.min() < -1e-5:
        raise ValueError('Negative available capacity')
    grouped = sealed | dict(groups=groups, parameters=[list(key) for key in keys],
                            original_groups=original, mapping=mapping.tolist())
    adapted = data | dict(capacity=capacity, source_cost=source_cost)
    matrix = hstack([old_matrix[:, columns], old_matrix[:, sealed['ng']:]], format='csc')
    return grouped, adapted, matrix


def observed_flow_snapshot(edges, zones):
    """Load the audited hourly A09 target cells from retained monthly receipts.

    The flow target is commercial exchange; the independent model flow in the
    same files is deliberately ignored. Missing A09 cells remain missing.
    """
    folder = ROOT / 'data/eu-market/flow-adjusted-clearing-2025/aligned-mixed-flow-observed-root-v1-u20-r1'
    metadata = json.loads((folder / 'flow-metadata.json').read_text())
    if metadata['zones'] != zones or metadata['corridor_count'] != len(edges):
        raise ValueError('Observed-flow corridor metadata changed')
    if list(zip(metadata['from_zone'], metadata['to_zone'])) != [
        (zones[i], zones[j]) for i, j in edges]:
        raise ValueError('Observed-flow edge order changed')
    observed, covered = [], []
    records = json.loads((folder / 'audit.json').read_text())['records']
    for month in range(1, 13):
        path = folder / f'month-{month:02d}/inferred-flows.npz'
        if records[month - 1]['month'] != month or digest(path) != records[month - 1]['inferred_flows_sha256']:
            raise ValueError(f'Observed-flow receipt changed for month {month}')
        with np.load(path) as archive:
            observed.append(archive['observed_a09_gw'])
            covered.append(archive['observed_within_model_bounds'])
    flows, mask = np.concatenate(observed), np.concatenate(covered)
    zone_covered = np.ones((8760, len(zones)), dtype=bool)
    for k, (i, j) in enumerate(edges):
        zone_covered[:, i] &= np.isfinite(flows[:, k])
        zone_covered[:, j] &= np.isfinite(flows[:, k])
    return flows, mask, ~zone_covered
