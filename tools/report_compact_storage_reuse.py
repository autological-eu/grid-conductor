"""Audit and plot annual reusable-HiGHS storage speed without a new solve."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baselines.compact.evaluation import physical_lp
from baselines.compact.source import digest

old_dir = ROOT/'data/bidding-zone-network-2025/compact-storage-annual-v1'
new_dir = ROOT/'data/bidding-zone-network-2025/compact-storage-annual-reuse-v2'
old_path, new_path = old_dir/'summary.json', new_dir/'summary.json'
old = json.loads(old_path.read_text())
new = json.loads(new_path.read_text())
if (old['status'] != 'full_year_rolling_storage_trial_not_investment_validation' or
        new['status'] != 'full_year_reusable_storage_trial_passed_numerical_gates' or
        old['manifest']['baseline_witness_sha256'] != new['manifest']['baseline_witness_sha256'] or
        old['manifest']['battery'] != new['manifest']['battery'] or
        len(old['day_checkpoint_sha256']) != 365 or len(new['day_checkpoint_sha256']) != 365):
    raise ValueError('Annual storage trials are not a matched pair')
zones = list(map(str, physical_lp()['zones']))
z = zones.index('DE-LU')
zone_counts = np.zeros(len(zones), dtype=int)
old_times, new_times, day_end_gaps = [], [], []
objective_delta, de_price_cells, de_price_max = 0., 0, 0.
all_price_cells = 0
for day in range(365):
    p, q = old_dir/f'day-{day:03d}.npz', new_dir/f'day-{day:03d}.npz'
    if digest(p) != old['day_checkpoint_sha256'][day] or digest(q) != new['day_checkpoint_sha256'][day]:
        raise ValueError(f'Day {day}: checkpoint hash changed')
    with np.load(p) as a, np.load(q) as b:
        if int(a['start']) != 24*day or int(b['start']) != 24*day:
            raise ValueError('Saved chronology changed')
        old_times.append(float(a['solve_seconds']))
        new_times.append(float(b['solve_seconds']))
        objective_delta += float(b['objective_eur']-a['objective_eur'])
        day_end_gaps.append(float(b['storage'][-1, 2]-a['storage'][-1, 2]))
        delta = b['prices']-a['prices']
        mask = np.abs(delta) > .01
        all_price_cells += int(mask.sum())
        zone_counts += mask.sum(axis=0)
        de_price_cells += int(mask[:, z].sum())
        de_price_max = max(de_price_max, float(np.max(np.abs(delta[:, z]))))
if abs(objective_delta) > .01 or abs(new['charge_mwh']-old['charge_mwh']) > 1e-5 or abs(new['discharge_mwh']-old['discharge_mwh']) > 1e-5:
    raise ValueError('Annual objective or battery energy differs materially')
if new['maximum_primal_residual'] > 1e-4 or new['emergency_mwh'] != 0 or abs(new['terminal_stock_mwh']-1000) > 1e-6:
    raise ValueError('Fast annual physical gate failed')
receipt = dict(status='annual_reusable_storage_objective_and_energy_parity_with_dual_degeneracy',
               old_summary_sha256=digest(old_path), new_summary_sha256=digest(new_path),
               baseline_witness_sha256=old['manifest']['baseline_witness_sha256'],
               reusable_model_sha256=new['manifest']['reusable_model_sha256'],
               days=365, hours=8760,
               old_wall_seconds=old['wall_seconds'], new_wall_seconds=new['wall_seconds'],
               old_solve_seconds=old['total_solver_seconds'],
               new_template_assembly_seconds=new['template_assembly_seconds'],
               new_update_seconds=new['update_seconds'],
               new_solve_seconds=new['solver_seconds'],
               new_update_and_solve_seconds=new['update_and_solver_seconds'],
               wall_speedup=old['wall_seconds']/new['wall_seconds'],
               solve_speedup=old['total_solver_seconds']/new['update_and_solver_seconds'],
               annual_objective_delta_eur=objective_delta,
               old_modeled_offer_cost_reduction_meur=old['modeled_offer_cost_reduction_meur'],
               new_modeled_offer_cost_reduction_meur=new['modeled_offer_cost_reduction_meur'],
               battery_charge_difference_mwh=new['charge_mwh']-old['charge_mwh'],
               battery_discharge_difference_mwh=new['discharge_mwh']-old['discharge_mwh'],
               modeled_energy_revenue_difference_eur=(new['modeled_battery_energy_revenue_meur']-
                                                      old['modeled_battery_energy_revenue_meur'])*1e6,
               maximum_fast_primal_residual=new['maximum_primal_residual'],
               maximum_numerical_carry_clamp_mwh=new['maximum_numerical_carry_clamp_mwh'],
               total_numerical_carry_clamp_mwh=new['total_numerical_carry_clamp_mwh'],
               days_with_different_end_stock=sum(abs(x)>.01 for x in day_end_gaps),
               maximum_day_end_stock_gap_mwh=max(map(abs, day_end_gaps)),
               changed_de_lu_price_cells=de_price_cells,
               maximum_de_lu_price_gap_eur_mwh=de_price_max,
               changed_all_zone_price_cells=all_price_cells,
               changed_fr_cor_price_cells=int(zone_counts[zones.index('FR-COR')]))
out = ROOT/'research/data/compact-storage-reuse-2025.json'
out.write_text(json.dumps(receipt, indent=2, allow_nan=False)+'\n')
fig, ax = plt.subplots(figsize=(10, 4.6))
x = np.arange(365)
ax.plot(x+1, old_times, color='#69748a', alpha=.65, lw=1, label='Fresh LP per day')
ax.plot(x+1, new_times, color='#087e78', alpha=.9, lw=1, label='Reusable HiGHS template')
ax.set(xlabel='2025 day', ylabel='Update + solve time (seconds)',
       title='Same 48-hour rolling storage model · daily calculation time')
ax.grid(alpha=.2)
ax.legend()
fig.text(.5, .01, 'Annual objectives and battery energy match; some equally optimal stock paths and dual prices differ.',
         ha='center', fontsize=8, color='#555')
fig.tight_layout(rect=[0,.03,1,1])
figure=ROOT/'research/figures/compact-storage-speed-2025.png'
fig.savefig(figure,dpi=180)
plt.close(fig)
print(json.dumps(receipt, indent=2))
