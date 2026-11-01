"""Reproduce two bounded-day storage checks on the retained 2025 joint LP."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baselines.compact.evaluation import ANNUAL, physical_lp, saved_annual
from baselines.compact.source import digest
from baselines.compact.storage import Battery, clear_window, rolling_days

model = physical_lp()
costs, annual = saved_annual()
zone = list(map(str, model['zones'])).index('DE-LU')
battery = Battery('DE-LU', 500, 2000, .95, .95, 1000, 1000)
rows = []
for start in (0, 7416):
    started = time.perf_counter()
    reference = clear_window(model, costs, start, 24)
    base_seconds = time.perf_counter() - started
    objective_gap = reference['objective_eur'] - float(annual['objectives'][start:start+24].sum())
    price_gap = float(np.max(np.abs(reference['zonal_prices'] -
                                     annual['row_duals'][start:start+24, :model['nz']])))
    if abs(objective_gap) > .01 or price_gap > 1e-5:
        raise ValueError('No-storage coupled-window solve differs from accepted hourly LP')
    started = time.perf_counter()
    trial = clear_window(model, costs, start, 24, (battery,))
    battery_seconds = time.perf_counter() - started
    charge, discharge, stock = trial['storage'][0].T
    stock_replay = battery.initial_mwh + np.cumsum(
        battery.charge_efficiency * charge - discharge / battery.discharge_efficiency)
    if np.max(np.abs(stock_replay - stock)) > 1e-6 or abs(stock[-1] - battery.terminal_mwh) > 1e-6:
        raise ValueError('Battery inventory replay failed')
    rows.append(dict(start_hour=start, date_utc=str(np.datetime64('2025-01-01') +
                                                   np.timedelta64(start, 'h')),
                     no_storage_objective_gap_eur=objective_gap,
                     no_storage_max_price_gap_eur_mwh=price_gap,
                     no_storage_solve_seconds=base_seconds,
                     battery_solve_seconds=battery_seconds,
                     modeled_offer_cost_reduction_eur=reference['objective_eur'] - trial['objective_eur'],
                     battery_charge_mwh=float(charge.sum()),
                     battery_discharge_mwh=float(discharge.sum()),
                     end_stock_mwh=float(stock[-1]),
                     min_stock_mwh=float(stock.min()), max_stock_mwh=float(stock.max()),
                     base_de_price_min_eur_mwh=float(reference['zonal_prices'][:, zone].min()),
                     base_de_price_max_eur_mwh=float(reference['zonal_prices'][:, zone].max()),
                     maximum_primal_residual=trial['maximum_primal_residual']))
started = time.perf_counter()
rolling = rolling_days(model, costs, 7416, 2, battery, lookahead_hours=48)
rolling_seconds = time.perf_counter() - started
rolling_stock = rolling['storage']
rolling_record = dict(start_hour=7416, executed_hours=48,
                      lookahead_hours=48, solve_seconds=rolling_seconds,
                      stock_after_first_day_mwh=float(rolling_stock[23, 2]),
                      terminal_stock_mwh=float(rolling_stock[-1, 2]),
                      charge_mwh=float(rolling_stock[:, 0].sum()),
                      discharge_mwh=float(rolling_stock[:, 1].sum()),
                      modeled_offer_cost_reduction_eur=float(
                          annual['objectives'][7416:7464].sum() - rolling['objective_eur']),
                      maximum_primal_residual=rolling['maximum_primal_residual'])
if abs(rolling_record['stock_after_first_day_mwh'] - battery.initial_mwh) < 1e-6:
    raise ValueError('Rolling trial did not exercise across-day stock carry')
record = dict(status='bounded_daily_storage_formulation_diagnostic_not_annual_investment_value',
              baseline='mixed_curve_fitting',
              audit_script_sha256=digest(Path(__file__)),
              storage_model_sha256=digest(ROOT / 'baselines/compact/storage.py'),
              baseline_witness_sha256=digest(ANNUAL / 'annual.npz'),
              bid_cost_sha256=digest(ANNUAL / 'costs.npz'),
              battery=dict(zone=battery.zone, power_mw=battery.power_mw,
                           energy_mwh=battery.energy_mwh,
                           charge_efficiency=battery.charge_efficiency,
                           discharge_efficiency=battery.discharge_efficiency,
                           initial_mwh=battery.initial_mwh,
                           terminal_mwh=battery.terminal_mwh,
                           throughput_eur_mwh=battery.throughput_eur_mwh),
              days=rows, rolling_two_day_trial=rolling_record)
path = ROOT / 'research/data/compact-storage-day-2025.json'
path.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
print(json.dumps(dict(days=rows, rolling_two_day_trial=rolling_record), indent=2))
