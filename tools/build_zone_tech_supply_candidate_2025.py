"""Build a source-scoped A75 lower-bound supply candidate, without changing a baseline.

Observed production demonstrates an hourly power floor only where its bidding
zone and technology match. This retrospective candidate is not a weather or
water availability estimate, and cannot be used for a forward scenario.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter

import numpy as np

from baselines.compact.source import ROOT, digest, grouped_fit_inputs
from tools.build_zone_adequacy_2025 import PSR, observed_zonal_generation

OUT = ROOT / 'data/bidding-zone-network-2025/zone-tech-observed-floor-v1'
REVIEW = ROOT / 'research/data/zone-tech-observed-floor-2025.csv'
SUMMARY = ROOT / 'research/data/zone-tech-observed-floor-2025.json'
DISPATCHABLE = {'nuclear', 'gas', 'hard_coal', 'lignite', 'oil', 'biomass',
                'waste', 'geothermal'}


def build():
    schema, data, _ = grouped_fit_inputs()
    zones = schema['zones']
    observed, scopes, checked = observed_zonal_generation(zones)
    groups = {(row['zone'], row['technology']): i for i, row in enumerate(schema['groups'])}
    keys = [(zone, tech) for zone in zones for tech in PSR]
    original = np.zeros((8760, len(keys)))
    candidate = np.zeros_like(original)
    rows = []
    counts = Counter()
    for j, (zone, tech) in enumerate(keys):
        group = groups.get((zone, tech))
        if group is not None:
            original[:, j] = data['capacity'][:, group]
        candidate[:, j] = original[:, j]
        report = observed[zone, tech]
        scope = '|'.join(sorted(scopes[zone])) or 'unavailable'
        matched = scope == 'bidding zone'
        known = matched & np.isfinite(report)
        gap = known & (report > original[:, j] + 1e-6)
        if matched and tech in DISPATCHABLE:
            candidate[gap, j] = report[gap]
        added = candidate[:, j] - original[:, j]
        if gap.any():
            counts['matched_rows_with_gap'] += 1
            counts['matched_gap_hours'] += int(gap.sum())
        if added.any():
            counts['candidate_uplift_rows'] += 1
            counts['candidate_uplift_mwh'] += float(added.sum())
            if group is None:
                counts['uplift_rows_needing_new_offer'] += 1
        status = ('unmatched_scope' if not matched else
                  'no_observed_generation' if not np.isfinite(report).any() else
                  'weather_or_water_reconciliation' if tech not in DISPATCHABLE and gap.any() else
                  'new_offer_required' if group is None and added.any() else
                  'existing_group_floor' if added.any() else 'no_uplift')
        rows.append(dict(zone=zone, technology=tech,
                         observed_source=f'ENTSO-E A75 {PSR[tech]} hourly generation',
                         observed_scope=scope,
                         model_source='retained 2025 grouped supply inputs',
                         model_group_index='' if group is None else group,
                         matched_observation_hours=int(known.sum()),
                         observed_over_model_hours=int(gap.sum()) if matched else '',
                         model_peak_mw=round(float(original[:, j].max()), 6),
                         observed_peak_mw=(round(float(report[known].max()), 6)
                                           if known.any() else ''),
                         candidate_peak_mw=round(float(candidate[:, j].max()), 6),
                         candidate_hourly_uplift_mwh=round(float(added.sum()), 6),
                         treatment=status))
    if np.any(candidate < original - 1e-8) or not np.isfinite(candidate).all():
        raise ValueError('Candidate reduced or invalidated available supply')
    for j, (_, tech) in enumerate(keys):
        if tech not in DISPATCHABLE and not np.array_equal(candidate[:, j], original[:, j]):
            raise ValueError('Weather or water availability was overwritten')
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / 'hourly.npz', original_mw=original,
                        candidate_mw=candidate, keys=np.asarray(keys, dtype='U32'))
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(status='retrospective_zone_tech_supply_candidate_not_lp_baseline',
                   hours=8760, zone_technology_rows=len(keys), a75_receipts_checked=checked,
                   model_groups=len(groups), **dict(counts),
                   source_paths=['data/bidding-zone-network-2025/sigmoid-month-pairs-v1/inputs.npz',
                                 'data/bidding-zone-network-2025/solar-country-fit-v1/delta.npz',
                                 'data/carbon-pilot/map-2025/{zone}/{month}.json'],
                   source_sha256={
                       'grouped_input': digest(ROOT / 'data/bidding-zone-network-2025/sigmoid-month-pairs-v1/inputs.npz'),
                       'solar_delta': digest(ROOT / 'data/bidding-zone-network-2025/solar-country-fit-v1/delta.npz'),
                       'a75_receipt_set': hashlib.sha256(''.join(
                           f'{zone}/{month:02d}:{digest(path)}\n'
                           for zone in zones for month in range(1, 13)
                           if (path := ROOT / f'data/carbon-pilot/map-2025/{zone}/{month:02d}.receipt.json').exists()
                       ).encode()).hexdigest(),
                   },
                   hourly_candidate_sha256=digest(OUT / 'hourly.npz'),
                   review_csv_sha256=digest(REVIEW),
                   rules=['Only exact bidding-zone A75 scope is comparable',
                          'Only dispatchable non-hydro technology rows receive an hourly floor',
                          'Weather-limited renewables, run-of-river and reservoir keep original availability',
                          'Missing LP offers require an explicit new generator and bid',
                          'Observed dispatch is a retrospective lower bound, not a scenario forecast'])
    SUMMARY.write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
