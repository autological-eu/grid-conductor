"""Run one frozen-bid 8,760-hour LP on the 19-gap A11 network candidate."""
from __future__ import annotations

import fcntl
import json
import time

import numpy as np

from baselines.compact.evaluation import a11_component_lp, saved_annual
from baselines.compact.lp import clear_hour, solver
from baselines.compact.source import ROOT, digest, grouped_fit_inputs

OUT = ROOT / 'data/bidding-zone-network-2025/a11-component-lp-v1'
SUMMARY = ROOT / 'research/data/a11-component-lp-2025.json'
INPUT = ROOT / 'research/data/a11-component-network-2025.json'


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'job.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (OUT / 'annual.npz').exists() or SUMMARY.exists():
            raise FileExistsError('Existing annual A11 component candidate')
        model = a11_component_lp()
        costs, prior = saved_annual()
        schema, data, _ = grouped_fit_inputs()
        highs = solver(model, costs)
        values = np.empty((8760, model['A'].shape[1]))
        duals = np.empty((8760, model['A'].shape[0]))
        objective = np.empty(8760)
        residual = 0.0
        started = time.perf_counter()
        for hour in range(8760):
            values[hour], duals[hour], objective[hour], error = clear_hour(highs, model, costs, hour)
            residual = max(residual, error)
            if objective[hour] > prior['objectives'][hour] + 0.1:
                raise ValueError(f'Relaxed candidate raised optimum at hour {hour}')
        solve_seconds = time.perf_counter() - started
        emergency = float(values[:, :model['ng']][:, model['emergency_mask']].sum())
        if emergency > 1e-6 or residual >= 1e-4:
            raise ValueError('A11 annual physical gate failed')
        observed = data['observed_prices']
        mask = np.isfinite(observed)
        before = prior['row_duals'][:, :model['nz']]
        after = duals[:, :model['nz']]
        zone_scores = []
        for j, zone in enumerate(model['zones']):
            good = mask[:, j]
            if good.any():
                zone_scores.append(dict(zone=zone, hours=int(good.sum()),
                    baseline_price_mae_eur_mwh=float(abs(before[good, j] - observed[good, j]).mean()),
                    candidate_price_mae_eur_mwh=float(abs(after[good, j] - observed[good, j]).mean())))
        np.savez_compressed(OUT / 'annual.npz', values=values, row_duals=duals,
                            objectives=objective, hours=np.arange(8760), optimal=np.ones(8760, bool))
        summary = dict(status='full_year_frozen_bid_A11_component_network_candidate_not_baseline',
            hours=8760, source_network_audit_sha256=digest(INPUT),
            source_costs_sha256=digest(ROOT / 'data/bidding-zone-network-2025/observed-root-fast-joint-lp-v1/costs.npz'),
            annual_witness_sha256=digest(OUT / 'annual.npz'),
            solve_seconds=solve_seconds, maximum_primal_residual_mw=residual,
            emergency_mwh=emergency,
            baseline_price_mae_eur_mwh=float(abs(before[mask] - observed[mask]).mean()),
            candidate_price_mae_eur_mwh=float(abs(after[mask] - observed[mask]).mean()),
            objective_reduction_eur=float(prior['objectives'].sum() - objective.sum()),
            zonal_prices=zone_scores,
            limitations=['Frozen bids from accepted 2025 same-month fit; no bid recalibration',
                         'A11-driven component bounds are dated effective candidates, not certified asset ratings',
                         'HVDC uplift can proxy a missing parallel circuit at inherited endpoints',
                         'AC PTDF topology/impedance and hydro schedule unchanged',
                         'Source A11 physical flow and A09 commercial schedule are not LP clearing constraints',
                         'No scenario-response or forward validation; accepted baseline unchanged'])
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps(summary, indent=2) + '\n')
        return summary


if __name__ == '__main__':
    result = run()
    print(json.dumps({key: result[key] for key in ('hours', 'solve_seconds',
        'maximum_primal_residual_mw', 'emergency_mwh',
        'baseline_price_mae_eur_mwh', 'candidate_price_mae_eur_mwh')}, indent=2))
