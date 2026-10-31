"""Reclear 2025 with dated A75 power additions and frozen old offer bids.

The new technology-specific columns carry only the incremental hourly
availability. Original pooled renewable offers, fixed hydro and water stay
unchanged. Missing-fleet bids are explicit provisional proxies.
"""
from __future__ import annotations

import csv
import fcntl
import json
import time

import numpy as np
from scipy.sparse import hstack

from baselines.compact.evaluation import CARRIER, OFFERS, a11_component_lp, offer_groups, physical_lp, saved_annual
from baselines.compact.lp import clear_hour, solver
from baselines.compact.source import ROOT, digest, grouped_fit_inputs

POWER = ROOT / 'data/bidding-zone-network-2025/lp-power-envelope-v3/hourly.npz'
POWER_SUMMARY = ROOT / 'research/data/lp-power-envelope-v3-2025.json'
OUT = ROOT / 'data/bidding-zone-network-2025/generation-power-lp-v2'
SUMMARY = ROOT / 'research/data/generation-power-lp-v2-2025.json'
ZERO_BID = {'onshore_wind', 'offshore_wind', 'solar', 'ror', 'geothermal'}


def candidate(network: str):
    model = physical_lp() if network == 'original' else a11_component_lp()
    costs, _ = saved_annual()
    schema, data, _ = grouped_fit_inputs()
    receipt = json.loads(POWER_SUMMARY.read_text())
    if digest(POWER) != receipt['hourly_sha256'] or receipt['zone_technology_rows'] != 624:
        raise ValueError('A75 power witness changed')
    with np.load(POWER) as archive:
        keys = [tuple(map(str, row)) for row in archive['keys']]
        original = archive['original_available_mw']
        adjusted = archive['candidate_available_mw']
    if original.shape != (8760, 624) or len(keys) != len(set(keys)):
        raise ValueError('A75 power chronology/key mismatch')
    indexed = {(g['zone'], g['technology']): i for i, g in enumerate(schema['groups'])}
    for j, key in enumerate(keys):
        if key in indexed:
            np.testing.assert_allclose(original[:, j], data['capacity'][:, indexed[key]], atol=1e-5, rtol=0)
        elif original[:, j].max() > 1e-6:
            raise ValueError(f'Unmapped existing grouped availability {key}')
    grouped, _ = offer_groups(schema, model)
    offers = json.loads(OFFERS.read_text())
    if len(offers) > model['ng']:
        raise ValueError('Source offer count changed')
    technology_columns = {}
    for g, ids in grouped.items():
        technology_columns.setdefault(schema['groups'][g]['technology'], []).extend(ids)
    for j, row in enumerate(offers):
        kinds = {CARRIER[k] for k in row['source_carriers']}
        if len(kinds) == 1 and 'emergency' not in kinds:
            technology_columns.setdefault(next(iter(kinds)), []).append(j)
    columns = []
    added_availability = []
    added_costs = []
    review = []
    for j, (zone, tech) in enumerate(keys):
        delta = adjusted[:, j] - original[:, j]
        if delta.max() <= 1e-7:
            continue
        if np.any(delta < -1e-6) or tech in {'ror', 'reservoir'}:
            raise ValueError(f'Changed hydro/water or narrowed availability {zone}/{tech}')
        zone_ids = np.flatnonzero(model['offer_zones'] == zone)
        if not len(zone_ids):
            raise ValueError(f'No zonal LP injection column: {zone}')
        representative = model['A'][:, int(zone_ids[0])]
        if any((representative != model['A'][:, int(k)]).nnz for k in zone_ids):
            raise ValueError(f'Non-unique generator injection at {zone}')
        columns.append(representative)
        group = indexed.get((zone, tech))
        local = grouped[group] if group is not None else []
        if tech in ZERO_BID:
            price = np.zeros(8760)
            bid_source = 'zero_bid_increment_weather_shaped_if_renewable'
        elif local:
            price = costs[:, local].max(axis=1)
            bid_source = 'flat_extension_of_local_fitted_offer_tail'
        else:
            global_ids = sorted(set(technology_columns.get(tech, [])))
            if not global_ids:
                raise ValueError(f'No same-technology cost proxy: {tech}')
            price = np.median(costs[:, global_ids], axis=1)
            bid_source = 'median_existing_same_technology_offer_proxy'
        added_availability.append(delta)
        added_costs.append(price)
        review.append(dict(zone=zone, technology=tech, incremental_available_twh=float(delta.sum()/1e6),
                           peak_increment_mw=float(delta.max()), bid_source=bid_source,
                           preexisting_group=group is not None, local_pure_offers=len(local)))
    if len(review) != receipt['changed_rows']:
        raise ValueError('Did not transfer all dated availability uplifts')
    A = hstack([model['A'][:, :model['ng']], *columns,
                model['A'][:, model['ng']:]], format='csc')
    nnew = len(columns)
    result = model | dict(A=A, ng=model['ng'] + nnew,
        availability=np.column_stack([model['availability'], *added_availability]),
        emergency_mask=np.r_[model['emergency_mask'], np.zeros(nnew, bool)],
        offer_zones=np.r_[model['offer_zones'], [r['zone'] for r in review]])
    candidate_costs = np.column_stack([costs, *added_costs])
    if abs(sum(r['incremental_available_twh'] for r in review) - receipt['incremental_available_twh']) > 1e-6:
        raise ValueError('Lost A75 candidate supply volume')
    return result, candidate_costs, review


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'job.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if SUMMARY.exists() or any((OUT / f'{name}.npz').exists() for name in ('original', 'a11')):
            raise FileExistsError('Existing A75 annual LP candidate')
        _, baseline = saved_annual()
        schema, data, _ = grouped_fit_inputs()
        observed = data['observed_prices']
        mask = np.isfinite(observed)
        outcomes = {}
        previous = baseline['row_duals'][:, :len(schema['zones'])]
        for network in ('original', 'a11'):
            model, costs, review = candidate(network)
            highs = solver(model, costs)
            values = np.empty((8760, model['A'].shape[1]))
            duals = np.empty((8760, model['A'].shape[0]))
            objective = np.empty(8760)
            residual = 0.
            started = time.perf_counter()
            for hour in range(8760):
                values[hour], duals[hour], objective[hour], error = clear_hour(highs, model, costs, hour)
                residual = max(residual, error)
            if objective[hour] > baseline['objectives'][hour] + .1:
                    raise ValueError(f'Relaxed generation candidate raised optimum: {network}/{hour}')
            seconds = time.perf_counter() - started
            emergency = float(values[:, :model['ng']][:, model['emergency_mask']].sum())
            if emergency > 1e-6 or residual >= 1e-4:
                raise ValueError(f'Full-year generation gate failed: {network}')
            new_start = 799
            added_dispatch = values[:, new_start:model['ng']]
            if added_dispatch.shape[1] != len(review):
                raise ValueError('New offer ordering changed')
            for j, row in enumerate(review):
                row['new_offer_dispatch_twh'] = float(added_dispatch[:, j].sum()/1e6)
            path = OUT / f'{network}.npz'
            np.savez_compressed(path, values=values, row_duals=duals,
                                objectives=objective, hours=np.arange(8760),
                                optimal=np.ones(8760, bool))
            prices = duals[:, :len(schema['zones'])]
            outcomes[network] = dict(hours=8760, solve_seconds=seconds,
                maximum_primal_residual_mw=residual, emergency_mwh=emergency,
                price_mae_eur_mwh=float(abs(prices[mask]-observed[mask]).mean()),
                objective_reduction_from_baseline_eur=float(baseline['objectives'].sum()-objective.sum()),
                added_offer_dispatch_twh=float(added_dispatch.sum()/1e6),
                added_offer_available_twh=float(sum(r['incremental_available_twh'] for r in review)),
                witness_sha256=digest(path), offer_rows=review,
                zonal_price_mae=[dict(zone=zone,
                    original_baseline_mae=float(abs(previous[mask[:,j],j]-observed[mask[:,j],j]).mean()) if mask[:,j].any() else None,
                    candidate_mae=float(abs(prices[mask[:,j],j]-observed[mask[:,j],j]).mean()) if mask[:,j].any() else None)
                    for j,zone in enumerate(schema['zones'])])
        summary = dict(status='full_year_A75_power_sensitivity_not_baseline',
            source_power_sha256=digest(POWER),
            source_network_sha256=digest(ROOT / 'research/data/a11-component-network-2025.json'),
            original_baseline_price_mae_eur_mwh=float(abs(previous[mask]-observed[mask]).mean()),
            outcomes=outcomes,
            limitations=['Retrospective A75 running peaks; no prospective capacity/outage validation',
                         'Original pooled renewable availability is preserved; incremental weather-shaped MW enters separate zero-bid columns',
                         'Missing dedicated fleets use provisional median same-technology bids; local existing technology uses a flat bid tail',
                         'Fixed hydro/water and original renewable weather-zero hours unchanged',
                         'No bid refit, generation-mix allocation audit, independent time transfer or scenario-response validation'])
        SUMMARY.write_text(json.dumps(summary, indent=2) + '\n')
        return summary


if __name__ == '__main__':
    result = run()
    print(json.dumps({key: {k: v for k, v in outcome.items() if k not in {'offer_rows', 'zonal_price_mae'}}
                      for key, outcome in result['outcomes'].items()}, indent=2))
