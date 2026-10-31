"""Bounded annual Norwegian reservoir timing test, with no added water.

This is a diagnostic schedule, not an auction bid or an accepted baseline.
The model-only retained LP prices provide a retrospective opportunity signal.
"""
from __future__ import annotations

import json
import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import hstack, tril, vstack, eye, csr_matrix

from baselines.compact.evaluation import physical_lp, saved_annual
from baselines.compact.lp import clear_hour, solver
from baselines.compact.nordic_storage import OUTPUT, physical_basis, sha, sources
from baselines.compact.source import ROOT, grouped_fit_inputs

OUT = ROOT / 'data/bidding-zone-network-2025/norway-seasonal-water-value-v1'
REPORT = ROOT / 'research/data/norway-seasonal-water-value-2025.json'


def schedule(water, turbines, signal, alpha=0.05):
    """Move at most alpha of each day's original energy between days.

    Keep the annual terminal stock and stay within hourly stock/turbine bounds.
    Weekly observed-stock trajectory is respected within 5% of storage capacity.
    """
    original = water['power']
    days = 365
    change = np.zeros_like(original)
    lower = tril(csr_matrix(np.ones((days, days))), format='csr')
    bounds_record = []
    for unit in range(original.shape[1]):
        p = original[:, unit].reshape(days, 24)
        daily = p.sum(axis=1)
        # Daily scalar preserves the inherited intraday shape. Hourly power and
        # stock limits are checked after solving; the LP bounds protect power.
        upper_scale = np.min(np.where(p > 1e-9, turbines[unit] / np.maximum(p, 1e-9), np.inf), axis=1)
        lo = np.maximum(-alpha * daily, -daily)
        hi = np.minimum(alpha * daily, (upper_scale - 1) * daily)
        if np.any(lo > hi + 1e-6):
            raise ValueError('Original turbine output exceeds ceiling')
        # Source stock at day ends is the reference; local deviations are bounded.
        inventory = water['inventory'][23::24, unit]
        cap = float(water['capacity'][unit])
        eta = float(water['eta'][unit])
        weekly = np.arange(6, days, 7)
        rows = lower[weekly]
        band = .05 * cap
        u = np.minimum(inventory[weekly], band) * eta
        l = np.minimum(cap - inventory[weekly], band) * eta
        A_ub = vstack([hstack([rows, csr_matrix((len(weekly), days))]),
                       hstack([-rows, csr_matrix((len(weekly), days))]),
                       hstack([eye(days, format='csr'), -eye(days, format='csr')]),
                       hstack([-eye(days, format='csr'), -eye(days, format='csr')])], format='csr')
        b_ub = np.r_[u, l, np.zeros(days), np.zeros(days)]
        A_eq = hstack([csr_matrix(np.ones((1, days))), csr_matrix((1, days))], format='csr')
        # Water value: smoothed model opportunity price, adjusted for fullness.
        # This is deliberately not calibrated to ENTSO-E prices.
        unit_signal = signal[:, unit].reshape(days, 24)
        daily_price = np.sum(unit_signal * p, axis=1) / np.maximum(daily, 1e-9)
        smooth = np.convolve(np.pad(daily_price, (15, 15), mode='edge'),
                             np.ones(31) / 31, mode='valid')
        fullness = inventory / cap
        water_value = np.maximum(0., smooth + 30 * (.5 - fullness))
        objective = np.r_[water_value - daily_price, np.full(days, 2.)]
        solved = linprog(objective, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq,
                         b_eq=[0.], bounds=list(zip(lo, hi)) + [(0, None)] * days,
                         method='highs')
        if not solved.success:
            raise RuntimeError(f'Water-value scheduling failed for unit {unit}: {solved.message}')
        delta = solved.x[:days]
        change[:, unit] = (p * (delta / np.maximum(daily, 1e-9))[:, None]).ravel()
        bounds_record.append(dict(unit=unit, water_value_min=float(water_value.min()),
                                  water_value_max=float(water_value.max()),
                                  changed_energy_twh=float(np.abs(delta).sum() / 1e6)))
    return change, bounds_record


def run():
    if REPORT.exists() or (OUT / 'trial.npz').exists():
        raise FileExistsError('Seasonal-water trial already exists')
    model = physical_lp()
    costs, baseline = saved_annual()
    native, original, units, water, allocation = sources()
    zone_share, branch = physical_basis(native, units, allocation, model['zones'])
    prices0 = baseline['row_duals'][:, :model['nz']]
    signal = prices0 @ zone_share.T
    change, curves = schedule(water, units.p_nom.to_numpy(), signal)
    proposed = water['power'] + change
    stock = water['initial'] + np.cumsum(water['inflow'] - water['spill'] - proposed / water['eta'], axis=0)
    if np.max(np.maximum(-stock, stock - water['capacity'])) > 1e-4:
        raise ValueError('Hourly reservoir stock infeasible')
    if np.max(np.abs(stock[-1] - water['terminal'])) > 1e-4:
        raise ValueError('Annual terminal stock changed')
    if np.max(proposed - units.p_nom.to_numpy()) > 1e-4 or proposed.min() < -1e-4:
        raise ValueError('Turbine bound violated')
    updated = model | dict(load=model['load'].copy(), flow=model['flow'].copy())
    highs = solver(updated, costs)
    results = None
    start = time.perf_counter()
    # One global scale preserves the annual water balance. A failed physical
    # reclear rejects that step; no emergency dispatch or border widening.
    for scale in (1., .5, .25, .125, .0625, .03125):
        updated['load'][:] = model['load'] - scale * (change @ zone_share)
        updated['flow'][:] = model['flow'] + scale * (change @ branch)
        prices = np.empty_like(prices0)
        emergency = 0.
        residual = 0.
        try:
            for hour in range(8760):
                x, dual, _, error = clear_hour(highs, updated, costs, hour)
                emergency += float(x[:model['ng']][model['emergency_mask']].sum())
                residual = max(residual, error)
                prices[hour] = dual[:model['nz']]
            if emergency > 1e-5 or residual > 1e-4:
                continue
            results = (scale, prices, residual, emergency)
            break
        except RuntimeError as exc:
            if 'Infeasible' not in str(exc):
                raise
    if results is None:
        raise RuntimeError('No non-emergency network-feasible timing step')
    scale, prices, residual, emergency = results
    stock = water['initial'] + np.cumsum(water['inflow'] - water['spill'] -
                                         (water['power'] + scale * change) / water['eta'], axis=0)
    schema, data, _ = grouped_fit_inputs()
    observed = data['observed_prices']
    mask = np.isfinite(observed)
    zone_metrics = {}
    for zone in ('NO1', 'NO2', 'NO3', 'NO4', 'NO5'):
        j = model['zones'].index(zone)
        if mask[:, j].any():
            zone_metrics[zone] = dict(before=float(np.mean(abs(prices0[mask[:,j],j]-observed[mask[:,j],j]))),
                                      after=float(np.mean(abs(prices[mask[:,j],j]-observed[mask[:,j],j]))))
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'trial.npz'
    np.savez_compressed(path, power=water['power'] + scale * change, inventory=stock,
                        prices=prices, original_prices=prices0)
    result = dict(status='seasonal_water_value_timing_sensitivity_not_baseline',
                  network_scale=scale, model_price_signal_only=True,
                  seasonal_rule='31-day modeled-price mean + 30 EUR/MWh times (0.5 - reservoir fullness)',
                  absolute_reservoir_timing_change_twh=float(np.abs(scale*change).sum()/1e6),
                  national_reservoir_generation_twh=float((water['power']+scale*change).sum()/1e6),
                  terminal_stock_error_mwh=float(np.max(abs(stock[-1]-water['terminal']))),
                  maximum_hourly_stock_violation_mwh=float(max(0., np.max(np.maximum(-stock,stock-water['capacity'])))),
                  maximum_primal_residual_mw=residual, emergency_mwh=emergency,
                  before_mae=float(np.mean(abs(prices0[mask]-observed[mask]))),
                  after_mae=float(np.mean(abs(prices[mask]-observed[mask]))),
                  nordic_zones=zone_metrics, curves=curves,
                  seconds=time.perf_counter()-start,
                  source_sha256={'water':sha(ROOT/'data/hydro-observations-2025/nve-updated-model-v5/water.npz'),
                                 'trial':sha(path)},
                  limitations=['Existing national inflow and RoR split unchanged; corrected RoR turbine ceiling is inactive under that split',
                               'Fixed inherited hourly shape within each day; only daily energy shifts',
                               'Retrospective model-only price signal; no forward-market validation or actual hydro bid reconstruction',
                               'National stock pooled by inherited PyPSA units; no river routing or independent RoR inflow'])
    REPORT.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
