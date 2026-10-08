"""Inventory mapping work required; country labels are not accepted zone assignments."""
import argparse
import json
from pathlib import Path
import xarray as xr
from eu_zones import ZONES, EXTERIORS
from hourly_renewable_estimates import digest


def candidates(country):
    labels = [row[0] for row in ZONES + EXTERIORS]
    # Shared DE-LU and split zones are candidates only, never automatic assignments.
    return [label for label in labels if label == country
            or label.startswith(country + '-')
            or (country in ['DE', 'LU'] and label == 'DE-LU')
            or (country in ['DK', 'SE', 'NO'] and label.startswith(country)
                and label[len(country):].isdigit())]


def run(network, expected, output):
    if output.exists():
        raise ValueError('Use a fresh diagnostic path')
    if digest(network) != expected:
        raise ValueError('Source network hash mismatch')
    with xr.open_dataset(network) as d:
        buses = list(d.buses_i.values)
        countries = list(d.buses_country.values)
        if len(set(buses)) != len(buses) or any(not isinstance(c, str) or not c for c in countries):
            raise ValueError('Unique buses and explicit countries required')
        lookup = dict(zip(buses, countries))
        assets = {}
        for kind in ['generators', 'loads', 'storage_units']:
            ids = list(d[kind + '_i'].values)
            locations = list(d[kind + '_bus'].values)
            if len(ids) != len(set(ids)) or len(ids) != len(locations) or any(b not in lookup for b in locations):
                raise ValueError('Complete unique asset/bus identities required')
            assets[kind] = [lookup[b] for b in locations]
        rows = []
        for country in sorted(set(countries)):
            labels = candidates(country)
            rows.append(dict(country=country, buses=countries.count(country),
                             asset_counts={kind: values.count(country) for kind, values in assets.items()},
                             registry_candidates=labels,
                             mapping_status=('missing_registry_scope' if not labels else
                                             'split_zone_geography_required' if len(labels) > 1 else
                                             'shared_zone_accounting_required' if labels == ['DE-LU'] else
                                             'single_candidate_scope_audit_required'),
                             accepted_assignment=None))
    report = dict(status='mapping_scope_diagnostic_no_accepted_assignments', year=2025,
                  network_sha256=expected, registry_sha256=digest(Path(__file__).with_name('eu_zones.py')),
                  producer_sha256=digest(__file__), countries=rows,
                  totals=dict(buses=len(buses), **{k: len(v) for k, v in assets.items()}),
                  limitations=['Registry is existing project discovery scope, not an authoritative 2025 geometry or coverage certificate.',
                               'Country/name candidates are not accepted asset-to-zone mapping; all assignments remain null.',
                               'Clustered bus centroids cannot establish asset geography or split-zone demand allocation.',
                               'Commercial transfer constraints and empirical/numerical acceptance gates remain separate.',
                               'No asset removal, dispatch solve, generation-availability substitution or zone pooling performed.'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print('Mapping scope:', len(rows), 'countries;', sum(len(r['registry_candidates']) > 1 for r in rows),
          'split countries;', sum(not r['registry_candidates'] for r in rows), 'without registry candidates.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--network', type=Path, required=True)
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    run(a.network, a.expected_sha256, a.output)
