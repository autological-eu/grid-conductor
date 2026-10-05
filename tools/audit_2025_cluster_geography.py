"""Audit original-bus membership and geographic extent; never infer bidding zones."""
import argparse
import csv
import math
from pathlib import Path
from monthly_dispatch import digest, save


def summarize(original, clustered, membership):
    groups = {node: [] for node in clustered}
    seen = set()
    for bus, node in membership:
        if bus in seen or bus not in original or node not in groups:
            raise ValueError('Duplicate, missing original bus or unknown cluster')
        seen.add(bus)
        country, longitude, latitude = original[bus]
        if not all(math.isfinite(v) for v in [longitude, latitude]):
            raise ValueError('Nonfinite original-bus geography')
        groups[node].append((bus, country, longitude, latitude))
    if seen != set(original) or any(not members for members in groups.values()):
        raise ValueError('Incomplete original-bus or clustered-node membership')
    rows = []
    for node, members in sorted(groups.items()):
        countries = sorted({m[1] for m in members})
        rows.append(dict(node=node, constituent_buses=len(members), countries=countries,
                         longitude_min=min(m[2] for m in members), longitude_max=max(m[2] for m in members),
                         latitude_min=min(m[3] for m in members), latitude_max=max(m[3] for m in members),
                         country_consistent=countries == [clustered[node]],
                         bidding_zone=None,
                         scope='Membership only; authoritative zone boundaries and cross-zone cluster audit still required.'))
    return rows


def compose_membership(simplified, final):
    if len(dict(simplified)) != len(simplified) or len(dict(final)) != len(final):
        raise ValueError('Duplicate bus-map keys')
    final = dict(final)
    if any(bus not in final for _, bus in simplified):
        raise ValueError('Simplification target missing from final clustering')
    return [(bus, final[target]) for bus, target in simplified]


def audit(original_path, clustered_path, busmap, simplification):
    import xarray as xr
    with xr.open_dataset(original_path) as data:
        original = {str(bus): (str(country), float(x), float(y)) for bus, country, x, y in
                    zip(data.buses_i.values, data.buses_country.values, data.buses_x.values, data.buses_y.values)}
    with xr.open_dataset(clustered_path) as data:
        clustered = dict(zip(map(str, data.buses_i.values), map(str, data.buses_country.values)))
    with busmap.open(newline='') as stream:
        membership = [(row['name'], row['busmap']) for row in csv.DictReader(stream)]
    with simplification.open(newline='') as stream:
        reader = csv.reader(stream)
        next(reader)
        simplified = [(row[0], row[1]) for row in reader]
    membership = compose_membership(simplified, membership)
    rows = summarize(original, clustered, membership)
    return dict(status='constituent_geography_inventory_only',
                source_sha256={p.name: digest(p) for p in [original_path, clustered_path, busmap, simplification]},
                original_buses=len(original), clustered_nodes=len(rows),
                country_mismatch_nodes=sum(not row['country_consistent'] for row in rows), nodes=rows,
                scope='No accepted bidding-zone mapping or empirical price validation.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--clustered', type=Path, required=True)
    parser.add_argument('--busmap', type=Path, required=True)
    parser.add_argument('--simplification', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.original, args.clustered, args.busmap, args.simplification)
    save(args.output, report)
    print(f"Audited {report['original_buses']} original buses / {report['clustered_nodes']} clusters; {report['country_mismatch_nodes']} country mismatches; no zone assignment")
