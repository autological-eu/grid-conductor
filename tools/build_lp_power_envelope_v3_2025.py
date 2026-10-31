"""Correct the A75 LP power candidate for preexisting capacity corrections.

The old v2 weather factor used raw PyPSA fleet nameplate even when the retained
LP already had a larger capacity-corrected availability envelope. This dated
v3 candidate scales only beyond the larger of those two demonstrated powers.
"""
from __future__ import annotations

import csv
import json

import numpy as np

from baselines.compact.source import ROOT, digest

OLD = ROOT/'data/bidding-zone-network-2025/zone-tech-power-envelope-v2/hourly.npz'
OLD_RECEIPT = ROOT/'research/data/zone-tech-power-envelope-2025.json'
FLEET = ROOT/'research/data/adequacy-2025/zone-technology.csv'
OUT = ROOT/'data/bidding-zone-network-2025/lp-power-envelope-v3/hourly.npz'
SUMMARY = ROOT/'research/data/lp-power-envelope-v3-2025.json'
WEATHER = {'solar', 'onshore_wind', 'offshore_wind'}
WATER = {'ror', 'reservoir'}


def build():
    old_receipt = json.loads(OLD_RECEIPT.read_text())
    if digest(OLD) != old_receipt['hourly_sha256']:
        raise ValueError('Changed v2 observed-power witness')
    with np.load(OLD) as archive:
        keys = [tuple(map(str, row)) for row in archive['keys']]
        original = archive['original_available_mw']
        observed = archive['demonstrated_running_peak_mw']
        old_candidate = archive['candidate_available_mw']
    fleet = {(r['zone'], r['technology']): float(r['source_fleet_nameplate_mw'])
             for r in csv.DictReader(FLEET.open())}
    if len(keys) != 624 or set(keys) != set(fleet) or original.shape != (8760, 624):
        raise ValueError('Changed zone-technology power mapping')
    adjusted = original.copy()
    coverage = []
    for j, (zone, tech) in enumerate(keys):
        effective_ceiling = max(fleet[zone,tech], float(original[:,j].max()))
        evidence = observed[:,j] > effective_ceiling + 1.0
        if not evidence.any():
            continue
        if tech in WATER:
            continue
        if tech in WEATHER:
            if effective_ceiling <= 0:
                raise ValueError(f'No weather profile to scale for {zone}/{tech}')
            adjusted[:,j] = original[:,j] * np.where(evidence,
                np.maximum(1, observed[:,j]/effective_ceiling), 1)
            if np.any((original[:,j] == 0) & (adjusted[:,j] != 0)):
                raise ValueError('Weather-zero hour gained supply')
        else:
            adjusted[:,j] = np.where(evidence, np.maximum(original[:,j], observed[:,j]), original[:,j])
        coverage.append(dict(zone=zone, technology=tech,
                             source_nameplate_mw=fleet[zone,tech],
                             current_model_peak_available_mw=float(original[:,j].max()),
                             observed_peak_mw=float(observed[:,j].max()),
                             candidate_incremental_available_twh=float((adjusted[:,j]-original[:,j]).sum()/1e6)))
    if np.any(adjusted < original-1e-6) or not np.isfinite(adjusted).all():
        raise ValueError('Candidate narrowed or invalidated source availability')
    if np.any(adjusted > old_candidate + 1e-5):
        raise ValueError('Corrected candidate exceeds old overstated envelope')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT, keys=np.asarray(keys, dtype='U32'),
                        original_available_mw=original, candidate_available_mw=adjusted,
                        observed_running_peak_mw=observed)
    result = dict(status='corrected_dated_power_candidate_not_baseline', hours=8760,
                  zone_technology_rows=len(keys), changed_rows=int(np.any(adjusted>original+1e-8, axis=0).sum()),
                  incremental_available_twh=float((adjusted-original).sum()/1e6),
                  old_v2_incremental_available_twh=float((old_candidate-original).sum()/1e6),
                  source_old_witness_sha256=digest(OLD), source_fleet_sha256=digest(FLEET),
                  hourly_sha256=digest(OUT), revised_rows=coverage,
                  limitations=['Retrospective A75 peak is a power diagnostic, not a weather forecast or outage schedule',
                               'Effective current-model ceiling uses peak modeled hourly availability as a conservative proxy',
                               'Hydro energy, water and fixed reservoir output remain unchanged'])
    SUMMARY.write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    result=build()
    print(json.dumps({k:result[k] for k in ('changed_rows','incremental_available_twh','old_v2_incremental_available_twh')},indent=2))
