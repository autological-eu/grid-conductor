"""Infer dated zonal technology power ceilings from matched 2025 A75 output.

The observed running peak is a lower bound on installed *power* after its
observation, not evidence of weather, inflow, fuel or hourly market availability.
This is an input candidate, not the accepted LP baseline.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter

import numpy as np

from baselines.compact.source import ROOT, digest, grouped_fit_inputs
from tools.build_zone_adequacy_2025 import PSR, observed_zonal_generation

OUT = ROOT / 'data/bidding-zone-network-2025/zone-tech-power-envelope-v2'
REVIEW = ROOT / 'research/data/zone-tech-power-envelope-2025.csv'
SUMMARY = ROOT / 'research/data/zone-tech-power-envelope-2025.json'
FLEET = ROOT / 'research/data/adequacy-2025/zone-technology.csv'
FLEET_AUDIT = ROOT / 'research/data/adequacy-2025/summary.json'
WEATHER_LIMITED = {'onshore_wind', 'offshore_wind', 'solar'}
WATER_LIMITED = {'ror', 'reservoir'}
EXCEEDANCE_TOLERANCE_MW = 1.0  # Match the source adequacy inventory's rounding gate.


def build():
    schema, data, _ = grouped_fit_inputs()
    fleet_audit = json.loads(FLEET_AUDIT.read_text())
    if digest(FLEET) != fleet_audit['output_sha256']['zone-technology.csv']:
        raise ValueError('Source fleet adequacy inventory changed')
    fleet = {(row['zone'], row['technology']): float(row['source_fleet_nameplate_mw'])
             for row in csv.DictReader(FLEET.open())}
    observed, scopes, checked = observed_zonal_generation(schema['zones'])
    groups = {(row['zone'], row['technology']): i for i, row in enumerate(schema['groups'])}
    keys = [(zone, tech) for zone in schema['zones'] for tech in PSR]
    original = np.zeros((8760, len(keys)))
    adjusted = np.zeros_like(original)
    power = np.zeros_like(original)
    demonstrated = np.zeros_like(original)
    rows = []
    counts = Counter()
    for j, (zone, tech) in enumerate(keys):
        group = groups.get((zone, tech))
        if group is not None:
            original[:, j] = data['capacity'][:, group]
        adjusted[:, j] = original[:, j]
        nameplate = fleet[zone, tech]
        report = observed[zone, tech]
        scope = '|'.join(sorted(scopes[zone])) or 'unavailable'
        matched = scope == 'bidding zone'
        known = np.isfinite(report) if matched else np.zeros(8760, bool)
        if matched:
            demonstrated[:, j] = np.maximum.accumulate(np.where(known, report, 0))
        # Keep the original source ceiling until a dated observation exceeds it.
        power[:, j] = np.where(demonstrated[:, j] > nameplate + EXCEEDANCE_TOLERANCE_MW,
                               demonstrated[:, j], nameplate)
        first_exceedance = np.flatnonzero(known &
                                          (report > nameplate + EXCEEDANCE_TOLERANCE_MW))
        status = ('unmatched_scope' if not matched else
                  'no_observation' if not known.any() else 'no_new_power')
        if first_exceedance.size:
            counts['rows_with_power_evidence_above_nameplate'] += 1
            counts['observed_exceedance_hours'] += int((known &
                (report > nameplate + EXCEEDANCE_TOLERANCE_MW)).sum())
            status = 'power_ceiling_only'
        if tech in WEATHER_LIMITED and nameplate > 0:
            # Scale existing weather availability, retaining its zero/weather
            # chronology; never copy generation into renewable availability.
            scale = power[:, j] / nameplate
            adjusted[:, j] = original[:, j] * scale
            if np.any(scale > 1 + 1e-8):
                status = 'weather_profile_scaled_by_demonstrated_power'
        elif tech in WATER_LIMITED:
            # Turbine power can be revised; inflow and stock cannot be inferred
            # from an observed peak. Preserve the fixed hydro/ror energy profile.
            if first_exceedance.size:
                status = 'hydro_power_only_water_unreconciled'
        elif first_exceedance.size:
            adjusted[:, j] = np.where(power[:, j] > nameplate,
                                       np.maximum(original[:, j], demonstrated[:, j]),
                                       original[:, j])
            if (adjusted[:, j] > original[:, j] + 1e-8).any():
                status = 'new_offer_required' if group is None else 'existing_dispatchable_group'
        uplift = adjusted[:, j] - original[:, j]
        if first_exceedance.size and np.any(abs(uplift[:first_exceedance[0]]) > 1e-8):
            raise ValueError('Candidate changed supply before first power observation')
        if uplift.max() > 1e-8:
            counts['availability_uplift_rows'] += 1
            counts['availability_uplift_mwh'] += float(uplift.sum())
            if group is None:
                counts['availability_rows_without_group'] += 1
        rows.append(dict(zone=zone, technology=tech,
                         model_group_index='' if group is None else group,
                         fleet_nameplate_source='retained PyPSA-Eur zonal fleet inventory',
                         original_fleet_nameplate_mw=round(nameplate, 6),
                         production_source=f'ENTSO-E A75 {PSR[tech]} hourly generation',
                         observed_scope=scope, observed_hours=int(known.sum()),
                         observed_peak_mw=(round(float(report[known].max()), 6) if known.any() else ''),
                         first_observed_above_nameplate_utc=(
                             str(np.datetime64('2025-01-01T00') + np.timedelta64(int(first_exceedance[0]), 'h'))+'Z'
                             if first_exceedance.size else ''),
                         demonstrated_power_ceiling_peak_mw=round(float(power[:, j].max()), 6),
                         original_available_mwh=round(float(original[:, j].sum()), 6),
                         candidate_available_mwh=round(float(adjusted[:, j].sum()), 6),
                         treatment=status))
    if np.any(adjusted < original - 1e-6) or not np.isfinite(adjusted).all():
        raise ValueError('Candidate lowered or invalidated availability')
    if any(not np.array_equal(adjusted[:, j], original[:, j]) for j, (_, tech) in enumerate(keys)
           if tech in WATER_LIMITED):
        raise ValueError('Water-limited energy profile changed')
    if np.any(np.diff(demonstrated, axis=0) < -1e-8):
        raise ValueError('Demonstrated power history decreased')
    for j, (_, tech) in enumerate(keys):
        if tech in WEATHER_LIMITED and np.any((original[:, j] == 0) & (adjusted[:, j] != 0)):
            raise ValueError('Weather-zero hour gained renewable availability')
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / 'hourly.npz', keys=np.asarray(keys, dtype='U32'),
                        original_available_mw=original, candidate_available_mw=adjusted,
                        demonstrated_running_peak_mw=demonstrated,
                        candidate_power_ceiling_mw=power)
    with REVIEW.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(status='dated_demonstrated_power_candidate_not_baseline',
                   hours=8760, rows=len(rows), a75_receipts_checked=checked,
                   **dict(counts),
                   source_sha256={
                       'fleet_inventory': digest(FLEET),
                       'grouped_input': digest(ROOT / 'data/bidding-zone-network-2025/sigmoid-month-pairs-v1/inputs.npz'),
                       'solar_delta': digest(ROOT / 'data/bidding-zone-network-2025/solar-country-fit-v1/delta.npz'),
                       'a75_receipt_set': hashlib.sha256(''.join(
                           f'{zone}/{month:02d}:{digest(path)}\n'
                           for zone in schema['zones'] for month in range(1, 13)
                           if (path := ROOT / f'data/carbon-pilot/map-2025/{zone}/{month:02d}.receipt.json').exists()
                       ).encode()).hexdigest()},
                   hourly_sha256=digest(OUT / 'hourly.npz'), csv_sha256=digest(REVIEW),
                   limits=['Running observed peak increases a power ceiling only from its observed hour onward',
                           'Renewable candidate scales original weather availability only where source nameplate exists',
                           'Hydro power ceilings do not add water or change fixed output',
                           'Missing profiles/offers and outage timing need source reconciliation',
                           'Retrospective A75 evidence is not independent price validation'])
    SUMMARY.write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
