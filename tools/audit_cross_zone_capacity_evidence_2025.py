"""Compare 2025 A11 physical and A09 commercial border flows to model edges.

This emits directional *observed flow* lower bounds, not certified NTC or
physical equipment ratings. JAO flow-based PTDF rows remain separate evidence.
Run with PYTHONPATH=tools in the pinned scientific environment.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone

import numpy as np

from baselines.compact.network import transport_corridors
from baselines.compact.source import ROOT, digest, grouped_fit_inputs
from eu_zones import EXTERIORS, ZONES
from flow_tracing import parse_quantity

RAW = ROOT / 'data/eu-market/flow-refresh-2025/raw'
OUT = ROOT / 'research/data/cross-zone-capacity-evidence-2025.csv'
SUMMARY = ROOT / 'research/data/cross-zone-capacity-evidence-2025.json'
WITNESS = ROOT / 'data/bidding-zone-network-2025/a11-corridor-floor-v1/hourly.npz'
PERIOD = dict(periodStart='202501010000', periodEnd='202601010000')
CODES = {row[0]: row[1] for row in ZONES + EXTERIORS}
START = datetime(2025, 1, 1, tzinfo=timezone.utc)


def series(source, sink, kind):
    if source not in CODES or sink not in CODES:
        return None, None
    code_a, code_b = CODES[source], CODES[sink]
    request = dict(PERIOD, documentType=kind, out_Domain=code_a, in_Domain=code_b)
    if kind == 'A09':
        request['contract_MarketAgreement.Type'] = 'A01'
    key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()[:24]
    path = RAW / f'{key}.xml'
    receipt = path.with_suffix('.json')
    if not path.exists() or not receipt.exists():
        return None, None
    meta = json.loads(receipt.read_text())
    if meta['request'] != request or digest(path) != meta['sha256']:
        raise ValueError(f'Changed ENTSO-E {kind} source {source}>{sink}')
    try:
        samples = parse_quantity(path.read_bytes(), {'out_Domain.mRID': code_a,
                                                      'in_Domain.mRID': code_b})
    except ValueError as error:
        if str(error) == 'No quantity data returned':
            return None, digest(path)
        raise
    quarters = np.full(8760 * 4, np.nan)
    for stamp, mw in samples.items():
        offset = (stamp - START).total_seconds() / 900
        if offset != int(offset) or not 0 <= offset < len(quarters) or not np.isfinite(mw):
            raise ValueError(f'Invalid {kind} timestamp or MW {source}>{sink}')
        quarters[int(offset)] = mw / 1000
    hourly = quarters.reshape(8760, 4)
    mean = np.where(np.isfinite(hourly).all(axis=1), hourly.mean(axis=1), np.nan)
    return mean, digest(path)


def audit():
    schema, data, _ = grouped_fit_inputs()
    zones = schema['zones']
    edges, lower, upper = transport_corridors(zones, data)
    rows = []
    files = {}
    a11 = np.full_like(lower, np.nan)
    a09 = np.full_like(lower, np.nan)
    for k, (i, j) in enumerate(edges):
        a, b = zones[i], zones[j]
        values = {}
        for kind in ('A11', 'A09'):
            forward, h1 = series(a, b, kind)
            reverse, h2 = series(b, a, kind)
            if h1:
                files[f'{kind}:{a}>{b}'] = h1
            if h2:
                files[f'{kind}:{b}>{a}'] = h2
            if forward is None or reverse is None:
                values[kind] = None
            else:
                valid = np.isfinite(forward) & np.isfinite(reverse)
                net = np.where(valid, forward - reverse, np.nan)
                values[kind] = net
        physical, scheduled = values['A11'], values['A09']
        if physical is not None:
            a11[:, k] = physical
        if scheduled is not None:
            a09[:, k] = scheduled
        covered = np.isfinite(physical) if physical is not None else np.zeros(8760, bool)
        commercial = np.isfinite(scheduled) if scheduled is not None else np.zeros(8760, bool)
        peak_export = float(max(0, np.nanmax(physical))) if covered.any() else None
        peak_import = float(max(0, -np.nanmin(physical))) if covered.any() else None
        model_export = float(upper[:, k].max())
        model_import = float((-lower[:, k]).max())
        observed_over_hourly = int((covered & ((physical > upper[:, k] + 1e-6) |
                                                (physical < lower[:, k] - 1e-6))).sum()) if covered.any() else 0
        rows.append(dict(from_zone=a, to_zone=b,
            a11_physical_hours=int(covered.sum()), a09_commercial_hours=int(commercial.sum()),
            model_max_export_gw=round(model_export, 6), model_max_import_gw=round(model_import, 6),
            a11_peak_export_gw=round(peak_export, 6) if peak_export is not None else '',
            a11_peak_import_gw=round(peak_import, 6) if peak_import is not None else '',
            a09_peak_export_gw=(round(float(max(0, np.nanmax(scheduled))), 6) if commercial.any() else ''),
            a09_peak_import_gw=(round(float(max(0, -np.nanmin(scheduled))), 6) if commercial.any() else ''),
            observed_a11_over_hourly_model_hours=observed_over_hourly,
            demonstrated_export_above_model_peak_gw=(round(max(0, peak_export - model_export), 6)
                                                       if peak_export is not None else ''),
            demonstrated_import_above_model_peak_gw=(round(max(0, peak_import - model_import), 6)
                                                       if peak_import is not None else ''),
            physical_peak_envelope_status=('no_complete_a11' if not covered.any() else
                'model_peak_below_observed_a11' if peak_export > model_export + 1e-6 or
                                                 peak_import > model_import + 1e-6 else
                'model_peak_covers_observed_a11')))
    # Dated demonstrated corridor-flow floors. They alter only the independent
    # transport envelope, not the source physical PTDF/link matrix.
    forward_peak = np.maximum.accumulate(np.where(np.isfinite(a11), np.maximum(a11, 0), 0), axis=0)
    reverse_peak = np.maximum.accumulate(np.where(np.isfinite(a11), np.maximum(-a11, 0), 0), axis=0)
    candidate_upper = np.maximum(upper, forward_peak)
    candidate_lower = np.minimum(lower, -reverse_peak)
    covered_cells = np.isfinite(a11)
    if np.any(covered_cells & ((a11 > candidate_upper + 1e-8) |
                                   (a11 < candidate_lower - 1e-8))):
        raise ValueError('Dated A11 corridor candidate fails an observed physical flow')
    if np.any(candidate_upper < upper) or np.any(candidate_lower > lower):
        raise ValueError('Dated corridor candidate narrowed an original bound')
    WITNESS.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(WITNESS, edges=edges, observed_a11_gw=a11,
                        observed_a09_gw=a09, original_lower_gw=lower,
                        original_upper_gw=upper, candidate_lower_gw=candidate_lower,
                        candidate_upper_gw=candidate_upper)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(status='physical_A11_and_commercial_A09_edge_evidence_not_applied_to_LP',
                   modeled_edges=len(rows), edges_with_complete_a11=sum(r['a11_physical_hours'] > 0 for r in rows),
                   edges_with_complete_a09=sum(r['a09_commercial_hours'] > 0 for r in rows),
                   edges_a11_above_model_peak=sum(r['physical_peak_envelope_status'] ==
                                                 'model_peak_below_observed_a11' for r in rows),
                   candidate_upper_uplift_cells=int((candidate_upper > upper + 1e-8).sum()),
                   candidate_lower_uplift_cells=int((candidate_lower < lower - 1e-8).sum()),
                   source_sha256=files, csv_sha256=digest(OUT),
                   hourly_witness_sha256=digest(WITNESS),
                   limitations=['A11 is reported physical exchange at a border, not a certified independent corridor rating',
                                'A09 is commercial exchange and must not be used as a physical line floor',
                                'Only complete four-quarter hourly means and both directions are compared',
                                'JAO market domain, full physical PTDF and outages are not reconstructed here',
                                'No accepted physical LP constraint changed'])
    SUMMARY.write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
