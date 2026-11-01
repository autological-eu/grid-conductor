"""Resumable annual trial using a reusable 48-hour HiGHS storage template."""
from __future__ import annotations

from dataclasses import asdict
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
from baselines.compact.source import digest
from baselines.compact.storage_reuse import ReusableBatteryWindow
from tools.run_compact_storage_annual import BATTERY, HOURS, LOOKAHEAD, read_day

OUT = ROOT / 'data/bidding-zone-network-2025/compact-storage-annual-reuse-v2'
REFERENCE = ROOT / 'data/bidding-zone-network-2025/compact-storage-annual-v1'
DAYS = 365


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'job.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        reference = json.loads((REFERENCE / 'summary.json').read_text())
        manifest = dict(status='fixed_horizon_storage_speed_candidate', year=2025,
                        baseline_witness_sha256=digest(ANNUAL / 'annual.npz'),
                        bid_cost_sha256=digest(ANNUAL / 'costs.npz'),
                        original_annual_summary_sha256=digest(REFERENCE / 'summary.json'),
                        reusable_model_sha256=digest(ROOT / 'baselines/compact/storage_reuse.py'),
                        runner_sha256=digest(Path(__file__)),
                        battery=asdict(BATTERY), lookahead_hours=LOOKAHEAD)
        if manifest['baseline_witness_sha256'] != reference['manifest']['baseline_witness_sha256']:
            raise ValueError('Reference baseline changed')
        manifest_file = OUT / 'manifest.json'
        if manifest_file.exists():
            if json.loads(manifest_file.read_text()) != manifest:
                raise ValueError('Existing fast-storage checkpoints use different sources or code')
        else:
            manifest_file.write_text(json.dumps(manifest, indent=2) + '\n')
        model = physical_lp()
        costs, baseline = saved_annual()
        regular = ReusableBatteryWindow(model, costs, BATTERY, LOOKAHEAD)
        last = ReusableBatteryWindow(model, costs, BATTERY, 24)
        current = BATTERY.initial_mwh
        carry_clamp_total = 0.0
        carry_clamp_max = 0.0
        total_cost, total_revenue, charge, discharge = 0., 0., 0., 0.
        max_residual, max_stock_error = 0., 0.
        max_old_day_end_gap, max_de_price_gap, max_all_price_gap = 0., 0., 0.
        all_price_cells_over_cent = 0
        runtime, updates, solves = 0., 0., 0.
        hashes = []
        zone = list(map(str, model['zones'])).index(BATTERY.zone)
        begun = time.perf_counter()
        for day in range(DAYS):
            clipped = float(np.clip(current, 0., BATTERY.energy_mwh))
            correction = abs(clipped-current)
            if correction > 1e-6:
                raise ValueError(f'Day {day}: carried stock outside physical bounds')
            carry_clamp_total += correction
            carry_clamp_max = max(carry_clamp_max, correction)
            current = clipped
            path = OUT / f'day-{day:03d}.npz'
            if not path.exists():
                template = regular if day < DAYS-1 else last
                result = template.clear(day*24, current)
                executed = result['storage'][:24]
                dispatch = result['values'][:24]
                cost = float(np.sum(dispatch[:, :model['ng']] * costs[day*24:(day+1)*24]))
                cost += BATTERY.throughput_eur_mwh * float(executed[:, :2].sum())
                temp = OUT / f'day-{day:03d}.partial.npz'
                np.savez_compressed(temp, start=day*24, initial_mwh=current,
                                    values=dispatch, prices=result['zonal_prices'][:24],
                                    storage=executed, objective_eur=cost,
                                    maximum_primal_residual=result['maximum_primal_residual'],
                                    update_seconds=result['update_seconds'],
                                    solver_seconds=result['solve_seconds'],
                                    solve_seconds=result['update_seconds']+result['solve_seconds'])
                os.replace(temp, path)
            row = read_day(path, day, current, model, costs)
            energy = row['storage']
            replay = current + np.cumsum(BATTERY.charge_efficiency*energy[:, 0]
                                         - energy[:, 1]/BATTERY.discharge_efficiency)
            stock_error = float(np.max(np.abs(replay-energy[:, 2])))
            if stock_error > 1e-6 or np.any(np.minimum(energy[:, 0], energy[:, 1]) > 1e-5):
                raise ValueError(f'Day {day}: stock or simultaneous cycling failed')
            current = float(energy[-1, 2])
            total_cost += float(row['objective_eur'])
            total_revenue += float(np.sum(row['prices'][:, zone]
                                          * (energy[:, 1]-energy[:, 0])))
            charge += float(energy[:, 0].sum())
            discharge += float(energy[:, 1].sum())
            max_residual = max(max_residual, float(row['maximum_primal_residual']))
            max_stock_error = max(max_stock_error, stock_error)
            updates += float(row['update_seconds'])
            solves += float(row['solver_seconds'])
            runtime += float(row['solve_seconds'])
            hashes.append(digest(path))
            with np.load(REFERENCE / f'day-{day:03d}.npz') as old:
                max_old_day_end_gap = max(max_old_day_end_gap,
                                          abs(current-float(old['storage'][-1, 2])))
                difference = row['prices'] - old['prices']
                max_de_price_gap = max(max_de_price_gap,
                                       float(np.max(np.abs(difference[:, zone]))))
                max_all_price_gap = max(max_all_price_gap,
                                        float(np.max(np.abs(difference))))
                all_price_cells_over_cent += int(np.sum(np.abs(difference) > .01))
            if (day+1) % 30 == 0 or day == 0:
                print(f'day {day+1}/{DAYS}, stock {current:.1f} MWh, '
                      f'elapsed {time.perf_counter()-begun:.1f} s', flush=True)
        if abs(current-BATTERY.terminal_mwh) > 1e-6:
            raise ValueError('Annual terminal stock failed')
        summary = dict(status='full_year_reusable_storage_trial_passed_numerical_gates',
                       manifest=manifest, day_checkpoint_sha256=hashes,
                       hours=HOURS, optimal_hours=HOURS, emergency_mwh=0.,
                       maximum_primal_residual=max_residual,
                       maximum_stock_replay_error_mwh=max_stock_error,
                       total_numerical_carry_clamp_mwh=carry_clamp_total,
                       maximum_numerical_carry_clamp_mwh=carry_clamp_max,
                       terminal_stock_mwh=current,
                       charge_mwh=charge, discharge_mwh=discharge,
                       modeled_offer_cost_reduction_meur=float(
                           (baseline['objectives'].sum()-total_cost)/1e6),
                       modeled_battery_energy_revenue_meur=total_revenue/1e6,
                       old_modeled_offer_cost_reduction_meur=reference['modeled_offer_cost_reduction_meur'],
                       old_modeled_battery_energy_revenue_meur=reference['modeled_battery_energy_revenue_meur'],
                       maximum_old_day_end_stock_gap_mwh=max_old_day_end_gap,
                       maximum_de_price_gap_eur_mwh=max_de_price_gap,
                       maximum_all_zone_price_gap_eur_mwh=max_all_price_gap,
                       all_zone_price_cells_over_cent=all_price_cells_over_cent,
                       template_assembly_seconds=regular.assembly_seconds+last.assembly_seconds,
                       update_seconds=updates, solver_seconds=solves,
                       update_and_solver_seconds=runtime,
                       wall_seconds=time.perf_counter()-begun)
        (OUT/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
        print(json.dumps({key:summary[key] for key in
                          ('modeled_offer_cost_reduction_meur','modeled_battery_energy_revenue_meur',
                           'maximum_old_day_end_stock_gap_mwh','maximum_de_price_gap_eur_mwh',
                           'maximum_all_zone_price_gap_eur_mwh','update_and_solver_seconds',
                           'wall_seconds')},indent=2), flush=True)


if __name__ == '__main__':
    main()
