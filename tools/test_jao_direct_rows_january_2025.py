"""January diagnostic: add only exactly zonal JAO rows to the frozen LP.

This is a mapping sensitivity, not a complete or accepted JAO market model.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import highspy
import numpy as np

from baselines.compact.evaluation import physical_lp, saved_annual
from baselines.compact.jao import exact_zone_rows, read_day
from baselines.compact.lp import clear_hour, solver
from baselines.compact.source import ROOT, grouped_fit_inputs

OUT = ROOT / 'data/jao/direct-row-lp-january-2025-v1'


def run():
    if (OUT / 'summary.json').exists():
        raise FileExistsError('Existing JAO direct-row LP diagnostic')
    model = physical_lp()
    costs, baseline = saved_annual()
    schema, data, _ = grouped_fit_inputs()
    highs = solver(model, costs)
    original_rows = model['A'].shape[0]
    prices = np.full((744, model['nz']), np.nan)
    rows_per_hour = np.zeros(744, dtype=int)
    failed = []
    max_residual = 0.0
    emergency_mwh = 0.0
    for day_index in range(31):
        day = date(2025, 1, 1) + timedelta(days=day_index)
        rows, _ = read_day('nordic', day)
        for local_hour in range(24):
            hour = day_index * 24 + local_hour
            timestamp = f'{day}T{local_hour:02d}:00:00Z'
            domain, ram, source_id = exact_zone_rows(rows, timestamp, model['zones'])
            count = len(ram)
            if not count:
                continue
            rows_per_hour[hour] = count
            column_index = domain.indices.astype(np.int32) + model['ng'] + model['nl']
            status = highs.addRows(count, np.full(count, -np.inf), ram, domain.nnz,
                                   domain.indptr.astype(np.int32), column_index,
                                   domain.data.astype(float))
            if status != highspy.HighsStatus.kOk:
                raise RuntimeError(f'Cannot add JAO rows at {timestamp}')
            try:
                values, duals, _, residual = clear_hour(highs, model, costs, hour)
                excess = domain @ values[-model['nz']:] - ram
                if excess.max(initial=0) > 1e-4:
                    raise ValueError(f'JAO direct-row primal residual at {timestamp}')
                prices[hour] = duals[:model['nz']]
                max_residual = max(max_residual, residual, float(excess.max(initial=0)))
                emergency_mwh += float(values[:model['ng']][model['emergency_mask']].sum())
            except RuntimeError as error:
                if 'Infeasible' not in str(error):
                    raise
                failed.append(dict(hour=hour, time=timestamp, jao_source_ids=source_id))
            finally:
                delete = highs.deleteRows(count, np.arange(original_rows, original_rows + count,
                                                           dtype=np.int32))
                if delete != highspy.HighsStatus.kOk:
                    raise RuntimeError('Could not remove JAO diagnostic rows')
                highs.clearSolver()
    covered = np.isfinite(prices).all(axis=1)
    observed = data['observed_prices'][:744]
    prior = baseline['row_duals'][:744, :model['nz']]
    metrics = {}
    for name in ['NO1', 'NO2', 'NO3', 'NO4', 'NO5', 'SE1', 'SE2', 'SE3', 'SE4']:
        index = model['zones'].index(name)
        good = covered & np.isfinite(observed[:, index])
        metrics[name] = dict(hours=int(good.sum()),
            original_mae=float(abs(prior[good, index] - observed[good, index]).mean()) if good.any() else None,
            direct_jao_mae=float(abs(prices[good, index] - observed[good, index]).mean()) if good.any() else None)
    summary = dict(status='partial_JAO_direct_zone_row_sensitivity_not_baseline',
        period='January 2025 UTC', directly_expressible_jao_rows=int(rows_per_hour.sum()),
        hours_with_direct_rows=int((rows_per_hour > 0).sum()),
        feasible_hours=int(covered.sum()), infeasible_hours=failed,
        emergency_mwh=emergency_mwh, maximum_checked_primal_residual_mw=max_residual,
        price_mae_on_feasible_direct_row_hours=metrics,
        limitations=['Filtered Nordic JAO rows are not a complete market domain',
                     'Only source rows with defined PTDFs and no virtual hubs were added',
                     'PTDF reference and physical/market net-position equivalence are not independently certified',
                     'January selected-hour scores are not full-year or out-of-sample scores'])
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / 'prices.npz', prices=prices, rows_per_hour=rows_per_hour)
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
