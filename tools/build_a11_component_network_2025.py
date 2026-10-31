"""Build a dated 2025 physical LP candidate for every A11 corridor gap.

AC line ratings are increased only within the source nameplate. HVDC gaps use
explicit *effective* link bounds: A11 proves aggregate border flow, not that
the inherited single cable has a larger nameplate. No topology or PTDF changes.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict

import numpy as np
import xarray as xr

from baselines.compact.evaluation import ANCHOR, physical_lp
from baselines.compact.network import a11_supported_transport_corridors
from baselines.compact.source import ROOT, digest, grouped_fit_inputs

CATALOGUE = ROOT / 'data/bidding-zone-network-2025/joint-network-calibration-v4/branches.json'
CATALOGUE_AUDIT = CATALOGUE.with_name('summary.json')
SOURCE = ROOT / 'data/bidding-zone-network-2025/a11-corridor-floor-v1/hourly.npz'
OUT = ROOT / 'data/bidding-zone-network-2025/a11-component-network-v1'
REVIEW = ROOT / 'research/data/a11-component-network-2025.csv'
SUMMARY = ROOT / 'research/data/a11-component-network-2025.json'


def build():
    schema, data, _ = grouped_fit_inputs()
    model = physical_lp()
    edges, transport_lower, transport_upper = a11_supported_transport_corridors(schema['zones'], data)
    with np.load(SOURCE) as archive:
        original_transport_lower = archive['original_lower_gw']
        original_transport_upper = archive['original_upper_gw']
        observed_a11 = archive['observed_a11_gw']
    catalogue_audit = json.loads(CATALOGUE_AUDIT.read_text())
    if digest(CATALOGUE) != catalogue_audit['catalogue_sha256']:
        raise ValueError('Original physical branch catalogue changed')
    branches = json.loads(CATALOGUE.read_text())
    if len(branches) != len(model['ratings']):
        raise ValueError('Branch catalogue no longer matches LP')
    expected = np.asarray([r['original_limit_mw'] * (1.15 if r['nordic'] else 1.)
                           for r in branches])
    np.testing.assert_allclose(model['ratings'], expected, rtol=0, atol=1e-6)
    ratings = np.broadcast_to(model['ratings'], (8760, len(branches))).copy()
    link_lower = model['link_min'].copy()
    link_upper = model['link_max'].copy()
    zones = schema['zones']
    with xr.open_dataset(ANCHOR / 'native.nc') as grid:
        bus_zone = dict(zip(grid['buses_i'].values.astype(str),
                            grid['buses_bidding_zone'].values.astype(str)))
        bus_zone = {b: 'ES' if z == 'ES-IB-MA' else z for b, z in bus_zone.items()}
        line_index = {name: i for i, name in enumerate(grid['lines_i'].values.astype(str))}
        line_bus0 = grid['lines_bus0'].values.astype(str)
        line_bus1 = grid['lines_bus1'].values.astype(str)
        line_nom = grid['lines_s_nom'].values.astype(float)
        link_names = grid['links_i'].values.astype(str)
        link_bus0 = grid['links_bus0'].values.astype(str)
        link_bus1 = grid['links_bus1'].values.astype(str)
        link_nom = grid['links_p_nom'].values.astype(float)
    line_pairs = defaultdict(list)
    for k, row in enumerate(branches):
        if row['component'] != 'Line' or row['name'] not in line_index:
            raise ValueError('Unmapped physical PTDF branch')
        j = line_index[row['name']]
        pair = frozenset((bus_zone[line_bus0[j]], bus_zone[line_bus1[j]]))
        if len(pair) == 2:
            line_pairs[pair].append((k, j))
        if abs(line_nom[j] - row['nameplate_mva']) > 1e-6:
            raise ValueError('Changed physical branch nameplate')
    link_pairs = defaultdict(list)
    for j in range(len(link_names)):
        pair = frozenset((bus_zone[link_bus0[j]], bus_zone[link_bus1[j]]))
        if len(pair) == 2:
            link_pairs[pair].append(j)
        if abs(model['link_max'][0, j] - link_nom[j]) > 1e-6:
            raise ValueError('Changed link source nameplate/order')
    jao = {(r['from_zone'], r['to_zone'], r['region']): r for r in
           csv.DictReader((ROOT / 'research/data/jao-edge-cnec-evidence-2025.csv').open())}
    review = []
    changed_ac = changed_link = 0
    for k, (a_id, b_id) in enumerate(edges):
        a, b = zones[a_id], zones[b_id]
        pair = frozenset((a, b))
        lines, links = line_pairs[pair], link_pairs[pair]
        if not lines and not links:
            raise ValueError(f'Edge without mapped native component: {a}/{b}')
        required_forward = transport_upper[:, k] * 1000
        required_reverse = -transport_lower[:, k] * 1000
        old_forward = original_transport_upper[:, k] * 1000
        old_reverse = -original_transport_lower[:, k] * 1000
        gap = max(float(np.max(required_forward - old_forward)),
                  float(np.max(required_reverse - old_reverse)))
        physical = observed_a11[:, k]
        covered = int(np.isfinite(physical).sum())
        status = 'no_complete_a11' if not covered else 'no_demonstrated_gap'
        component_names = []
        if gap > 1e-5:
            if lines and links:
                raise ValueError(f'Mixed AC/HVDC gap needs separate source mapping: {a}/{b}')
            if lines:
                ids = np.asarray([item[0] for item in lines])
                current = float(model['ratings'][ids].sum())
                required = np.maximum(required_forward, required_reverse)
                factor = np.maximum(1, required / current)
                ratings[:, ids] = model['ratings'][ids][None, :] * factor[:, None]
                for row_id, line_id in lines:
                    if (ratings[:, row_id] > line_nom[line_id] + 1e-5).any():
                        raise ValueError(f'A11 gap exceeds mapped AC nameplate: {a}/{b}')
                    component_names.append(f'Line:{branches[row_id]["name"]}')
                status = 'dated_ac_rating_within_nameplate'
                changed_ac += 1
            else:
                # Preserve each source link's directional share and orientation.
                forward_base = np.zeros(8760)
                reverse_base = np.zeros(8760)
                for j in links:
                    same = bus_zone[link_bus0[j]] == a
                    forward_base += model['link_max'][:, j] if same else -model['link_min'][:, j]
                    reverse_base += -model['link_min'][:, j] if same else model['link_max'][:, j]
                if np.any(forward_base <= 0) or np.any(reverse_base <= 0):
                    raise ValueError(f'Unsupported directional link bounds: {a}/{b}')
                forward_factor = np.maximum(1, required_forward / forward_base)
                reverse_factor = np.maximum(1, required_reverse / reverse_base)
                for j in links:
                    same = bus_zone[link_bus0[j]] == a
                    link_upper[:, j] = model['link_max'][:, j] * (forward_factor if same else reverse_factor)
                    link_lower[:, j] = model['link_min'][:, j] * (reverse_factor if same else forward_factor)
                    component_names.append(f'Link:{link_names[j]}')
                status = 'dated_effective_hvdc_bound_above_inherited_nameplate'
                changed_link += 1
        review.append(dict(from_zone=a, to_zone=b, a11_covered_hours=covered,
            original_export_peak_gw=round(float(old_forward.max()/1000), 6),
            original_import_peak_gw=round(float(old_reverse.max()/1000), 6),
            a11_peak_export_gw=round(float(max(0, np.nanmax(physical))), 6) if covered else '',
            a11_peak_import_gw=round(float(max(0, -np.nanmin(physical))), 6) if covered else '',
            mapped_ac_lines=len(lines), mapped_hvdc_links=len(links),
            component_names='|'.join(component_names),
            jao_core_endpoint_cnec_rows=jao[(a, b, 'core')]['matching_cnec_rows'],
            jao_nordic_endpoint_cnec_rows=jao[(a, b, 'nordic')]['matching_cnec_rows'],
            candidate_status=status))
    if np.any(ratings < model['ratings'][None, :] - 1e-6):
        raise ValueError('Candidate lowered an AC rating')
    if np.any(link_lower > model['link_min'] + 1e-6) or np.any(link_upper < model['link_max'] - 1e-6):
        raise ValueError('Candidate narrowed an HVDC link')
    if changed_ac + changed_link != 19:
        raise ValueError('Unreconciled A11/model edge gap')
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / 'inputs.npz', ratings_mw=ratings,
                        link_min_mw=link_lower, link_max_mw=link_upper)
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(review[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(review)
    summary = dict(status='complete_19_gap_component_level_candidate_not_baseline',
        hours=8760, reviewed_edges=len(review), ac_edges_revised=changed_ac,
        hvdc_edges_revised=changed_link,
        source_sha256=dict(native=digest(ANCHOR / 'native.nc'),
                           original_branch_catalogue=digest(CATALOGUE),
                           a11_edge_witness=digest(SOURCE),
                           jao_endpoint_crosswalk=digest(ROOT / 'research/data/jao-edge-cnec-evidence-2025.csv')),
        input_sha256=digest(OUT / 'inputs.npz'), review_csv_sha256=digest(REVIEW),
        limitations=['A11 demonstrates realized border flow, not firm transfer capacity',
                     'HVDC effective uplift may aggregate missing parallel equipment into an inherited link',
                     'AC PTDF coefficients, topology, impedance and hydro schedule are unchanged',
                     'JAO CNECs corroborate endpoints only; flow-based market domain remains unmapped',
                     'No acceptance or scenario-response gate passed'])
    SUMMARY.write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
