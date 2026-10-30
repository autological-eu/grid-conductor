"""Export source-labelled 2025 zonal supply and connection adequacy inventories.

Read-only diagnostic over retained research inputs. No parameter is changed.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import logging
from collections import defaultdict
from pathlib import Path

import numpy as np
import pypsa

from baselines.compact.evaluation import ANCHOR, CARRIER, physical_lp
from baselines.compact.network import transport_corridors
from baselines.compact.source import ROOT, grouped_fit_inputs, observed_flow_snapshot

OUTPUT = ROOT / 'research/data/adequacy-2025'
OBSERVED = ROOT / 'data/carbon-pilot/map-2025'
MAPPING = ROOT / 'data/bidding-zone-network-2025/annual-v7/mapping.json'
HYDRO_BLOCKS = ROOT / 'data/synthetic-europe-physical-2025-irena-linear/hydro-warm-v1'
WATER = ROOT / 'data/hydro-observations-2025/nve-updated-model-v5/water.npz'
RAW = ROOT / 'data/pypsa-eur/upstream/resources/gridfix-2025/networks/base_s_128_elec.nc'
PSR = {'onshore_wind': 'B19', 'offshore_wind': 'B18', 'solar': 'B16',
       'nuclear': 'B14', 'ror': 'B11', 'reservoir': 'B12', 'gas': 'B04',
       'hard_coal': 'B05', 'lignite': 'B02', 'oil': 'B06', 'biomass': 'B01',
       'waste': 'B17', 'geothermal': 'B09'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observed_zonal_generation(zones):
    """Use raw A75 intervals only; distinguish actual zone from national proxy."""
    result = {(zone, kind): np.full(8760, np.nan) for zone in zones for kind in PSR}
    scope = defaultdict(set)
    checked = 0
    for zone in zones:
        for month in range(1, 13):
            path = OBSERVED / zone / f'{month:02d}.json'
            receipt_path = path.with_suffix('.receipt.json')
            if not path.exists() or not receipt_path.exists():
                continue
            receipt = json.loads(receipt_path.read_text())
            if receipt['zone'] != zone or receipt['month'] != month or digest(path) != receipt['sha256']:
                raise ValueError(f'A75 receipt mismatch: {zone}/{month}')
            if receipt['source']['provider'] != 'ENTSO-E Transparency Platform':
                raise ValueError('Unexpected A75 provider')
            scope[zone].add(receipt['geographic_scope'])
            rows = json.loads(path.read_text())
            if len(rows) < receipt['complete_hours']:
                raise ValueError(f'A75 complete-hour receipt exceeds rows: {zone}/{month}')
            seen = set()
            for row in rows:
                hour = int((np.datetime64(row['start'].removesuffix('Z')) -
                            np.datetime64('2025-01-01T00')).astype('timedelta64[h]').astype(int))
                if not 0 <= hour < 8760 or row['zone'] != zone:
                    raise ValueError('A75 hour/zone outside 2025 domain')
                if hour in seen:
                    raise ValueError('Duplicate A75 hourly row')
                seen.add(hour)
                for kind, code in PSR.items():
                    if code not in row['generation_mwh_by_type']:
                        continue
                    value = float(row['generation_mwh_by_type'][code])
                    if np.isfinite(result[zone, kind][hour]):
                        raise ValueError(f'Duplicate A75 generation cell: {zone}/{kind}/{hour}')
                    result[zone, kind][hour] = value
            checked += 1
    return result, scope, checked


def source_fleet(native, original, zones, schema, data):
    """Return source nameplate, fixed hydro, and its verified country replay."""
    nameplate = defaultdict(float)
    for _, row in native.generators.iterrows():
        if row.carrier == 'emergency':
            continue
        zone = str(native.buses.loc[row.bus, 'bidding_zone'])
        if zone == 'ES-IB-MA':
            zone = 'ES'
        nameplate[zone, CARRIER[row.carrier]] += float(row.p_nom)
    units = original.storage_units.query("carrier == 'hydro'")
    power = np.concatenate([np.load(HYDRO_BLOCKS / f'{i:02d}.npz')['hydro_power']
                            for i in range(59)])
    if power.shape != (8760, len(units)):
        raise ValueError('Original fixed hydro schedule shape changed')
    with np.load(WATER) as archive:
        water = archive['power']
    norway = (units.bus.map(original.buses.country) == 'NO').to_numpy()
    if water.shape != (8760, int(norway.sum())):
        raise ValueError('Norway hydro witness shape changed')
    power[:, norway] = water
    mapping = json.loads(MAPPING.read_text())
    shares = {row['name']: row['shares'] for row in mapping['allocation']
              if row['component'] == 'FixedReservoir'}
    fixed = {zone: np.zeros(8760) for zone in zones}
    for j, (name, row) in enumerate(units.iterrows()):
        if name not in shares:
            raise ValueError(f'Missing reservoir mapping {name}')
        for bus, fraction in shares[name].items():
            zone = bus.rsplit('::', 1)[1]
            if zone == 'ES-IB-MA':
                zone = 'ES'
            nameplate[zone, 'reservoir'] += float(row.p_nom * fraction)
            fixed[zone] += power[:, j] * fraction
    technology = schema['technologies'].index('reservoir')
    replay_error = {}
    for country in schema['countries']:
        country_id = schema['countries'].index(country)
        country_zones = [z for z in zones if any(g['zone'] == z and g['country'] == country
                                                  for g in schema['groups'])]
        if not country_zones:
            continue
        reconstructed = sum((fixed[z] for z in country_zones), start=np.zeros(8760))
        retained = data['fixed_generation'][:, country_id, technology]
        replay_error[country] = float(np.max(abs(reconstructed - retained)))
    return nameplate, fixed, replay_error


def write_csv(path, rows):
    with path.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def run():
    schema, data, _ = grouped_fit_inputs()
    model = physical_lp()
    zones = model['zones']
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    native = pypsa.Network(ANCHOR / 'native.nc')
    original = pypsa.Network(RAW)
    nameplate, fixed, hydro_replay_error = source_fleet(native, original, zones, schema, data)
    observed, scopes, receipts = observed_zonal_generation(zones)
    keys = {(group['zone'], group['technology']): i
            for i, group in enumerate(schema['groups'])}
    zone_country = {group['zone']: group['country'] for group in schema['groups']}
    supply = []
    for zone in zones:
        for kind, code in PSR.items():
            group = keys.get((zone, kind))
            available = data['capacity'][:, group] if group is not None else np.zeros(8760)
            if kind == 'reservoir':
                available = np.full(8760, nameplate[zone, kind])
            report = observed[zone, kind]
            known = np.isfinite(report)
            geographic_scope = '|'.join(sorted(scopes[zone])) or 'unavailable'
            comparable = geographic_scope == 'bidding zone'
            exceed = known & (report > available + 1)
            cap_exceed = known & (report > nameplate[zone, kind] + 1)
            supply.append(dict(
                zone=zone, country=zone_country.get(zone, ''), technology=kind,
                model_source='retained 2025 PyPSA-Eur-based fleet and zonal allocation',
                model_source_file='data/bidding-zone-network-2025/annual-solar-alignment-v1/native.nc',
                availability_source=('fixed PyPSA/NVE hydro schedule; turbine p_nom is power ceiling'
                                     if kind == 'reservoir' else
                                     'retained 2025 PyPSA weather/fleet inputs with solar and capacity corrections'),
                availability_source_file=('data/synthetic-europe-physical-2025-irena-linear/hydro-warm-v1/NN.npz; '
                                          'data/hydro-observations-2025/nve-updated-model-v5/water.npz'
                                          if kind == 'reservoir' else
                                          'data/bidding-zone-network-2025/sigmoid-month-pairs-v1/inputs.npz'),
                observed_source='ENTSO-E A75 '+code+'; raw hourly production',
                observed_source_file=f'data/carbon-pilot/map-2025/{zone}/MM.json',
                observed_geographic_scope=geographic_scope,
                observed_comparable_to_zone='yes' if comparable else 'no',
                observation_hours=int(known.sum()),
                source_fleet_nameplate_mw=round(nameplate[zone, kind], 6),
                model_peak_hourly_available_mw=round(float(available.max()), 6),
                model_annual_available_twh=round(float(available.sum() / 1e6), 6),
                fixed_reservoir_generation_twh=(round(float(fixed[zone].sum() / 1e6), 6)
                                                 if kind == 'reservoir' and
                                                 hydro_replay_error.get(zone_country.get(zone, ''), 0) <= 1e-6 else ''),
                fixed_reservoir_replay_status=('matches_retained_country_total' if
                    kind == 'reservoir' and hydro_replay_error.get(zone_country.get(zone, ''), 0) <= 1e-6 else
                    'source_schedule_differs_from_retained' if kind == 'reservoir' else ''),
                observed_peak_mw=round(float(report[known].max()), 6) if known.any() else '',
                observed_generation_twh=round(float(report[known].sum() / 1e6), 6) if known.any() else '',
                observed_over_source_nameplate_hours=int(cap_exceed.sum()) if comparable else '',
                observed_over_hourly_available_hours=int(exceed.sum()) if comparable else '',
                maximum_hourly_availability_gap_mw=(round(float((report[exceed] - available[exceed]).max()), 6)
                                                     if comparable and exceed.any() else ''),
                adequacy_status=('uncovered' if not known.any() else
                                 'scope_not_matched' if not comparable else
                                 'observed_above_source_nameplate' if cap_exceed.any() else
                                 'observed_above_model_availability' if exceed.any() else
                                 'no_observed_exceedance'),
            ))
    edges, lower, upper = transport_corridors(zones, data)
    observed_flow, within_bounds, missing_zone = observed_flow_snapshot(edges, zones)
    if len(edges) != 95 or observed_flow.shape != lower.shape:
        raise ValueError('Retained corridor/A09 dimensions changed')
    physical = defaultdict(lambda: {'line': 0, 'transformer': 0, 'link': 0})
    bus_zone = native.buses.bidding_zone.replace({'ES-IB-MA': 'ES'}).to_dict()
    for kind in ['line', 'transformer', 'link']:
        frame = getattr(native, {'line': 'lines', 'transformer': 'transformers',
                                 'link': 'links'}[kind])
        for _, row in frame.iterrows():
            a, b = bus_zone[row.bus0], bus_zone[row.bus1]
            if a != b:
                physical[tuple(sorted((a, b)))][kind] += 1
    connection = []
    for index, (left, right) in enumerate(edges):
        a, b = zones[left], zones[right]
        coverage = np.isfinite(observed_flow[:, index])
        counts = physical[tuple(sorted((a, b)))]
        connection.append(dict(
            from_zone=a, to_zone=b,
            model_topology_source='PyPSA-Eur physical grid; refined bidding-zone mapping',
            model_topology_file='data/bidding-zone-network-2025/annual-solar-alignment-v1/native.nc',
            model_constraint_source='PyPSA-Eur N-0 ratings and controllable-link bounds; LP also uses PTDF',
            model_constraint_file='data/bidding-zone-network-2025/annual-solar-alignment-v1/network.npz',
            observed_exchange_source='ENTSO-E A09 day-ahead commercial exchange',
            observed_exchange_file='data/eu-market/flow-adjusted-clearing-2025/aligned-mixed-flow-observed-root-v1-u20-r1/month-MM/inferred-flows.npz',
            jao_role='not in retained LP; only sampled Core/Nordic presolved 2025 probes',
            jao_probe_file='data/jao/probe-2025-v1/*presolved.json.gz',
            ac_line_count=counts['line'], transformer_count=counts['transformer'],
            controllable_link_count=counts['link'],
            independent_envelope_mean_export_gw=round(float(upper[:, index].mean()), 6),
            independent_envelope_mean_import_gw=round(float(-lower[:, index].mean()), 6),
            independent_envelope_min_export_gw=round(float(upper[:, index].min()), 6),
            independent_envelope_min_import_gw=round(float(-lower[:, index].min()), 6),
            observed_a09_hours=int(coverage.sum()),
            observed_peak_abs_exchange_gw=(round(float(abs(observed_flow[coverage, index]).max()), 6)
                                           if coverage.any() else ''),
            observed_outside_independent_envelope_hours=int((coverage & ~within_bounds[:, index]).sum()),
            observed_incident_zone_missing_hours=int(missing_zone[:, left].sum()),
        ))
    missing_components = [(row['from_zone'], row['to_zone']) for row in connection
                          if row['ac_line_count'] + row['transformer_count'] +
                          row['controllable_link_count'] == 0]
    if missing_components:
        raise ValueError(f'Corridor without a source component: {missing_components}')
    jao_paths = sorted((ROOT / 'data/jao/probe-2025-v1').glob('*presolved.json.gz'))
    jao_probes = []
    for path in jao_paths:
        with gzip.open(path, 'rt') as file:
            probe = json.load(file)
        if probe['market_domain_complete'] or not probe['presolved_only']:
            raise ValueError('JAO probe status differs from sampled presolved evidence')
        jao_probes.append(dict(region=probe['region'], start=probe['start'],
                               constraints=len(probe['constraints'])))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT / 'zone-technology.csv', supply)
    write_csv(OUTPUT / 'zone-connections.csv', connection)
    summary = dict(status='read_only_adequacy_inventory_not_a_model_change',
        model='mixed_curve_fitting_2025_source_inputs', hours=8760,
        zones=len(zones), zone_technology_rows=len(supply), modeled_technology_groups=len(keys),
        cross_zone_connections=len(connection), a75_receipts_verified=receipts,
        exact_zone_observed_rows=sum(r['observed_comparable_to_zone'] == 'yes' and
                                     r['observation_hours'] > 0 for r in supply),
        exact_zone_source_nameplate_shortfall_rows=sum(r['adequacy_status'] == 'observed_above_source_nameplate' for r in supply),
        exact_zone_availability_shortfall_rows=sum(r['adequacy_status'] == 'observed_above_model_availability' for r in supply),
        a09_observed_corridors=sum(r['observed_a09_hours'] > 0 for r in connection),
        jao_sampled_presolved_hours=jao_probes,
        fixed_hydro_country_replay_mismatch_mw={k: round(v, 6) for k, v in hydro_replay_error.items()
                                                if v > 1e-6},
        limitations=['Observed A75 production is a demonstrated hourly lower bound only for matching zone and category',
                     'National or proxy-scope A75 series are listed but not compared to a single zone',
                     'Source PyPSA p_nom is shown separately from corrected LP availability; the latter may exceed the former',
                     'Hourly availability is not energy-constrained hydro water or commercial market capacity',
                     'Independent corridor envelopes are N-0 sums, not the full PTDF or JAO flow-based domain',
                     'No capacity, availability, network topology or accepted baseline parameter is changed'],
        source_sha256={str(p.relative_to(ROOT)): digest(p) for p in
                       [ANCHOR / 'native.nc', RAW, MAPPING,
                        ANCHOR / 'network.npz', WATER,
                        ROOT / 'data/bidding-zone-network-2025/sigmoid-month-pairs-v1/inputs.npz'] +
                       [HYDRO_BLOCKS / f'{i:02d}.npz' for i in range(59)] + jao_paths},
        output_sha256={p.name: digest(p) for p in
                       [OUTPUT / 'zone-technology.csv', OUTPUT / 'zone-connections.csv']})
    (OUTPUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
