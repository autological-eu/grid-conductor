"""Independently replay the two A75 frozen-bid annual LP witnesses."""
from __future__ import annotations

import json

import numpy as np

from baselines.compact.source import ROOT, digest
from tools.price_mechanism_2025 import dual_replay
from tools.run_generation_power_lp_2025 import OUT, SUMMARY, candidate

AUDIT = ROOT / 'research/data/generation-power-lp-audit-2025.json'


def audit():
    summary = json.loads(SUMMARY.read_text())
    outcomes = {}
    for network in ('original', 'a11'):
        model, costs, rows = candidate(network)
        witness = OUT/f'{network}.npz'
        if digest(witness) != summary['outcomes'][network]['witness_sha256']:
            raise ValueError('Annual witness hash changed')
        with np.load(witness) as archive:
            x = archive['values']; y = archive['row_duals']; objective = archive['objectives']
            if not archive['optimal'].all() or not np.array_equal(archive['hours'], np.arange(8760)):
                raise ValueError('Incomplete 2025 chronology')
        ng, nl, nz = (model[k] for k in ('ng', 'nl', 'nz'))
        if x.shape != (8760, model['A'].shape[1]) or y.shape != (8760, model['A'].shape[0]):
            raise ValueError('Witness/model dimensions changed')
        maximum = dict(primal_residual_mw=0., objective_residual_eur=0.)
        for start in range(0, 8760, 168):
            stop = min(start + 168, 8760); sl = slice(start, stop)
            rating = model['ratings'][sl] if model['ratings'].ndim == 2 else model['ratings']
            case = {key: model[key] for key in ('A', 'ng', 'nl', 'nz', 'islands')}
            case.update(cost=costs[sl], availability=model['availability'][sl],
                        link_min=model['link_min'][sl], link_max=model['link_max'][sl],
                        load=model['load'][sl], island_rhs=model['island_rhs'][sl],
                        ratings=rating)
            full_cost = np.c_[costs[sl], np.zeros((stop-start, nl+nz))]
            reduced = full_cost - (model['A'].T@y[sl].T).T
            replay = dual_replay(case, x[sl], y[sl], reduced, objective[sl], model['flow'][sl])
            for key, value in replay.items():
                maximum[key] = max(maximum.get(key, 0.), value)
            actual = (model['A']@x[sl].T).T
            low = np.c_[model['load'][sl], model['island_rhs'][sl], -rating-model['flow'][sl]]
            high = np.c_[model['load'][sl], model['island_rhs'][sl], rating-model['flow'][sl]]
            maximum['primal_residual_mw'] = max(maximum['primal_residual_mw'],
                float(np.maximum(low-actual, 0).max()), float(np.maximum(actual-high, 0).max()))
            maximum['objective_residual_eur'] = max(maximum['objective_residual_eur'],
                float(abs((x[sl, :ng]*costs[sl]).sum(axis=1)-objective[sl]).max()))
        if maximum['primal_residual_mw'] >= 1e-4 or maximum['objective_residual_eur'] >= .05:
            raise ValueError('Failed full-year primal/objective replay')
        outcomes[network] = dict(hours=8760, new_offer_columns=len(rows),
                                 witness_sha256=digest(witness), numerical=maximum)
    result = dict(status='both_full_year_primal_dual_replays_passed', outcomes=outcomes)
    AUDIT.write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
