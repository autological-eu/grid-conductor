"""Exact interval averages of learned PWL offers, original coupled-network LP.

This transfers economic curves, not the fast model's smoothed inverse responses.
The hard LP uses declared bid discretization; original PTDF/island/internal-line
rows and offsets return, and the fast model's quadratic transport cost is absent.
"""
import time
import numpy as np
from scipy.sparse import hstack
from monthly_diurnal_splines_2025 import labels, expand
from sigmoid_month_pairs_2025 import certify


def bids_from_anchors(anchors, bins):
    if bins % 5:
        raise ValueError('Bid bins must align with all six learned supply nodes')
    mid = (np.arange(bins) + .5) / bins
    segment = np.minimum((mid * 5).astype(int), 4)
    weight = mid * 5 - segment
    return anchors[..., segment] * (1 - weight) + anchors[..., segment + 1] * weight


def clear(state, market, theta, hours, bins=20, progress=None):
    from nve_hydro_diagnostics import solver
    from run_regional_water_candidate_2025 import guarded_hour
    source, data, original_matrix, _, _ = state
    started = time.perf_counter()
    count = len(source['groups']); ng = count * bins
    matrix = hstack([original_matrix[:, np.repeat(np.arange(count), bins)],
                     original_matrix[:, count:]], format='csc')
    offers = market.offers(expand(theta, labels(source['groups'], hours)), hours)
    cost = bids_from_anchors(offers['anchors'], bins).reshape(len(hours), ng)
    availability = np.repeat(data['capacity'][hours] / bins, bins, axis=1)
    model = {k: data[k][hours] for k in ['load', 'island_rhs', 'link_min', 'link_max']}
    model.update(A=matrix, cost=cost, availability=availability, ng=ng,
                 nl=source['nl'], nz=source['nz'], zones=source['zones'],
                 ratings=data['ratings'], islands=[None] * data['island_rhs'].shape[1])
    backend = solver(model)
    backend.setOptionValue('primal_feasibility_tolerance', 1e-8)
    values = np.zeros((len(hours), matrix.shape[1]))
    duals = np.zeros((len(hours), matrix.shape[0]))
    objectives = np.zeros(len(hours))
    for t, hour in enumerate(hours):
        if progress is not None and t % 168 == 0:
            progress(t, len(hours))
        result, value = guarded_hour(backend, model, t, data['flow'][hour])
        if value is None:
            backend = solver(model)
            backend.setOptionValue('primal_feasibility_tolerance', 1e-8)
            result, value = guarded_hour(backend, model, t, data['flow'][hour])
        if value is None:
            raise RuntimeError(f'Physical LP failed at hour {hour}: {result}')
        values[t] = value
        duals[t] = backend.getSolution().row_dual
        objectives[t] = result['objective_eur']
    certificate = certify(matrix, cost, availability, data, hours, values, duals,
                          objectives, ng, source['nl'], source['nz'])
    quantities = values[:, :ng].reshape(len(hours), count, bins).sum(axis=2)
    return dict(values=values, row_duals=duals, objectives=objectives,
                hours=hours, quantities_gw=quantities / 1000,
                prices=duals[:, :source['nz']]), dict(
                    seconds=time.perf_counter() - started, bins=bins,
                    certificate=certificate, emergency_mwh=0,
                    scope='Original coupled physical rows/offsets; hard interval-average PWL bids, no quadratic transport cost.')
