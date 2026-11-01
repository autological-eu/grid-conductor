"""Resumable 2025 rolling battery trial on the retained European joint LP.

Run with the pinned scientific Python. Daily arrays are ignored research
checkpoints; only the final compact summary is suitable for tracked evidence.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import fcntl
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baselines.compact.evaluation import ANNUAL, physical_lp, saved_annual
from baselines.compact.lp import ratings_at
from baselines.compact.source import digest
from baselines.compact.storage import Battery, rolling_days

OUT = ROOT / 'data/bidding-zone-network-2025/compact-storage-annual-v1'
BATTERY = Battery('DE-LU', 500, 2000, .95, .95, 1000, 1000)
DAYS = 365
HOURS = 8760
LOOKAHEAD = 48


def read_day(path: Path, day: int, initial: float, model, costs):
    with np.load(path) as archive:
        row = {key: archive[key] for key in archive.files}
    if (int(row['start']) != day * 24 or len(row['storage']) != 24
            or abs(float(row['initial_mwh']) - initial) > 1e-6
            or not np.isfinite(row['values']).all()
            or not np.isfinite(row['prices']).all()
            or not np.isfinite(row['storage']).all()
            or float(row['maximum_primal_residual']) > 1e-4):
        raise ValueError(f'Day {day}: invalid or stale checkpoint')
    ng, nl, nz = (model[key] for key in ('ng', 'nl', 'nz'))
    if row['values'].shape != (24, model['A'].shape[1]) or row['prices'].shape != (24, nz):
        raise ValueError(f'Day {day}: wrong checkpoint dimensions')
    computed = float(np.sum(row['values'][:, :ng] * costs[day*24:(day+1)*24]))
    computed += BATTERY.throughput_eur_mwh * float(row['storage'][:, :2].sum())
    if abs(computed - float(row['objective_eur'])) > .01:
        raise ValueError(f'Day {day}: saved objective does not replay')
    actual = (model['A'] @ row['values'].T).T
    z = list(map(str, model['zones'])).index(BATTERY.zone)
    actual[:, z] += -row['storage'][:, 0] + row['storage'][:, 1]
    for t in range(24):
        h = day * 24 + t
        values = row['values'][t]
        lower = np.r_[model['load'][h], model['island_rhs'][h],
                      -ratings_at(model, h) - model['flow'][h]]
        upper = np.r_[model['load'][h], model['island_rhs'][h],
                      ratings_at(model, h) - model['flow'][h]]
        if (np.max(np.maximum(lower - actual[t], actual[t] - upper)) > 1e-4
                or np.max(np.maximum(-values[:ng], values[:ng] - model['availability'][h])) > 1e-4
                or np.max(np.maximum(model['link_min'][h] - values[ng:ng+nl],
                                     values[ng:ng+nl] - model['link_max'][h])) > 1e-4
                or np.sum(values[:ng][model['emergency_mask']]) > 1e-6):
            raise ValueError(f'Day {day}, hour {h}: saved network feasibility failed')
    return row


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'job.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = dict(baseline='mixed_curve_fitting', year=2025,
                        baseline_witness_sha256=digest(ANNUAL / 'annual.npz'),
                        bid_cost_sha256=digest(ANNUAL / 'costs.npz'),
                        storage_model_sha256=digest(ROOT / 'baselines/compact/storage.py'),
                        runner_sha256=digest(Path(__file__)),
                        battery=asdict(BATTERY), lookahead_hours=LOOKAHEAD,
                        executed_hours_per_step=24, terminal_policy='target declared MWh at each look-ahead boundary')
        manifest_file = OUT / 'manifest.json'
        if manifest_file.exists():
            if json.loads(manifest_file.read_text()) != manifest:
                raise ValueError('Existing storage checkpoints have different source/model/asset assumptions')
        else:
            manifest_file.write_text(json.dumps(manifest, indent=2) + '\n')
        model = physical_lp()
        costs, baseline = saved_annual()
        if model['availability'].shape[0] != HOURS or len(baseline['objectives']) != HOURS:
            raise ValueError('2025 chronology changed')
        current = BATTERY.initial_mwh
        objective, revenue, charge, discharge, runtime = 0.0, 0.0, 0.0, 0.0, 0.0
        max_residual, max_stock_error = 0.0, 0.0
        price_abs_change, price_changed = 0.0, 0
        checkpoint_hashes = []
        z = list(map(str, model['zones'])).index(BATTERY.zone)
        started = time.perf_counter()
        for day in range(DAYS):
            path = OUT / f'day-{day:03d}.npz'
            if not path.exists():
                before = time.perf_counter()
                result = rolling_days(model, costs, 24 * day, 1,
                                      replace(BATTERY, initial_mwh=current),
                                      lookahead_hours=LOOKAHEAD, horizon_end=HOURS)
                elapsed = time.perf_counter() - before
                temp = OUT / f'day-{day:03d}.partial.npz'
                np.savez_compressed(temp, start=day * 24, initial_mwh=current,
                                    values=result['values'], prices=result['zonal_prices'],
                                    storage=result['storage'], objective_eur=result['objective_eur'],
                                    maximum_primal_residual=result['maximum_primal_residual'],
                                    solve_seconds=elapsed)
                os.replace(temp, path)
            row = read_day(path, day, current, model, costs)
            energy = row['storage']
            replay = current + np.cumsum(BATTERY.charge_efficiency * energy[:, 0]
                                         - energy[:, 1] / BATTERY.discharge_efficiency)
            stock_error = float(np.max(np.abs(replay - energy[:, 2])))
            if stock_error > 1e-6 or np.any(np.minimum(energy[:, 0], energy[:, 1]) > 1e-5):
                raise ValueError(f'Day {day}: stock or simultaneous-cycling gate failed')
            current = float(energy[-1, 2])
            objective += float(row['objective_eur'])
            charge += float(energy[:, 0].sum())
            discharge += float(energy[:, 1].sum())
            runtime += float(row['solve_seconds'])
            max_residual = max(max_residual, float(row['maximum_primal_residual']))
            max_stock_error = max(max_stock_error, stock_error)
            revenue += float(np.sum(row['prices'][:, z] * (energy[:, 1] - energy[:, 0])))
            delta = row['prices'] - baseline['row_duals'][day*24:(day+1)*24, :model['nz']]
            price_abs_change += float(np.abs(delta).sum())
            price_changed += int(np.sum(np.abs(delta) > 1e-5))
            checkpoint_hashes.append(digest(path))
            if (day + 1) % 15 == 0 or day == 0:
                print(f'day {day + 1}/{DAYS}, stock {current:.1f} MWh, '
                      f'elapsed {time.perf_counter()-started:.1f} s', flush=True)
        if abs(current - BATTERY.terminal_mwh) > 1e-6:
            raise ValueError('Annual terminal stock failed')
        summary = dict(status='full_year_rolling_storage_trial_not_investment_validation',
                       manifest=manifest, day_checkpoint_sha256=checkpoint_hashes,
                       days=DAYS, hours=HOURS, optimal_hours=HOURS,
                       emergency_mwh=0.0,
                       maximum_primal_residual=max_residual,
                       maximum_stock_replay_error_mwh=max_stock_error,
                       start_stock_mwh=BATTERY.initial_mwh,
                       terminal_stock_mwh=current,
                       charge_mwh=charge, discharge_mwh=discharge,
                       baseline_offer_cost_meur=float(baseline['objectives'].sum()/1e6),
                       scenario_offer_cost_meur=objective/1e6,
                       modeled_offer_cost_reduction_meur=float((baseline['objectives'].sum()-objective)/1e6),
                       modeled_battery_energy_revenue_meur=revenue/1e6,
                       mean_absolute_zonal_price_change_eur_mwh=price_abs_change/(HOURS*model['nz']),
                       changed_zonal_price_cells=price_changed,
                       total_solver_seconds=runtime,
                       wall_seconds=time.perf_counter()-started,
                       limitations=['2025 fitted offers and perfect retrospective 48h model-input look-ahead',
                                    'fixed hydro; no endogenous reservoir response',
                                    'look-ahead terminal target is a policy assumption',
                                    'no storage CAPEX, degradation, outage, ancillary service or independent investment validation'])
        (OUT / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
        print(json.dumps({key: summary[key] for key in
                          ('status', 'modeled_offer_cost_reduction_meur', 'charge_mwh',
                           'discharge_mwh', 'terminal_stock_mwh', 'total_solver_seconds',
                           'wall_seconds')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
