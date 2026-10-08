"""Read-only boundary audit of the single retained annual reference; no solve."""
import argparse
import json
from pathlib import Path
import numpy as np
import pypsa
from monthly_dispatch import digest
from submonthly_inventory_driver import verify_annual


def check_calendar(blocks):
    """Require one ordered, gap-free full year; retain block boundary identities."""
    if not blocks:
        raise ValueError('Empty block calendar')
    cursor = 0
    boundaries = [0]
    for index, block in enumerate(blocks):
        start, end = block['start_hour'], block['end_hour_exclusive']
        if (block['index'] != index or not isinstance(start, int)
                or not isinstance(end, int) or start != cursor or end <= start
                or block['hours'] != end - start or end > 8760):
            raise ValueError('Unordered, overlapping or incomplete block calendar')
        cursor = end
        boundaries.append(end)
    if cursor != 8760:
        raise ValueError('Full 8760-hour calendar required')
    return boundaries


def check_boundaries(state, capacity, cyclic, tolerance=1e-6):
    if state.ndim != 2 or state.shape[1] != len(capacity) or len(cyclic) != len(capacity):
        raise ValueError('Inventory layout mismatch')
    if not np.isfinite(state).all() or not np.isfinite(capacity).all() or np.any(capacity < 0):
        raise ValueError('Invalid inventory/capacity')
    lower = float(np.maximum(-state, 0).max())
    upper = float(np.maximum(state - capacity, 0).max())
    closure = float(np.abs(state[0, cyclic] - state[-1, cyclic]).max()) if np.any(cyclic) else 0.
    if max(lower, upper, closure) > tolerance:
        raise ValueError('Boundary feasibility exceeds diagnostic tolerance')
    return dict(lower_bound_violation_mwh=lower, upper_bound_violation_mwh=upper,
                cyclic_closure_residual_mwh=closure, diagnostic_tolerance_mwh=tolerance)


def run(network, reference, workspace, output):
    if output.exists():
        raise ValueError('Use a fresh output path')
    domain = json.loads(workspace.read_text())
    if digest(network) != domain['input_sha256']:
        raise ValueError('Source hash mismatch')
    boundary_hours = check_calendar(domain['blocks'])
    cost = verify_annual(reference, domain)
    n = pypsa.Network(network)
    expected = np.datetime64('2025-01-01T00', 'ns') + np.arange(8760).astype('timedelta64[h]')
    np.testing.assert_array_equal(n.snapshots.values, expected)
    np.testing.assert_array_equal(n.snapshot_weightings.stores.values, np.ones(8760))
    ids = domain['storage_ids']
    if len(ids) != len(set(ids)) or set(ids) != set(n.storage_units.index):
        raise ValueError('Storage identity mismatch')
    storage = n.storage_units.loc[ids]
    with np.load(reference / 'annual-state.npz', allow_pickle=False) as a:
        state = a['inventories_mwh'].reshape(len(domain['blocks']) + 1, len(ids))
    capacity = (storage.p_nom * storage.max_hours).values
    cyclic = storage.cyclic_state_of_charge.values.astype(bool)
    metrics = check_boundaries(state, capacity, cyclic)
    rows = [dict(id=i, carrier=storage.loc[i, 'carrier'], energy_capacity_mwh=float(capacity[j]),
                 initial_mwh=float(state[0, j]), final_mwh=float(state[-1, j]),
                 minimum_boundary_mwh=float(state[:, j].min()),
                 maximum_boundary_mwh=float(state[:, j].max()), cyclic=bool(cyclic[j]))
            for j, i in enumerate(ids)]
    report = dict(status='retained_reference_boundary_diagnostic_not_annual_optimum',
                  network_sha256=digest(network), workspace_sha256=digest(workspace),
                  annual_state_sha256=digest(reference / 'annual-state.npz'),
                  annual_replay_sha256=digest(reference / 'annual-replay.json'),
                  producer_sha256=digest(Path(__file__)), pypsa_version=pypsa.__version__,
                  annual_feasible_cost_eur=cost, boundaries=state.shape[0], boundary_hours=boundary_hours,
                  boundary_times_utc=[str(np.datetime64('2025-01-01T00') + np.timedelta64(h, 'h')) + 'Z' for h in boundary_hours],
                  storage=rows,
                  nonzero_initial_inventory_count=int(np.count_nonzero(state[0] > 1e-6)),
                  metrics=metrics,
                  limitations=['Boundary diagnostic supplements the intact annual witness replay; does not replace hourly physics checks.',
                               'Fixed trial inventories are not newly optimised or empty initial conditions.',
                               'Numerical tolerance is diagnostic, not an empirical or annual-optimum acceptance gate.',
                               'No solve, storage pooling or zonal allocation performed.'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(f'Boundary audit passed: {len(ids)} storage units, {state.shape[0]} boundaries; '
          f"{report['nonzero_initial_inventory_count']} nonzero initial inventories.")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['network', 'reference', 'workspace', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    run(a.network, a.reference, a.workspace, a.output)
