"""Summarize the saved 2025 rolling-battery result without another solve."""
from __future__ import annotations

import calendar
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baselines.compact.evaluation import ANNUAL, saved_annual
from baselines.compact.source import digest

folder = ROOT / 'data/bidding-zone-network-2025/compact-storage-annual-v1'
summary_path = folder / 'summary.json'
summary = json.loads(summary_path.read_text())
if summary['status'] != 'full_year_rolling_storage_trial_not_investment_validation':
    raise ValueError('Annual storage trial did not finish')
_, baseline = saved_annual()
if digest(ANNUAL / 'annual.npz') != summary['manifest']['baseline_witness_sha256']:
    raise ValueError('Retained baseline changed')
months = [dict(month=calendar.month_abbr[i], modeled_offer_cost_reduction_meur=0.0,
               charge_gwh=0.0, discharge_gwh=0.0, days=0) for i in range(1, 13)]
for day, expected in enumerate(summary['day_checkpoint_sha256']):
    path = folder / f'day-{day:03d}.npz'
    if digest(path) != expected:
        raise ValueError(f'Day {day}: checkpoint hash changed')
    with np.load(path) as archive:
        saved = {key: archive[key] for key in ('start', 'objective_eur', 'storage')}
    if int(saved['start']) != day * 24:
        raise ValueError('Checkpoint chronology changed')
    month = int(str(np.datetime64('2025-01-01') + np.timedelta64(day, 'D'))[5:7]) - 1
    row = months[month]
    row['modeled_offer_cost_reduction_meur'] += float(
        (baseline['objectives'][day*24:(day+1)*24].sum() - saved['objective_eur']) / 1e6)
    row['charge_gwh'] += float(saved['storage'][:, 0].sum() / 1000)
    row['discharge_gwh'] += float(saved['storage'][:, 1].sum() / 1000)
    row['days'] += 1
if abs(sum(m['modeled_offer_cost_reduction_meur'] for m in months)
       - summary['modeled_offer_cost_reduction_meur']) > 1e-8:
    raise ValueError('Monthly benefit does not sum to saved annual result')
receipt = dict(status=summary['status'], year=2025,
               source_summary_sha256=digest(summary_path),
               baseline_witness_sha256=summary['manifest']['baseline_witness_sha256'],
               bid_cost_sha256=summary['manifest']['bid_cost_sha256'],
               storage_model_sha256=summary['manifest']['storage_model_sha256'],
               annual_runner_sha256=summary['manifest']['runner_sha256'],
               battery=summary['manifest']['battery'],
               lookahead_hours=summary['manifest']['lookahead_hours'],
               terminal_policy=summary['manifest']['terminal_policy'],
               days=summary['days'], hours=summary['hours'],
               optimal_hours=summary['optimal_hours'],
               emergency_mwh=summary['emergency_mwh'],
               maximum_primal_residual=summary['maximum_primal_residual'],
               maximum_stock_replay_error_mwh=summary['maximum_stock_replay_error_mwh'],
               terminal_stock_mwh=summary['terminal_stock_mwh'],
               modeled_offer_cost_reduction_meur=summary['modeled_offer_cost_reduction_meur'],
               modeled_battery_energy_revenue_meur=summary['modeled_battery_energy_revenue_meur'],
               mean_absolute_zonal_price_change_eur_mwh=summary['mean_absolute_zonal_price_change_eur_mwh'],
               total_solver_seconds=summary['total_solver_seconds'],
               wall_seconds=summary['wall_seconds'], monthly=months)
out = ROOT / 'research/data/compact-storage-annual-2025.json'
out.write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')

fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
x = np.arange(12)
axes[0].bar(x, [m['modeled_offer_cost_reduction_meur'] for m in months], color='#167b79')
axes[0].set(ylabel='Modeled offer-cost reduction (M€)', title='2025 DE-LU battery trial · 500 MW / 2,000 MWh')
axes[0].grid(axis='y', alpha=.2)
axes[1].bar(x-.2, [m['charge_gwh'] for m in months], width=.4, label='Charging', color='#5275a3')
axes[1].bar(x+.2, [m['discharge_gwh'] for m in months], width=.4, label='Discharging', color='#dc8c40')
axes[1].set(ylabel='Battery energy (GWh)', xticks=x,
            xticklabels=[m['month'] for m in months])
axes[1].legend()
axes[1].grid(axis='y', alpha=.2)
fig.text(.5, .015, '48-hour retrospective look-ahead; 24-hour execution; stock carried across days. No CAPEX or independent investment validation.',
         ha='center', fontsize=8, color='#555')
fig.tight_layout(rect=[0, .035, 1, 1])
figure = ROOT / 'research/figures/compact-storage-annual-2025.png'
figure.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(figure, dpi=180)
plt.close(fig)
print(json.dumps(dict(receipt=str(out), figure=str(figure),
                      annual_gain_meur=receipt['modeled_offer_cost_reduction_meur']), indent=2))
