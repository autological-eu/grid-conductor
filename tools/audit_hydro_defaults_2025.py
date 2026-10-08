"""Replay original inflows through native PyPSA and record effective storage defaults."""
import argparse
import json
from pathlib import Path
import numpy as np
import pypsa
from hourly_renewable_estimates import digest

FIELDS = ['p_nom', 'max_hours', 'p_min_pu', 'p_max_pu', 'efficiency_store',
          'efficiency_dispatch', 'standing_loss', 'state_of_charge_initial',
          'cyclic_state_of_charge', 'cyclic_state_of_charge_per_period',
          'state_of_charge_initial_per_period', 'p_nom_extendable']


def audit(network, bundle, output):
    if output.exists():
        raise ValueError('Use a fresh audit path')
    summary_path = bundle / 'summary.json'
    summary = json.loads(summary_path.read_text())
    if digest(network) != summary['network_sha256']:
        raise ValueError('Network hash mismatch')
    if digest(bundle / 'hourly.npz') != summary['hourly_sha256']:
        raise ValueError('Inflow bundle hash mismatch')
    n = pypsa.Network(network)
    hydro = n.storage_units[n.storage_units.carrier == 'hydro']
    with np.load(bundle / 'hourly.npz', allow_pickle=False) as a:
        ids = a['reservoir_ids'].tolist()
        if len(ids) != len(set(ids)) or set(ids) != set(hydro.index):
            raise ValueError('Reservoir identity mismatch')
        np.testing.assert_array_equal(a['hours_utc'], n.snapshots.values)
        np.testing.assert_array_equal(a['inflow_mw'], n.storage_units_t.inflow[ids].values)
    temporal = {key: list(frame.columns) for key, frame in n.storage_units_t.items()
                if len(frame.columns)}
    if set(temporal) != {'inflow'}:
        raise ValueError('Additional temporal storage physics require a dedicated exporter')
    rows = []
    if [r['id'] for r in summary['reservoirs']] != ids:
        raise ValueError('Summary identity order mismatch')
    for original in summary['reservoirs']:
        identity = original['id']
        for key, value in original['source_parameters'].items():
            if n.storage_units.loc[identity, key] != value:
                raise ValueError(f'Native static parameter mismatch: {identity}/{key}')
        effective = {key: hydro.loc[identity, key].item()
                     if hasattr(hydro.loc[identity, key], 'item')
                     else hydro.loc[identity, key] for key in FIELDS}
        rows.append(dict(id=identity, effective_parameters=effective,
                         defaulted_fields=[key for key in FIELDS
                                           if key not in original['source_parameters']],
                         energy_capacity_mwh=effective['p_nom'] * effective['max_hours']))
    report = dict(status='native_storage_defaults_audit_not_zonal_acceptance',
                  network_sha256=digest(network), bundle_summary_sha256=digest(summary_path),
                  hourly_sha256=summary['hourly_sha256'], producer_sha256=digest(__file__),
                  pypsa_version=pypsa.__version__, hours=len(n.snapshots), reservoirs=rows,
                  nonempty_temporal_fields=temporal,
                  zero_energy_capacity_reservoirs=[r['id'] for r in rows if r['energy_capacity_mwh'] == 0],
                  limitations=['Defaults are effective values under the recorded native PyPSA version.',
                               'Cyclic flags do not imply empty annual boundary inventories; retained trial boundaries remain separate.',
                               'Zero-energy reservoirs are retained, not removed or assigned invented storage.',
                               'No optimisation, observed-water validation, zone mapping or pooling performed.'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(f'Native replay passed: {len(rows)} reservoirs, {len(n.snapshots)} hours; '
          f"{len(report['zero_energy_capacity_reservoirs'])} zero-energy reservoirs preserved.")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--network', type=Path, required=True)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    audit(a.network, a.bundle, a.output)
