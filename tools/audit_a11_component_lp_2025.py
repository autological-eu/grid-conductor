"""Independently replay all saved primal and dual conditions for the A11 candidate."""
from __future__ import annotations

import json

import numpy as np

from baselines.compact.evaluation import a11_component_lp, saved_annual
from baselines.compact.source import ROOT, digest
from tools.price_mechanism_2025 import dual_replay

SUMMARY = ROOT / 'research/data/a11-component-lp-2025.json'
WITNESS = ROOT / 'data/bidding-zone-network-2025/a11-component-lp-v1/annual.npz'
OUT = ROOT / 'research/data/a11-component-lp-audit-2025.json'


def audit():
    summary = json.loads(SUMMARY.read_text())
    if digest(WITNESS) != summary['annual_witness_sha256']:
        raise ValueError('A11 annual witness hash changed')
    model = a11_component_lp()
    costs, _ = saved_annual()
    with np.load(WITNESS) as archive:
        values = archive['values']
        duals = archive['row_duals']
        objectives = archive['objectives']
        if not archive['optimal'].all() or not np.array_equal(archive['hours'], np.arange(8760)):
            raise ValueError('Lost complete optimal hourly chronology')
    ng, nl, nz = (model[k] for k in ('ng', 'nl', 'nz'))
    maximum = dict(primal_residual_mw=0., objective_residual_eur=0.)
    for start in range(0, 8760, 168):
        stop = min(start + 168, 8760)
        sl = slice(start, stop)
        case = {key: model[key] for key in ('A', 'ng', 'nl', 'nz', 'islands')}
        case.update(cost=costs[sl], availability=model['availability'][sl],
                    link_min=model['link_min'][sl], link_max=model['link_max'][sl],
                    load=model['load'][sl], island_rhs=model['island_rhs'][sl],
                    ratings=model['ratings'][sl])
        full_cost = np.c_[costs[sl], np.zeros((stop - start, nl + nz))]
        reduced = full_cost - (model['A'].T @ duals[sl].T).T
        replay = dual_replay(case, values[sl], duals[sl], reduced,
                             objectives[sl], model['flow'][sl])
        for key, result in replay.items():
            maximum[key] = max(maximum.get(key, 0.), result)
        actual = (model['A'] @ values[sl].T).T
        lower = np.c_[model['load'][sl], model['island_rhs'][sl],
                      -model['ratings'][sl] - model['flow'][sl]]
        upper = np.c_[model['load'][sl], model['island_rhs'][sl],
                      model['ratings'][sl] - model['flow'][sl]]
        maximum['primal_residual_mw'] = max(maximum['primal_residual_mw'],
            float(np.maximum(lower - actual, 0).max()),
            float(np.maximum(actual - upper, 0).max()))
        maximum['objective_residual_eur'] = max(maximum['objective_residual_eur'],
            float(abs((values[sl, :ng] * costs[sl]).sum(axis=1) - objectives[sl]).max()))
    if maximum['primal_residual_mw'] >= 1e-4 or maximum['objective_residual_eur'] >= .05:
        raise ValueError('Annual independent primal/objective replay failed')
    result = dict(status='full_year_primal_dual_replay_passed', hours=8760,
                  annual_witness_sha256=digest(WITNESS), numerical=maximum)
    OUT.write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
