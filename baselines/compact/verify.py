"""Read-only equivalence checks for the compact research successor.

Run with the pinned scientific Python: ``python -m baselines.compact.verify``.
Use ``--annual`` to reclear all 8,760 hours (about 30 seconds on this host).
"""
from __future__ import annotations

import argparse
import ast
import json
import tempfile
from pathlib import Path

import numpy as np

from .evaluation import FIT, physical_lp, saved_annual, transferred_costs
from .fit import fit
from .lp import clear_hour, solver
from .network import transport_corridors
from .roots import ObservedPriceMultistartMarket
from .source import grouped_fit_inputs, observed_flow_snapshot


def import_gate():
    files = list(Path(__file__).parent.glob('*.py'))
    active = [path for path in files if path.name != 'verify.py']
    if len(active) > 20:
        raise AssertionError(f'Active project module limit exceeded: {len(active)}')
    for path in active:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                bare = node.module.split('.')[0]
                if bare in {'tools', 'baselines'} or (Path('tools') / f'{bare}.py').exists():
                    raise AssertionError(f'Historical project import in {path}: {node.module}')
    return len(active)


def market_inputs():
    schema, data, matrix = grouped_fit_inputs()
    edges, lower, upper = transport_corridors(schema['zones'], data)
    market = ObservedPriceMultistartMarket(
        schema['zones'], schema['groups'], lower, upper, edges,
        data['capacity'] / 1000, data['source_cost'], data['load'] / 1000,
        observed_prices=data['observed_prices'])
    if matrix.shape[0] != 311 or len(edges) != 95 or market.ng != 326:
        raise AssertionError('Changed physical or transport dimensions')
    return schema, data, market


def verify(annual=False, fit_step=False):
    modules = import_gate()
    schema, data, market = market_inputs()
    model = physical_lp()
    saved_cost, witness = saved_annual()
    calculated_cost = transferred_costs(schema, data, market, model)
    np.testing.assert_array_equal(calculated_cost, saved_cost)
    highs = solver(model, calculated_cost)
    hours = range(8760) if annual else [0, 12, 744, 2160, 4368, 6576, 8759]
    objective_gap = price_gap = residual = generation_gap = 0.0
    for hour in hours:
        values, duals, objective, error = clear_hour(highs, model, calculated_cost, hour)
        objective_gap = max(objective_gap, abs(objective - witness['objectives'][hour]))
        price_gap = max(price_gap, float(abs(duals[:model['nz']] - witness['row_duals'][hour, :model['nz']]).max()))
        generation_gap = max(generation_gap, abs(values[:model['ng']].sum() - witness['values'][hour, :model['ng']].sum()))
        residual = max(residual, error)
    if objective_gap > 0.01 or price_gap > 1e-5 or generation_gap > 1e-4 or residual > 1e-4:
        raise AssertionError('LP equivalence or physical gate failed')
    result = dict(active_modules=modules, lp_hours=len(hours), cost_cells=int(calculated_cost.size),
                  max_objective_gap_eur=objective_gap, max_price_gap_eur_mwh=price_gap,
                  max_total_generation_gap_mw=generation_gap, max_primal_residual_mw=residual)
    if fit_step:
        flow, flow_mask, missing = observed_flow_snapshot(market.edges, schema['zones'])
        with tempfile.TemporaryDirectory() as folder:
            _, _, history = fit(1, 1, 1.0, market, schema, data, flow, flow_mask,
                                missing, Path(folder))
        old = json.loads((FIT / 'month-01/history.json').read_text())
        for step in (0, 1):
            for metric in ('all_price_mae', 'generation_mae_gw', 'mix_share_mae'):
                np.testing.assert_allclose(history[step][metric], old[step][metric], rtol=0, atol=1e-8)
        result['january_fit_steps_replayed'] = 2
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--annual', action='store_true')
    parser.add_argument('--fit-step', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(annual=args.annual, fit_step=args.fit_step), indent=2))
