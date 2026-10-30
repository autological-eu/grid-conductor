"""Independent physical and source-covered generation audit of a timing trial."""
from __future__ import annotations

import argparse
import json

import numpy as np

from .evaluation import ANCHOR, CARRIER, LAYOUT, offer_groups, physical_lp, saved_annual
from .nordic_storage import OUTPUT, WATER, physical_basis, sha, sources
from .source import grouped_fit_inputs


def generation(schema, data, model, native, values, hydro_delta):
    groups, mixed = offer_groups(schema, model)
    quantities = np.zeros((8760, len(schema['groups'])))
    for group, ids in groups.items():
        if ids:
            quantities[:, group] = values[:, ids].sum(axis=1)
    layout = json.loads(LAYOUT.read_text())
    carriers = native.generators.carrier.to_numpy(dtype=str)
    member_capacity = (native.get_switchable_as_dense('Generator', 'p_max_pu').to_numpy()
                       * native.generators.p_nom.to_numpy())
    keys = {(group['zone'], group['technology']): i for i, group in enumerate(schema['groups'])}
    for column in mixed:
        members = layout['members'][column]
        zone = str(model['offer_zones'][column])
        kinds = {CARRIER[carriers[member]] for member in members}
        denominator = member_capacity[:, members].sum(axis=1)
        fallback = sum((data['capacity'][:, keys[zone, kind]] for kind in kinds
                        if (zone, kind) in keys), start=np.zeros(8760))
        use = np.where(denominator > 1e-8, denominator, fallback)
        if np.any((use <= 1e-8) & (values[:, column] > 1e-5)):
            raise ValueError('Mixed offer has no source availability')
        for kind in kinds:
            ids = [member for member in members if CARRIER[carriers[member]] == kind]
            if (zone, kind) not in keys:
                if member_capacity[:, ids].max(initial=0) > 1e-8:
                    raise ValueError(f'Unmapped mixed offer source: {zone}/{kind}')
                continue
            numerator = np.where(denominator > 1e-8,
                                 member_capacity[:, ids].sum(axis=1),
                                 data['capacity'][:, keys[zone, kind]])
            quantities[:, keys[zone, kind]] += np.divide(
                values[:, column] * numerator, use,
                out=np.zeros(8760), where=use > 0)
    ci = np.array([g['country_id'] for g in schema['groups']])
    ti = np.array([schema['technologies'].index(g['technology']) for g in schema['groups']])
    modeled = data['fixed_generation'].copy()
    for group in range(len(schema['groups'])):
        modeled[:, ci[group], ti[group]] += quantities[:, group]
    norway = next(g['country_id'] for g in schema['groups'] if g['country'] == 'NO')
    reservoir = schema['technologies'].index('reservoir')
    modeled[:, norway, reservoir] += hydro_delta.sum(axis=1)
    known = np.isfinite(data['observed_generation'])
    return float(abs(modeled[known] - data['observed_generation'][known]).mean() / 1000)


def audit(alpha=0.1):
    name = f'alpha-{alpha:.2f}'
    path = OUTPUT / f'{name}.npz'
    receipt = json.loads((OUTPUT / f'{name}.json').read_text())
    if receipt['witness_sha256'] != sha(path):
        raise ValueError('Storage trial witness changed')
    with np.load(path) as archive:
        result = {key: archive[key] for key in archive.files}
    native, _, units, water, allocation = sources()
    model = physical_lp()
    cost, baseline = saved_annual()
    zone_share, branch = physical_basis(native, units, allocation, model['zones'])
    delta = result['power'] - water['power']
    if abs(delta.reshape(365, 24, 5).sum(axis=1)).max() > 1e-5:
        raise ValueError('Hydro daily energy changed')
    stock = water['initial'] + np.cumsum(water['inflow'] - water['spill']
                                         - result['power'] / water['eta'], axis=0)
    if abs(stock - result['inventory']).max() > 1e-5 or abs(stock[23::24] - water['inventory'][23::24]).max() > 1e-4:
        raise ValueError('Hydro stock replay failed')
    if np.maximum(-stock, stock - water['capacity']).max() > 1e-4:
        raise ValueError('Hydro stock bound failed')
    values = result['values']
    actual = (model['A'] @ values.T).T
    load = model['load'] - delta @ zone_share
    flow = model['flow'] + delta @ branch
    rowlo = np.column_stack((load, model['island_rhs'], -model['ratings'] - flow))
    rowhi = np.column_stack((load, model['island_rhs'], model['ratings'] - flow))
    ng, nl = model['ng'], model['nl']
    collo = np.column_stack((np.zeros((8760, ng)), model['link_min']))
    colhi = np.column_stack((model['availability'], model['link_max']))
    residual = max(float(np.maximum(rowlo - actual, 0).max()),
                   float(np.maximum(actual - rowhi, 0).max()),
                   float(np.maximum(collo - values[:, :ng + nl], 0).max()),
                   float(np.maximum(values[:, :ng + nl] - colhi, 0).max()))
    if residual > 1e-4 or values[:, :ng][:, model['emergency_mask']].sum() > 1e-4:
        raise ValueError('Physical or no-emergency replay failed')
    objectives = (values[:, :ng] * cost).sum(axis=1)
    if max(abs(objectives - result['objectives'])) > .05:
        raise ValueError('Hourly LP objective replay failed')
    schema, data, _ = grouped_fit_inputs()
    base_mix = generation(schema, data, model, native, baseline['values'], np.zeros_like(delta))
    trial_mix = generation(schema, data, model, native, values, delta)
    return dict(maximum_primal_residual_mw=residual,
                maximum_objective_gap_eur=float(abs(objectives - result['objectives']).max()),
                maximum_stock_replay_mwh=float(abs(stock - result['inventory']).max()),
                baseline_generation_mae_gw=base_mix,
                candidate_generation_mae_gw=trial_mix)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--alpha', type=float, default=0.1)
    args = parser.parse_args()
    print(json.dumps(audit(args.alpha), indent=2))
