"""Audited Norway reservoir timing sensitivity on the retained physical LP.

This is a research candidate. Its daily optimization sees only the retained
model's own baseline prices; observed auction prices are evaluation targets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from pathlib import Path

import numpy as np
import pypsa
from scipy.optimize import linprog

from .evaluation import ANCHOR, physical_lp, saved_annual
from .lp import clear_hour, solver
from .source import ROOT, grouped_fit_inputs

WATER = ROOT / 'data/hydro-observations-2025/nve-updated-model-v5'
MAPPING = ROOT / 'data/bidding-zone-network-2025/annual-v7/mapping.json'
ORIGINAL = ROOT / 'data/pypsa-eur/upstream/resources/gridfix-2025/networks/base_s_128_elec.nc'
OUTPUT = ROOT / 'data/bidding-zone-network-2025/nordic-reservoir-timing-v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources():
    summary = json.loads((WATER / 'summary.json').read_text())
    if sha(WATER / 'water.npz') != summary['water_witness_sha256']:
        raise ValueError('NVE water witness changed')
    annual = json.loads((MAPPING.parent / 'summary.json').read_text())
    if sha(MAPPING) != annual['mapping_sha256']:
        raise ValueError('Zonal hydro allocation changed')
    anchored = json.loads((ANCHOR / 'inputs.json').read_text())
    if sha(ANCHOR / 'native.nc') != anchored['files']['native.nc']:
        raise ValueError('Physical network witness changed')
    with np.load(WATER / 'water.npz') as archive:
        water = {key: archive[key] for key in archive.files}
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    native = pypsa.Network(ANCHOR / 'native.nc')
    original = pypsa.Network(ORIGINAL)
    hydro = original.storage_units.query("carrier == 'hydro'")
    norway = hydro.bus.map(original.buses.country).to_numpy() == 'NO'
    units = hydro.loc[norway]
    if len(units) != 5 or water['power'].shape != (8760, len(units)):
        raise ValueError('Norway reservoir fleet does not match NVE water witness')
    mapping = json.loads(MAPPING.read_text())
    allocation = {row['name']: row['shares'] for row in mapping['allocation']
                  if row['component'] == 'FixedReservoir'}
    return native, original, units, water, allocation


def physical_basis(native, units, allocation, zones):
    """PTDF and island changes for one additional MW from each hydro unit."""
    meta = json.loads((ANCHOR / 'inputs.json').read_text())
    bus = list(native.buses.index)
    bus_id = {name: j for j, name in enumerate(bus)}
    zone_of = native.buses.bidding_zone.replace({'ES-IB-MA': 'ES'}).to_dict()
    offsets = np.zeros((len(units), len(bus)))
    zone_share = np.zeros((len(units), len(zones)))
    for k, name in enumerate(units.index):
        if name not in allocation:
            raise ValueError(f'Missing hydro allocation: {name}')
        for node, share in allocation[name].items():
            offsets[k, bus_id[node]] += share
            zone_share[k, zones.index(zone_of[node])] += share
        if abs(zone_share[k].sum() - 1) > 1e-12:
            raise ValueError('Hydro allocation does not conserve generation')
        for zone, zshare in zip(zones, zone_share[k]):
            for node, weight in meta['weights'][zone].items():
                offsets[k, bus_id[node]] -= zshare * weight
    native.determine_network_topology()
    branch, island = [], []
    for _, row in native.sub_networks.iterrows():
        sub = row.obj
        nodes = [bus_id[node] for node in sub.buses_o]
        island.append(offsets[:, nodes].sum(axis=1))
        if len(nodes) > 1:
            sub.calculate_PTDF()
            branch.append(offsets[:, nodes] @ np.asarray(sub.PTDF).T)
    if max(abs(np.array(island)).ravel()) > 1e-10:
        raise ValueError('Hydro perturbation changes physical island energy')
    return zone_share, np.concatenate(branch, axis=1)


def retime(water, power_limits, price_signal, alpha, movement_cost=2.0):
    """Preserve each unit's daily water release and every hourly stock bound."""
    original = water['power']
    result = original.copy()
    lower_triangle = np.tril(np.ones((24, 24)))
    for day in range(365):
        hours = slice(day * 24, (day + 1) * 24)
        for unit in range(original.shape[1]):
            initial = water['initial'][unit] if day == 0 else water['inventory'][day * 24 - 1, unit]
            incoming = np.cumsum(water['inflow'][hours, unit] - water['spill'][hours, unit])
            p0 = original[hours, unit]
            max_power = power_limits[unit]
            bounds = [(max(0, p - alpha * max_power), min(max_power, p + alpha * max_power)) for p in p0]
            if any(low > high + 1e-5 for low, high in bounds):
                raise ValueError('Original reservoir output exceeds turbine bound')
            balance = np.zeros((25, 72))
            balance[:24, :24] = np.eye(24)
            balance[:24, 24:48] = -np.eye(24)
            balance[:24, 48:72] = np.eye(24)
            balance[24, :24] = 1
            target = np.r_[p0, p0.sum()]
            cumulative = np.zeros((48, 72))
            cumulative[:24, :24] = lower_triangle
            cumulative[24:, :24] = -lower_triangle
            eta = water['eta'][unit]
            limit = np.r_[eta * (initial + incoming),
                          eta * (water['capacity'][unit] - initial - incoming)]
            objective = np.r_[-price_signal[hours, unit],
                              np.full(48, movement_cost)]
            solved = linprog(objective, A_ub=cumulative, b_ub=limit,
                             A_eq=balance, b_eq=target,
                             bounds=bounds + [(0, None)] * 48, method='highs')
            if not solved.success:
                raise RuntimeError(f'Water timing infeasible for day {day}, unit {unit}: {solved.message}')
            result[hours, unit] = solved.x[:24]
    stock = np.cumsum(water['inflow'] - water['spill'] - result / water['eta'], axis=0)
    stock += water['initial']
    if np.max(abs(stock[23::24] - water['inventory'][23::24])) > 1e-4:
        raise ValueError('Daily reservoir stock anchor changed')
    if np.max(np.maximum(-stock, stock - water['capacity'])) > 1e-4:
        raise ValueError('Retimed reservoir violates storage capacity')
    if np.max(abs(stock[-1] - water['terminal'])) > 1e-4:
        raise ValueError('Annual reservoir boundary changed')
    return result, stock


def evaluate(alpha=0.1, output=OUTPUT):
    if not 0 < alpha <= 1:
        raise ValueError('Require a positive movement fraction at most one')
    output = Path(output)
    name = f'alpha-{alpha:.2f}'
    if (output / f'{name}.npz').exists() or (output / f'{name}.json').exists():
        raise FileExistsError(f'Existing trial witness: {name}; choose a fresh output path')
    model = physical_lp()
    cost, baseline = saved_annual()
    native, original, units, water, allocation = sources()
    zone_share, branch = physical_basis(native, units, allocation, model['zones'])
    if branch.shape != (5, 255):
        raise ValueError('Physical flow basis changed')
    baseline_prices = baseline['row_duals'][:, :model['nz']]
    proposed, stock = retime(water, units.p_nom.to_numpy(), baseline_prices @ zone_share.T, alpha)
    delta = proposed - water['power']
    updated = model | dict(load=model['load'].copy(), flow=model['flow'].copy())
    highs = solver(updated, cost)
    prices = np.empty((8760, model['nz']))
    objectives = np.empty(8760)
    shortage = np.empty(8760)
    values = np.empty_like(baseline['values'])
    day_scales = np.empty(365)
    maximum_residual = 0.0
    started = time.perf_counter()
    for day in range(365):
        hours = slice(day * 24, (day + 1) * 24)
        change = delta[hours]
        def set_scale(scale):
            updated['load'][hours] = model['load'][hours] - scale * (change @ zone_share)
            updated['flow'][hours] = model['flow'][hours] + scale * (change @ branch)
        def feasible(scale):
            set_scale(scale)
            for hour in range(hours.start, hours.stop):
                try:
                    x, _, _, _ = clear_hour(highs, updated, cost, hour)
                except RuntimeError as error:
                    if 'Infeasible' not in str(error):
                        raise
                    return False
                if x[:model['ng']][model['emergency_mask']].sum() > 1e-5:
                    return False
            return True
        low, high = 0.0, 1.0
        if feasible(1.0):
            low = 1.0
        else:
            for _ in range(8):
                mid = (low + high) / 2
                if feasible(mid):
                    low = mid
                else:
                    high = mid
        day_scales[day] = low
        set_scale(low)
        for hour in range(hours.start, hours.stop):
            x, duals, objective, error = clear_hour(highs, updated, cost, hour)
            values[hour] = x
            prices[hour] = duals[:model['nz']]
            objectives[hour] = objective
            shortage[hour] = x[:model['ng']][model['emergency_mask']].sum()
            maximum_residual = max(maximum_residual, error)
        if day % 60 == 0:
            print(f'day {day}: feasible scale {low:.4f}', flush=True)
    delta *= np.repeat(day_scales, 24)[:, None]
    proposed = water['power'] + delta
    stock = water['initial'] + np.cumsum(water['inflow'] - water['spill'] - proposed / water['eta'], axis=0)
    if np.max(abs(stock[23::24] - water['inventory'][23::24])) > 1e-4:
        raise ValueError('Network scaling changed daily water anchors')
    if np.max(np.maximum(-stock, stock - water['capacity'])) > 1e-4:
        raise ValueError('Network scaling violated water inventory')
    if shortage.max() > 1e-5:
        raise ValueError('Candidate requires emergency supply')
    schema, data, _ = grouped_fit_inputs()
    observed = data['observed_prices']
    price_mask = np.isfinite(observed)
    def metrics(series):
        return {zone: float(abs(series[price_mask[:, j], j] - observed[price_mask[:, j], j]).mean())
                for j, zone in enumerate(model['zones']) if price_mask[:, j].any()}
    original_metrics, candidate_metrics = metrics(baseline_prices), metrics(prices)
    output.mkdir(parents=True, exist_ok=True)
    receipt = dict(status='retrospective_reservoir_timing_sensitivity_not_accepted',
                   alpha=alpha, movement_cost_eur_mwh=2.0,
                   forecast='retained model baseline price, no observed price lookup',
                   changed_reservoir_mwh=float(abs(delta).sum()),
                   maximum_hourly_change_mw=float(abs(delta).max()),
                   network_scale_min=float(day_scales.min()),
                   network_scale_mean=float(day_scales.mean()),
                   network_clipped_days=int((day_scales < 1).sum()),
                   network_zero_days=int((day_scales == 0).sum()),
                   maximum_primal_residual_mw=maximum_residual,
                   maximum_daily_stock_difference_mwh=float(abs(stock[23::24] - water['inventory'][23::24]).max()),
                   emergency_mwh=float(shortage.sum()),
                   solve_seconds=time.perf_counter() - started,
                   baseline_price_mae=original_metrics,
                   candidate_price_mae=candidate_metrics,
                   input_sha256={str(path.relative_to(ROOT)): sha(path) for path in
                                 [WATER / 'water.npz', MAPPING, ORIGINAL, ANCHOR / 'native.nc']})
    np.savez_compressed(output / f'{name}.npz', power=proposed, inventory=stock,
                        price=prices, objectives=objectives, values=values,
                        day_scales=day_scales)
    receipt['witness_sha256'] = sha(output / f'{name}.npz')
    (output / f'{name}.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--alpha', type=float, default=0.1)
    arguments = parser.parse_args()
    print(json.dumps(evaluate(arguments.alpha), indent=2))
