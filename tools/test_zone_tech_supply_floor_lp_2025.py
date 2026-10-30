"""Frozen-bid LP sensitivity for existing-offer A75 supply floors only."""
from __future__ import annotations

import csv
import json
import time

import numpy as np

from baselines.compact.evaluation import offer_groups, physical_lp, saved_annual
from baselines.compact.lp import clear_hour, solver
from baselines.compact.source import ROOT, digest, grouped_fit_inputs
from tools.build_zone_adequacy_2025 import observed_zonal_generation
from tools.build_zone_tech_supply_candidate_2025 import OUT as INPUT, REVIEW

OUT = ROOT / 'data/bidding-zone-network-2025/zone-tech-observed-floor-lp-v1'
SUMMARY = ROOT / 'research/data/zone-tech-observed-floor-lp-2025.json'


def run():
    if (OUT / 'witness.npz').exists():
        raise FileExistsError('Existing supply-floor LP witness; refusing duplicate solve')
    schema, data, _ = grouped_fit_inputs()
    model = physical_lp()
    costs, baseline = saved_annual()
    grouped, _ = offer_groups(schema, model)
    with np.load(INPUT / 'hourly.npz') as archive:
        original = archive['original_mw']
        candidate = archive['candidate_mw']
        keys = [tuple(pair) for pair in archive['keys']]
    inventory = list(csv.DictReader(REVIEW.open()))
    if len(inventory) != len(keys) or len(keys) != candidate.shape[1]:
        raise ValueError('Supply-floor input inventory changed')
    group_keys = {(row['zone'], row['technology']): i for i, row in enumerate(schema['groups'])}
    changed = []
    skipped = []
    for j, key in enumerate(keys):
        if key != (inventory[j]['zone'], inventory[j]['technology']):
            raise ValueError('Supply-floor key order changed')
        delta = candidate[:, j] - original[:, j]
        if delta.max() <= 1e-7:
            continue
        group = group_keys.get(key)
        ids = grouped.get(group, []) if group is not None else []
        if not ids:
            skipped.append(dict(zone=key[0], technology=key[1],
                                missing_mwh=float(delta.sum())))
            continue
        ids = np.asarray(ids)
        base = model['availability'][:, ids].sum(axis=1)
        if np.max(abs(base - original[:, j])) > 1e-4:
            raise ValueError(f'LP/group supply mismatch: {key}')
        positive = base > 1e-8
        model['availability'][:, ids] += np.where(
            positive[:, None],
            np.divide(model['availability'][:, ids] * delta[:, None], base[:, None],
                      out=np.zeros((8760, len(ids))), where=positive[:, None]),
            delta[:, None] / len(ids))
        if np.max(abs(model['availability'][:, ids].sum(axis=1) - candidate[:, j])) > 1e-4:
            raise ValueError(f'LP/group supply floor failed: {key}')
        changed.append(dict(zone=key[0], technology=key[1],
                            added_mwh=float(delta.sum()), offer_columns=ids.tolist()))
    if not changed:
        raise ValueError('No existing-offer supply floors available')
    highs = solver(model, costs)
    values = np.empty((8760, model['A'].shape[1]))
    prices = np.empty((8760, model['nz']))
    maximum_residual = 0.0
    started = time.perf_counter()
    for hour in range(8760):
        values[hour], dual, _, residual = clear_hour(highs, model, costs, hour)
        prices[hour] = dual[:model['nz']]
        maximum_residual = max(maximum_residual, residual)
    observed_price = data['observed_prices']
    price_mask = np.isfinite(observed_price)
    previous_price = baseline['row_duals'][:, :model['nz']]
    observed_generation, _, _ = observed_zonal_generation(model['zones'])
    affected = []
    for row in changed:
        key = (row['zone'], row['technology'])
        actual = observed_generation[key]
        mask = np.isfinite(actual)
        ids = row['offer_columns']
        prior = baseline['values'][:, ids].sum(axis=1)
        trial = values[:, ids].sum(axis=1)
        affected.append(dict(zone=key[0], technology=key[1], hours=int(mask.sum()),
                             baseline_generation_mae_mw=float(abs(prior[mask] - actual[mask]).mean()),
                             trial_generation_mae_mw=float(abs(trial[mask] - actual[mask]).mean())))
    summary = dict(status='partial_existing_offer_supply_floor_sensitivity_not_baseline',
                   hours=8760, changed_groups=changed, excluded_missing_offer_groups=skipped,
                   original_price_mae_eur_mwh=float(abs(previous_price[price_mask] - observed_price[price_mask]).mean()),
                   trial_price_mae_eur_mwh=float(abs(prices[price_mask] - observed_price[price_mask]).mean()),
                   affected_generation=affected,
                   emergency_mwh=float(values[:, :model['ng']][:, model['emergency_mask']].sum()),
                   maximum_primal_residual_mw=maximum_residual,
                   solve_seconds=time.perf_counter() - started,
                   input_sha256=digest(INPUT / 'hourly.npz'),
                   limitations=['Retrospective observed-production floor, not forward available energy',
                                'Only existing technology-specific LP offer columns are changed',
                                'Missing fleets and mixed zero-bid offers remain unresolved',
                                'Frozen bids and unchanged physical network; no baseline promotion'])
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / 'witness.npz', values=values, prices=prices)
    summary['witness_sha256'] = digest(OUT / 'witness.npz')
    SUMMARY.write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    result = run()
    print(json.dumps({k: result[k] for k in ('hours', 'original_price_mae_eur_mwh',
                                            'trial_price_mae_eur_mwh', 'emergency_mwh',
                                            'maximum_primal_residual_mw', 'solve_seconds')}, indent=2))
