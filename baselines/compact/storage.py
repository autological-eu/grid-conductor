"""Chronological battery candidate on the unchanged hourly European network LP.

A bounded window is one coupled LP. It is a formulation and runtime diagnostic,
not the accepted annual baseline or a claim about real storage inventories.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import block_diag, coo_matrix, hstack, vstack

from .lp import ratings_at


@dataclass(frozen=True)
class Battery:
    zone: str
    power_mw: float
    energy_mwh: float
    charge_efficiency: float
    discharge_efficiency: float
    initial_mwh: float
    terminal_mwh: float
    throughput_eur_mwh: float = 0.01


def clear_window(model, costs, start: int, hours: int, batteries=()):
    """Clear consecutive hours with zonal battery power and exact stock balances.

    Hourly source rows, PTDF ratings and bid costs are unchanged. The terminal
    stock is declared, not inferred from observed prices or reset implicitly.
    """
    if hours < 1 or start < 0 or start + hours > len(model['availability']):
        raise ValueError('Invalid chronological window')
    ng, nl, nz = (int(model[key]) for key in ('ng', 'nl', 'nz'))
    ni = len(model['islands'])
    A = model['A'].tocsc()
    nr, nc = A.shape
    if nc != ng + nl + nz:
        raise ValueError('Unexpected accepted LP column order')
    zones = list(map(str, model['zones']))
    for battery in batteries:
        if (battery.zone not in zones or battery.power_mw <= 0 or battery.energy_mwh <= 0
                or not 0 < battery.charge_efficiency <= 1
                or not 0 < battery.discharge_efficiency <= 1
                or not 0 <= battery.initial_mwh <= battery.energy_mwh
                or not 0 <= battery.terminal_mwh <= battery.energy_mwh
                or battery.throughput_eur_mwh < 0):
            raise ValueError('Invalid battery declaration')
    count = len(batteries)
    nbase = hours * nc
    nextra = count * hours * 3  # charge, discharge, ending stock per asset/hour
    total = nbase + nextra
    offsets = lambda b, t, component: nbase + (b * hours + t) * 3 + component

    # The original network rows remain block-diagonal. Battery charging is
    # negative local supply; discharge is positive supply in its bidding zone.
    base = block_diag([A] * hours, format='csc')
    rows, cols, vals = [], [], []
    for b, battery in enumerate(batteries):
        z = zones.index(battery.zone)
        for t in range(hours):
            rows.extend([t * nr + z, t * nr + z])
            cols.extend([offsets(b, t, 0) - nbase, offsets(b, t, 1) - nbase])
            vals.extend([-1.0, 1.0])
    network = hstack([base, coo_matrix((vals, (rows, cols)),
                                       shape=(hours * nr, nextra))], format='csr')
    equal_rows = np.concatenate([np.arange(t * nr, t * nr + nz + ni) for t in range(hours)])
    branch_rows = np.concatenate([np.arange(t * nr + nz + ni, (t + 1) * nr)
                                  for t in range(hours)])
    rhs_eq, lower_branch, upper_branch = [], [], []
    cost = np.zeros(total)
    bounds = []
    for t in range(hours):
        h = start + t
        rhs_eq.extend(model['load'][h])
        rhs_eq.extend(model['island_rhs'][h])
        rating = ratings_at(model, h)
        lower_branch.extend(-rating - model['flow'][h])
        upper_branch.extend(rating - model['flow'][h])
        cost[t * nc:t * nc + ng] = costs[h]
        bounds.extend([(0, float(x)) for x in model['availability'][h]])
        bounds.extend((float(lo), float(hi)) for lo, hi in
                      zip(model['link_min'][h], model['link_max'][h], strict=True))
        bounds.extend([(None, None)] * nz)
    stock_rows, stock_cols, stock_vals = [], [], []
    stock_rhs = []
    for b, battery in enumerate(batteries):
        for t in range(hours):
            idx = b * hours + t
            charge, discharge, stock = (offsets(b, t, k) for k in range(3))
            stock_rows.extend([idx] * 3)
            stock_cols.extend([charge, discharge, stock])
            stock_vals.extend([-battery.charge_efficiency,
                               1 / battery.discharge_efficiency, 1.0])
            if t:
                stock_rows.append(idx)
                stock_cols.append(offsets(b, t - 1, 2))
                stock_vals.append(-1.0)
                stock_rhs.append(0.0)
            else:
                stock_rhs.append(battery.initial_mwh)
            cost[charge] = cost[discharge] = battery.throughput_eur_mwh
            bounds.extend([(0, battery.power_mw), (0, battery.power_mw),
                           (battery.terminal_mwh, battery.terminal_mwh)
                           if t == hours - 1 else (0, battery.energy_mwh)])
    stock_matrix = coo_matrix((stock_vals, (stock_rows, stock_cols)),
                              shape=(count * hours, total)).tocsr()
    eq = vstack([network[equal_rows], stock_matrix], format='csr')
    branch = network[branch_rows]
    ub = vstack([branch, -branch], format='csr')
    upper = np.asarray(upper_branch)
    lower = np.asarray(lower_branch)
    result = linprog(cost, A_ub=ub, b_ub=np.r_[upper, -lower],
                     A_eq=eq, b_eq=np.r_[rhs_eq, stock_rhs], bounds=bounds,
                     method='highs', options={'primal_feasibility_tolerance': 1e-8})
    if not result.success:
        raise RuntimeError(f'Window LP failed: {result.message}')
    x = result.x
    residual = max(float(np.abs(eq @ x - np.r_[rhs_eq, stock_rhs]).max(initial=0)),
                   float(np.maximum(ub @ x - np.r_[upper, -lower], 0).max(initial=0)))
    if residual > 1e-4:
        raise ValueError(f'Window primal residual {residual} MW or MWh')
    original = x[:nbase].reshape(hours, nc)
    if np.any(original[:, :ng][:, model['emergency_mask']].sum(axis=1) > 1e-6):
        raise ValueError('Window used emergency supply')
    storage = np.zeros((count, hours, 3))
    for b in range(count):
        for t in range(hours):
            storage[b, t] = [x[offsets(b, t, k)] for k in range(3)]
    if np.any(np.minimum(storage[:, :, 0], storage[:, :, 1]) > 1e-5):
        raise ValueError('Simultaneous battery charge and discharge needs a nonconvex model')
    return dict(objective_eur=float(result.fun), values=original,
                zonal_prices=result.eqlin.marginals[:hours * (nz + ni)].reshape(hours, nz + ni)[:, :nz],
                storage=storage, maximum_primal_residual=residual)


def rolling_days(model, costs, start: int, days: int, battery: Battery,
                 lookahead_hours: int = 48, horizon_end: int | None = None):
    """Execute 24 hours at a time, carrying actual stock between coupled LPs.

    The declared terminal MWh is imposed at each look-ahead boundary and at
    the final end. Future model bids/inputs are known in this retrospective
    trial; it is not a real day-ahead forecast or a year-optimal policy.
    """
    if days < 1 or lookahead_hours < 24 or lookahead_hours % 24:
        raise ValueError('Rolling horizon must contain whole UTC days')
    stop = start + 24 * days
    horizon_end = stop if horizon_end is None else horizon_end
    if (start < 0 or stop > len(model['availability']) or horizon_end < stop
            or horizon_end > len(model['availability'])):
        raise ValueError('Rolling period outside source chronology')
    current = battery.initial_mwh
    values, prices, stocks = [], [], []
    cost_eur, residual = 0.0, 0.0
    ng = int(model['ng'])
    for day in range(days):
        hour = start + 24 * day
        horizon = min(lookahead_hours, horizon_end - hour)
        candidate = clear_window(model, costs, hour, horizon,
                                 (replace(battery, initial_mwh=current),))
        used = candidate['storage'][0, :24]
        dispatch = candidate['values'][:24]
        values.append(dispatch)
        prices.append(candidate['zonal_prices'][:24])
        stocks.append(used)
        cost_eur += float(np.sum(dispatch[:, :ng] * costs[hour:hour + 24]))
        cost_eur += battery.throughput_eur_mwh * float(used[:, :2].sum())
        current = float(used[-1, 2])
        residual = max(residual, candidate['maximum_primal_residual'])
    if stop == horizon_end and abs(current - battery.terminal_mwh) > 1e-6:
        raise ValueError('Rolling terminal stock did not close')
    stock = np.concatenate(stocks)
    replay = battery.initial_mwh + np.cumsum(
        battery.charge_efficiency * stock[:, 0]
        - stock[:, 1] / battery.discharge_efficiency)
    if np.max(np.abs(replay - stock[:, 2])) > 1e-6:
        raise ValueError('Rolling stock chronology failed')
    return dict(objective_eur=cost_eur, values=np.concatenate(values),
                zonal_prices=np.concatenate(prices), storage=stock,
                maximum_primal_residual=residual)
