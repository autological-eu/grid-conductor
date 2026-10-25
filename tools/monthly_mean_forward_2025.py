"""Training-only monthly economic-function means and independent score audits."""
import numpy as np
from independent_hourly_transport_2025 import economic_nodes, raw_from_nodes
from report_batched_transport_2025 import independent_response
from supply_knot_network_2025 import generation
from sigmoid_month_pairs_2025 import metric


def monthly_mean(theta, availability, neutral):
    if theta.ndim != 3 or theta.shape[:2] != availability.shape or theta.shape[-1] != 6:
        raise ValueError('Expected actual training hours × groups × six coefficients')
    nodes = economic_nodes(theta)
    support = (availability > 0).sum(axis=0)
    mean = economic_nodes(neutral).copy()
    for g in range(theta.shape[1]):
        present = availability[:, g] > 0
        if present.any():
            mean[g] = nodes[present, g].mean(axis=0)
    raw = raw_from_nodes(mean)
    np.testing.assert_allclose(economic_nodes(raw), mean, atol=1e-10, rtol=0)
    return raw, support


def audit_score(state, market, theta, result, month):
    """Replay every response independently before discarding large live arrays."""
    source, data, _, _, capacity = state
    hours = result['hours']
    maxima = dict(balance_mw=0., bound_mw=0., response_mw=0., residual_work_eur=0.)
    replay_q = np.empty_like(result['quantities_gw'])
    for start in range(0, len(hours), 96):
        sl = slice(start, start+96); h = hours[sl]
        raw = theta if theta.ndim == 2 else theta[sl]
        q, f = independent_response(market, raw, result['prices'][sl], h)
        balance = q @ market.Z + f @ market.M - market.load[h]
        bound = max(np.maximum(-q, 0).max(), np.maximum(q-market.capacity[h], 0).max(),
                    np.maximum(market.lower[h]-f, 0).max(), np.maximum(f-market.upper[h], 0).max())*1000
        values = [abs(balance).max()*1000, bound,
                  max(abs(q-result['quantities_gw'][sl]).max(), abs(f-result['flows_gw'][sl]).max())*1000,
                  (abs(balance*result['prices'][sl]).sum(axis=1)*1000).max()]
        for key, value in zip(maxima, values):
            maxima[key] = max(maxima[key], float(value))
        replay_q[sl] = q
    if not all(np.isfinite(list(maxima.values()))) or max(maxima[k] for k in maxima if k != 'residual_work_eur') > 1e-4 or maxima['residual_work_eur'] >= .05:
        raise ValueError('Independent response/balance replay failed: '+str(maxima))
    gen = generation(source, data, capacity, replay_q*1000, hours)
    metrics, monthly = metric(source, data, result['prices'], gen, hours, month)
    complete = np.isfinite(data['observed_prices']).all(axis=0)
    zone = abs(result['prices'][:, complete]-data['observed_prices'][hours][:, complete]).mean(axis=0)
    np.testing.assert_allclose(zone.mean(), metrics['price_mae'], atol=1e-10, rtol=0)
    return dict(metrics=metrics, monthly_generation_twh=monthly.tolist(), zone_mae=zone.tolist(),
                audit=maxima, solver_certificate=result['certificate'], seconds=result['seconds']), gen
