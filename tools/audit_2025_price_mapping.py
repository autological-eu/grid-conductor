"""Inventory a provisional model-node/observed-price mapping; no validation claim.

Country labels alone cannot assign clustered nodes in split bidding-zone countries.
Those nodes remain unresolved until constituent-bus geography is audited.
"""
import argparse
import json
from pathlib import Path
from monthly_dispatch import digest, save

SPLIT_COUNTRIES = {'DK', 'IT', 'NO', 'SE'}
NATIONAL_ZONES = {'AL', 'AT', 'BE', 'BG', 'CH', 'CZ', 'EE', 'ES', 'FI', 'FR', 'GR',
                  'HR', 'HU', 'LT', 'LV', 'MK', 'NL', 'PL', 'PT', 'RO', 'RS', 'SI', 'SK'}


def candidate(country, available):
    if country in SPLIT_COUNTRIES:
        return None, 'requires constituent-bus bidding-zone geography; centroid insufficient'
    zone = 'DE-LU' if country in {'DE', 'LU'} else country if country in NATIONAL_ZONES else None
    if zone is None or zone not in available:
        return None, 'no matching published observed-price zone'
    return zone, 'provisional country mapping; geography and load aggregation still require audit'


def audit(network, prices):
    import xarray as xr
    manifest = json.loads((prices / 'manifest.json').read_text())
    available = {name for name in manifest if (prices / f'{name}.json').exists()}
    with xr.open_dataset(network) as data:
        rows = [dict(node=str(node), country=str(country), longitude=float(x), latitude=float(y),
                     candidate_zone=candidate(str(country), available)[0], reason=candidate(str(country), available)[1])
                for node, country, x, y in zip(data['buses_i'].values, data['buses_country'].values,
                                              data['buses_x'].values, data['buses_y'].values)]
    return dict(status='provisional_mapping_inventory_only', input_sha256=digest(network),
                price_manifest_sha256=digest(prices / 'manifest.json'),
                observed_price_sha256={zone: digest(prices / f'{zone}.json') for zone in sorted(available)},
                nodes=rows, unresolved_nodes=sum(row['candidate_zone'] is None for row in rows),
                scope='No dispatch prices compared; no empirically validated nodes. Split-country clusters remain unresolved.',
                remaining_gates=['Audit constituent-bus geography and cluster mixing',
                                 'Declare nodal-price aggregation and sensitivity',
                                 'Predeclare training/held-out periods, coverage and numerical thresholds',
                                 'Verify annual dispatch before assessing agreement'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--prices', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.input, args.prices)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save(args.output, result)
    print(f"Provisional inventory: {len(result['nodes'])} nodes, {result['unresolved_nodes']} unresolved; not validated")
