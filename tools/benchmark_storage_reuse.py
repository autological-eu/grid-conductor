"""Compare fresh SciPy/HiGHS and reusable HiGHS on saved 2025 storage windows."""
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
from baselines.compact.storage import Battery, clear_window
from baselines.compact.storage_reuse import ReusableBatteryWindow

old_folder = ROOT / 'data/bidding-zone-network-2025/compact-storage-annual-v1'
old_summary = json.loads((old_folder / 'summary.json').read_text())
if old_summary['status'] != 'full_year_rolling_storage_trial_not_investment_validation':
    raise ValueError('Old annual reference is incomplete')
if digest(ANNUAL / 'annual.npz') != old_summary['manifest']['baseline_witness_sha256']:
    raise ValueError('Accepted baseline changed')
model = physical_lp()
costs, _ = saved_annual()
battery = Battery(**old_summary['manifest']['battery'])
starts = [*range(0, 7), *range(309, 316), 364]
templates = {}
rows = []
for day in starts:
    hour, size = 24*day, min(48, 8760-24*day)
    with np.load(old_folder / f'day-{day:03d}.npz') as archive:
        prior_initial = float(archive['initial_mwh'])
        saved_stock = archive['storage'].copy()
        saved_objective = float(archive['objective_eur'])
    if size not in templates:
        templates[size] = ReusableBatteryWindow(model, costs, battery, size)
    beginning = time.perf_counter()
    fresh = clear_window(model, costs, hour, size,
                         (Battery(**dict(old_summary['manifest']['battery'],
                                          initial_mwh=prior_initial)),))
    fresh_seconds = time.perf_counter() - beginning
    reused = templates[size].clear(hour, prior_initial)
    fresh_executed_cost = float(np.sum(fresh['values'][:24, :model['ng']]
                                       * costs[hour:hour+24]))
    fresh_executed_cost += battery.throughput_eur_mwh * float(fresh['storage'][0, :24, :2].sum())
    if abs(fresh_executed_cost - saved_objective) > .01 or np.max(np.abs(
            fresh['storage'][0, :24] - saved_stock)) > 1e-5:
        raise ValueError(f'Day {day}: old saved checkpoint differs from fresh solve')
    row = dict(day=day, window_hours=size, old_seconds=fresh_seconds,
               new_update_seconds=reused['update_seconds'],
               new_solve_seconds=reused['solve_seconds'],
               objective_gap_eur=float(reused['objective_eur']-fresh['objective_eur']),
               max_zonal_price_gap_eur_mwh=float(np.max(np.abs(
                   reused['zonal_prices']-fresh['zonal_prices']))),
               price_cells_over_0_01=int(np.sum(np.abs(
                   reused['zonal_prices']-fresh['zonal_prices']) > .01)),
               executed_max_price_gap_eur_mwh=float(np.max(np.abs(
                   reused['zonal_prices'][:24]-fresh['zonal_prices'][:24]))),
               executed_price_cells_over_0_01=int(np.sum(np.abs(
                   reused['zonal_prices'][:24]-fresh['zonal_prices'][:24]) > .01)),
               executed_max_stock_gap_mwh=float(np.max(np.abs(
                   reused['storage'][:24]-fresh['storage'][0, :24]))),
               executed_max_network_dispatch_gap_mw=float(np.max(np.abs(
                   reused['values'][:24]-fresh['values'][:24]))),
               max_stock_gap_mwh=float(np.max(np.abs(
                   reused['storage']-fresh['storage'][0]))),
               first_day_end_stock_gap_mwh=float(
                   reused['storage'][23, 2]-fresh['storage'][0, 23, 2]),
               max_primal_residual=reused['maximum_primal_residual'])
    if abs(row['objective_gap_eur']) > .01 or row['max_primal_residual'] > 1e-4:
        raise ValueError(f'Day {day}: reusable objective or feasibility failed')
    rows.append(row)
    print(f'day {day}: old {fresh_seconds:.2f}s, new {row["new_update_seconds"]+row["new_solve_seconds"]:.2f}s, '
          f'objective gap {row["objective_gap_eur"]:.7f} €, end stock gap {row["first_day_end_stock_gap_mwh"]:.1f} MWh', flush=True)
result = dict(status='representative_windows_objective_feasibility_parity_with_degenerate_prices_and_stock',
              old_summary_sha256=digest(old_folder / 'summary.json'),
              baseline_witness_sha256=old_summary['manifest']['baseline_witness_sha256'],
              reusable_model_sha256=digest(ROOT / 'baselines/compact/storage_reuse.py'),
              old_model_sha256=digest(ROOT / 'baselines/compact/storage.py'),
              template_assembly_seconds={str(h): t.assembly_seconds for h,t in templates.items()},
              old_total_seconds=sum(r['old_seconds'] for r in rows),
              reused_update_and_solve_seconds=sum(r['new_update_seconds']+r['new_solve_seconds'] for r in rows),
              rows=rows)
out=ROOT/'research/data/compact-storage-reuse-benchmark-2025.json'
out.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
print('TOTAL', result['old_total_seconds'], result['reused_update_and_solve_seconds'])
