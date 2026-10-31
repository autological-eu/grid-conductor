"""Render source-checked, side-by-side 2025 fleet and corridor inventories."""
from __future__ import annotations

import csv
import json
from collections import defaultdict

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['svg.hashsalt'] = 'grid-conductor-network-before-after-2025'

from baselines.compact.source import ROOT, digest

DATA = ROOT / 'research/data'
REPORT = ROOT / 'research/network-before-after-2025.md'


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def shown(value, digits=2):
    return '—' if value is None else f'{value:,.{digits}f}'


def run():
    original_file = DATA / 'adequacy-2025/zone-technology.csv'
    power_file = DATA / 'zone-tech-power-envelope-2025.csv'
    edges_file = DATA / 'a11-component-network-2025.csv'
    adequacy_receipt = json.loads((DATA / 'adequacy-2025/summary.json').read_text())
    power_receipt = json.loads((DATA / 'zone-tech-power-envelope-2025.json').read_text())
    edge_receipt = json.loads((DATA / 'a11-component-network-2025.json').read_text())
    # The original inventory and each candidate must remain distinguishable.
    if adequacy_receipt['zone_technology_rows'] != 624 or power_receipt['rows'] != 624 or edge_receipt['reviewed_edges'] != 95:
        raise ValueError('Unexpected source inventory size')
    if (digest(original_file) != adequacy_receipt['output_sha256']['zone-technology.csv'] or
        digest(original_file) != power_receipt['source_sha256']['fleet_inventory'] or
        digest(power_file) != power_receipt['csv_sha256']):
        raise ValueError('Changed source fleet or power-envelope inventory')
    if digest(edges_file) != edge_receipt['review_csv_sha256']:
        raise ValueError('Changed A11 edge review')
    original = read_csv(original_file)
    power = {(r['zone'], r['technology']): r for r in read_csv(power_file)}
    if len(power) != 624 or len(original) != 624:
        raise ValueError('Duplicate or missing zone-technology row')
    fleet = []
    for row in original:
        key = (row['zone'], row['technology'])
        candidate = power.pop(key)
        if abs(float(row['source_fleet_nameplate_mw']) - float(candidate['original_fleet_nameplate_mw'])) > .001:
            raise ValueError(f'Fleet source mismatch: {key}')
        matched = row['observed_comparable_to_zone'] == 'yes' and bool(row['observed_peak_mw'])
        if matched != (candidate['observed_scope'] == 'bidding zone' and bool(candidate['observed_peak_mw'])):
            raise ValueError(f'Observation scope mismatch: {key}')
        fleet.append(dict(zone=row['zone'], technology=row['technology'],
            original_fleet_nameplate_mw=row['source_fleet_nameplate_mw'],
            peak_hourly_model_available_mw=row['model_peak_hourly_available_mw'],
            candidate_demonstrated_power_ceiling_mw=candidate['demonstrated_power_ceiling_peak_mw'],
            observed_peak_generation_mw=row['observed_peak_mw'] if matched else '',
            unallocated_observed_peak_mw=row['observed_peak_mw'] if not matched else '',
            observed_hours=row['observation_hours'],
            observed_scope=row['observed_geographic_scope'],
            candidate_treatment=candidate['treatment']))
    if power:
        raise ValueError('Unjoined power candidate rows')
    fleet.sort(key=lambda r: (r['zone'], r['technology']))
    fleet_out = DATA / 'network-before-after-generation-2025.csv'
    write_csv(fleet_out, fleet)
    by_zone = defaultdict(list)
    for row in fleet:
        by_zone[row['zone']].append(row)
    zones = []
    for zone, rows in sorted(by_zone.items()):
        covered = [r for r in rows if r['observed_peak_generation_mw']]
        proxy = [r for r in rows if r['unallocated_observed_peak_mw']]
        zones.append(dict(zone=zone,
            total_original_fleet_gw=sum(float(r['original_fleet_nameplate_mw']) for r in rows)/1000,
            matched_technologies=len(covered),
            matched_original_fleet_gw=sum(float(r['original_fleet_nameplate_mw']) for r in covered)/1000,
            matched_candidate_ceiling_gw=sum(float(r['candidate_demonstrated_power_ceiling_mw']) for r in covered)/1000,
            sum_observed_technology_peaks_gw=sum(float(r['observed_peak_generation_mw']) for r in covered)/1000 if covered else None,
            unallocated_proxy_peak_sum_gw=sum(float(r['unallocated_observed_peak_mw']) for r in proxy)/1000 if proxy else None))
    edges = read_csv(edges_file)
    corridor_file = ROOT / 'data/bidding-zone-network-2025/a11-corridor-floor-v1/hourly.npz'
    with np.load(corridor_file) as witness:
        if digest(corridor_file) != edge_receipt['source_sha256']['a11_edge_witness']:
            raise ValueError('Changed A11 corridor witness')
        lower = witness['candidate_lower_gw']
        upper = witness['candidate_upper_gw']
        observed = witness['observed_a11_gw']
    if lower.shape != (8760, 95):
        raise ValueError('Changed hourly edge dimensions')
    edge_rows = []
    for j, row in enumerate(edges):
        covered = int(row['a11_covered_hours'])
        if covered != int(np.isfinite(observed[:, j]).sum()):
            raise ValueError(f'Changed A11 coverage at edge {j}')
        before_export = float(row['original_export_peak_gw'])
        before_import = float(row['original_import_peak_gw'])
        after_export = float(upper[:, j].max())
        after_import = float((-lower[:, j]).max())
        if after_export + 1e-6 < before_export or after_import + 1e-6 < before_import:
            raise ValueError('Candidate narrowed source edge envelope')
        if covered and (float(row['a11_peak_export_gw']) > after_export + 1e-5 or
                        float(row['a11_peak_import_gw']) > after_import + 1e-5):
            raise ValueError('A11 peak exceeds revised independent edge envelope')
        edge_rows.append(dict(from_zone=row['from_zone'], to_zone=row['to_zone'],
            original_export_limit_gw=shown(before_export, 6),
            revised_export_limit_gw=shown(after_export, 6),
            observed_peak_export_gw=row['a11_peak_export_gw'],
            original_import_limit_gw=shown(before_import, 6),
            revised_import_limit_gw=shown(after_import, 6),
            observed_peak_import_gw=row['a11_peak_import_gw'],
            a11_covered_hours=covered, ac_lines=row['mapped_ac_lines'],
            hvdc_links=row['mapped_hvdc_links'], status=row['candidate_status']))
    edge_out = DATA / 'network-before-after-connections-2025.csv'
    write_csv(edge_out, edge_rows)
    figures = ROOT / 'research/figures'
    figures.mkdir(exist_ok=True)
    covered_zones = [r for r in zones if r['matched_technologies']]
    positions = np.arange(len(covered_zones))
    fig, ax = plt.subplots(figsize=(11, max(5, len(covered_zones)*.36)))
    ax.barh(positions + .2, [r['matched_original_fleet_gw'] for r in covered_zones], .25,
            label='Original nameplate')
    ax.barh(positions - .05, [r['matched_candidate_ceiling_gw'] for r in covered_zones], .25,
            label='Separate power-ceiling candidate')
    ax.plot([r['sum_observed_technology_peaks_gw'] for r in covered_zones], positions + .075,
            'ko', markersize=4, label='Sum of A75 technology peaks')
    ax.set_yticks(positions, [r['zone'] for r in covered_zones])
    ax.invert_yaxis(); ax.set_xlabel('GW, matched technologies only')
    ax.set_title('2025 zone generation power: source, candidate, observed peaks')
    ax.legend(loc='lower right', fontsize=8); fig.tight_layout()
    generation_figure = figures / 'network-generation-before-after-2025.svg'
    fig.savefig(generation_figure, metadata={'Date': None}); plt.close(fig)
    changed = [r for r in edge_rows if r['status'].startswith('dated_')]
    fig, ax = plt.subplots(figsize=(11, max(5, len(changed)*.37)))
    positions = np.arange(len(changed))
    before = [max(float(r['original_export_limit_gw']), float(r['original_import_limit_gw'])) for r in changed]
    after = [max(float(r['revised_export_limit_gw']), float(r['revised_import_limit_gw'])) for r in changed]
    peak = [max(float(r['observed_peak_export_gw']), float(r['observed_peak_import_gw'])) for r in changed]
    ax.hlines(positions, before, after, color='#7c91ac', linewidth=3, label='Limit revision')
    ax.plot(before, positions, 'o', color='#375e97', markersize=4, label='Original envelope peak')
    ax.plot(after, positions, 's', color='#238b45', markersize=4, label='Candidate envelope peak')
    ax.plot(peak, positions, 'x', color='#ab3129', markersize=5, label='A11 physical-flow peak')
    ax.set_yticks(positions, [r['from_zone']+'–'+r['to_zone'] for r in changed])
    ax.invert_yaxis(); ax.set_xlabel('GW, maximum across directions (for overview only)')
    ax.set_title('2025 modeled connections with demonstrated A11 gaps')
    ax.legend(fontsize=8); fig.tight_layout()
    connections_figure = figures / 'network-connections-before-after-2025.svg'
    fig.savefig(connections_figure, metadata={'Date': None}); plt.close(fig)
    lines = ['# 2025 network inventory: before and after candidate corrections', '',
        '**Scope:** 48 bidding zones, 13 generation categories and 95 modeled cross-zone connections. '
        'The original research baseline is unchanged. The generation power-ceiling candidate and the '
        'A11 physical-network candidate are **separate experiments**; the annual €24.831/MWh LP sensitivity '
        'uses only the latter, with original generation inputs and frozen bids.', '',
        f'Download all [624 zone–technology rows]({fleet_out.relative_to(REPORT.parent)}) and '
        f'[95 directional connection rows]({edge_out.relative_to(REPORT.parent)}). Blank observed values mean '
        'no exactly scoped observation; they do not mean zero generation or flow.', '',
        '## Generation capacity beside observed output', '',
        'The full fleet column sums original PyPSA-derived zone–technology nameplates. The paired columns '
        'use only technologies with **bidding-zone-matched** ENTSO-E A75 generation: original fleet power, '
        'the separate dated observed-power-ceiling candidate, and the sum of each technology’s observed '
        '2025 hourly peak. Those technology peaks can occur in different hours, so their sum is **not** '
        'a simultaneous zonal maximum. National or proxy generation is excluded from the paired comparison '
        'but shown in a separate column where present; it must not be compared directly to one zone’s fleet, '
        'especially when repeated across zones of a country. '
        'The candidate ceiling is a power diagnostic, not available renewable energy or reservoir water.', '',
        '![Matched zone fleet power, candidate ceiling and non-simultaneous A75 peaks](figures/network-generation-before-after-2025.svg)', '',
        '| Zone | Full fleet GW | Matched tech | Matched original GW | Candidate ceiling GW | Matched observed peaks GW | Unallocated national/proxy peaks GW |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in zones:
        lines.append(f"| {r['zone']} | {shown(r['total_original_fleet_gw'])} | {r['matched_technologies']}/13 | {shown(r['matched_original_fleet_gw'])} | {shown(r['matched_candidate_ceiling_gw'])} | {shown(r['sum_observed_technology_peaks_gw'])} | {shown(r['unallocated_proxy_peak_sum_gw'])} |")
    lines += ['', 'The downloadable detail keeps each technology, its original fleet nameplate, its peak '
        'model hourly availability, the proposed demonstrated power ceiling, observed peak output, '
        'coverage, geographic scope and treatment. These distinctions matter especially for hydro, wind '
        'and solar. No generation ceiling candidate has yet passed a combined full-year LP audit.', '',
        '## Modeled connections beside observed physical flow', '',
        'All figures below are **GW**. Export means from the first named zone to the second; import is '
        'the reverse direction. Original and revised limits are the **peak independent N-0 directional '
        'edge envelopes** across 2025, not simultaneously feasible transfers under the joint PTDF model '
        'and not JAO market capacities. The revised envelope corresponds to the separate dated A11 '
        'component candidate. ENTSO-E A11 physical-flow peaks use only complete hourly observations '
        'in both directions; A09 commercial schedules are not substituted. A single complete hour '
        'is sufficient for a diagnostic. Fifteen edges have zero such hours.', '',
        '![Original and candidate envelopes beside A11 peaks for the 19 revised connections](figures/network-connections-before-after-2025.svg)', '',
        '| Connection | Original export | Revised export | A11 peak export | Original import | Revised import | A11 peak import | A11 hours | Status |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    labels = {'no_demonstrated_gap':'unchanged', 'no_complete_a11':'no A11',
        'dated_ac_rating_within_nameplate':'AC revised',
        'dated_effective_hvdc_bound_above_inherited_nameplate':'HVDC effective revised'}
    for r in edge_rows:
        lines.append(f"| {r['from_zone']}–{r['to_zone']} | {r['original_export_limit_gw']} | {r['revised_export_limit_gw']} | {r['observed_peak_export_gw'] or '—'} | {r['original_import_limit_gw']} | {r['revised_import_limit_gw']} | {r['observed_peak_import_gw'] or '—'} | {r['a11_covered_hours']:,} | {labels[r['status']]} |")
    lines += ['', '## Interpretation and provenance', '',
        'Three AC edges have revised mapped PTDF branch ratings within original line nameplate. '
        'Sixteen HVDC edges have effective aggregate bounds that may stand for missing parallel '
        'equipment; a larger limit is not proof that any particular cable was uprated. The remaining '
        '61 observed edges have no demonstrated gap, and 15 have no usable A11 hour. '
        'The [annual network sensitivity](a11-component-network-2025.md) cleared all 8,760 hours '
        'with zero emergency, but did not apply the generation power-ceiling candidate. A lower '
        'in-sample price error alone does not validate either candidate for asset scenarios.', '',
        'Generation inputs and A75 coverage: [adequacy inventory](zone-network-adequacy-2025.md) '
        'and [dated power-envelope study](zone-tech-power-envelope-2025.md). Physical-flow and '
        'network provenance: [A11 source audit](cross-zone-capacity-evidence-2025.md) and '
        '[component LP audit](a11-component-network-2025.md). The tracked source tables and '
        'their SHA-256 receipts are retained in `research/data`; large hourly arrays remain ignored.', '']
    REPORT.write_text('\n'.join(lines))
    result = {'zones': len(zones), 'generator_rows': len(fleet), 'connections': len(edge_rows),
            'matched_generator_rows': sum(bool(r['observed_peak_generation_mw']) for r in fleet),
            'a11_covered_connections': sum(r['a11_covered_hours'] > 0 for r in edge_rows),
            'generation_csv_sha256': digest(fleet_out), 'connections_csv_sha256': digest(edge_out),
            'report_sha256': digest(REPORT),
            'generation_figure_sha256': digest(generation_figure),
            'connections_figure_sha256': digest(connections_figure),
            'source_generation_sha256': digest(original_file),
            'source_power_candidate_sha256': digest(power_file),
            'source_network_candidate_sha256': digest(edges_file),
            'source_hourly_a11_sha256': digest(corridor_file)}
    (DATA / 'network-before-after-2025.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
