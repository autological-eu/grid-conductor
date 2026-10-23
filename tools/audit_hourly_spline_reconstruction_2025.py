"""Independently reconstruct SciPy bids, LP witnesses, scores and stopping."""
import json
from pathlib import Path
import time
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.sparse import csr_matrix, hstack
from sigmoid_month_pairs_2025 import ROOT, FAMILIES, EMBER, digest, certify
from run_differentiable_spline_2025 import atomic_json
from supply_knot_network_2025 import load
from spline_europe_2025 import ZERO_TECH, problem
from hourly_spline_reconstruction_2025 import OUT, PLAN


def curves(theta):
    inc = .001 + 20 * np.logaddexp(0, theta[:, 1:])
    heights = np.c_[np.zeros(len(theta)), np.cumsum(inc, axis=1)]
    return PchipInterpolator(np.linspace(0, 1, 6), heights.T, axis=0)


def costs_for(sealed, data, theta, hours, bins):
    zero = np.array([g['technology'] in ZERO_TECH for g in sealed['groups']])
    edges = np.linspace(0, 1, bins + 1)
    costs = []
    for t, hour in enumerate(hours):
        p = curves(theta[t])
        j = p.antiderivative()
        average = np.diff(j(edges) - edges[:, None] * p(.5), axis=0).T * bins
        bid = data['source_cost'][hour, :, None] + 80 * np.tanh(theta[t, :, :1] / 4) + average
        bid[zero] = 0
        costs.append(bid.ravel())
    return np.c_[costs, data['emergency_cost'][hours]]


def run():
    began = time.perf_counter()
    summary = json.loads((OUT / 'summary.json').read_text())
    history = json.loads((OUT / 'history.json').read_text())
    provenance = json.loads((OUT / 'provenance.json').read_text())
    for name, sha in provenance.items():
        if digest(ROOT / name) != sha:
            raise ValueError('Changed producer: ' + name)
    assert digest(OUT / 'history.json') == summary['history_sha256']
    assert digest(OUT / 'best-parameters.npy') == summary['best_parameter_sha256']
    design = json.loads(PLAN.read_text())
    sealed, data, A, emergency, original_capacity = load()
    hours = np.load(OUT / 'hours.npy')
    assert len(hours) == 744 and np.array_equal(hours, np.arange(744))
    count, bins, nz = len(sealed['groups']), design['lp_tranches_per_curve'], sealed['nz']
    ng = count * bins + emergency.shape[1]
    matrix = hstack([A[:, np.repeat(np.arange(count), bins)], emergency, A[:, count:]], format='csc')
    mapping = np.array(sealed['mapping'])
    ncountry, ntech = len(sealed['countries']), len(sealed['technologies'])
    destinations = [g['country_id'] * ntech + sealed['technologies'].index(g['technology']) for g in sealed['original_groups']]
    attribution = csr_matrix((np.ones(len(mapping)), (np.arange(len(mapping)), destinations)), shape=(len(mapping), ncountry * ntech))
    membership = csr_matrix((np.ones(len(mapping)), (np.arange(len(mapping)), mapping)), shape=(len(mapping), count))
    capacity = original_capacity[hours] @ membership
    np.testing.assert_allclose(capacity, data['capacity'][hours], atol=1e-7, rtol=0)
    shares = np.divide(original_capacity[hours], capacity[:, mapping], out=np.zeros_like(original_capacity[hours]), where=capacity[:, mapping] > 0)
    target = data['observed_prices'][hours]
    complete = np.isfinite(data['observed_prices']).all(axis=0)
    ember = data['ember'][design['month'] - 1]
    known = np.isfinite(ember)
    rows = []
    best, best_step, stale = np.inf, None, 0
    maxima = {}
    for step, record in enumerate(history):
        assert step == record['iteration']
        stage = OUT / f'iteration-{step:03d}'
        assert digest(stage / 'parameters.npy') == record['parameter_sha256']
        assert digest(stage / 'lp.npz') == record['lp_sha256']
        theta = np.load(stage / 'parameters.npy')
        with np.load(stage / 'lp.npz') as z:
            w = {k: z[k] for k in z.files}
        assert np.array_equal(w['hours'], hours)
        costs = costs_for(sealed, data, theta, hours, bins)
        av = np.c_[np.repeat(data['capacity'][hours] / bins, bins, axis=1), data['emergency_available'][hours]]
        checks = certify(matrix, costs, av, data, hours, w['values'], w['row_duals'], w['objectives'], ng, sealed['nl'], nz)
        for key, value in checks.items():
            maxima[key] = max(maxima.get(key, 0), value)
        assert np.maximum(w['values'][:, count * bins:ng], 0).sum() <= 1e-6
        q = w['values'][:, :count * bins].reshape(len(hours), count, bins).sum(axis=2)
        np.testing.assert_allclose(q, w['quantities'], atol=1e-8, rtol=0)
        generation = ((q[:, mapping] * shares) @ attribution).reshape(len(hours), ncountry, ntech) + data['fixed_generation'][hours]
        np.testing.assert_allclose(generation, w['generation'], atol=1e-7, rtol=0)
        np.testing.assert_allclose(generation.sum(axis=(1, 2)), q.sum(axis=1) + data['fixed_generation'][hours].sum(axis=(1, 2)), atol=1e-5, rtol=0)
        monthly = np.column_stack([generation[:, :, [sealed['technologies'].index(t) for t in EMBER[f]]].sum(axis=(0, 2)) / 1e6 for f in FAMILIES])
        np.testing.assert_allclose(monthly, record['monthly_generation_twh'], atol=1e-10, rtol=0)
        price_mae = float(abs(w['row_duals'][:, :nz][:, complete] - target[:, complete]).mean())
        generation_mae = float(abs(monthly[known] - ember[known]).mean())
        normalized = float((abs(monthly[known] - ember[known]) / np.maximum(ember[known], .25)).mean())
        for key, score in [('price_mae', price_mae), ('generation_mae_twh', generation_mae), ('generation_normalized_mae', normalized)]:
            assert abs(score - record['lp'][key]) < 1e-9, key
        improved = price_mae < best - design['minimum_price_improvement_eur_mwh']
        if improved:
            best, best_step, stale = price_mae, step, 0
        else:
            stale += 1
        assert record['improved_lp_price'] == improved
        assert record['nonimproving_iterations'] == stale and record['best_iteration'] == best_step
        assert stale < design['patience'] or step == len(history) - 1
        rows.append(dict(iteration=step, price_mae=price_mae, generation_mae_twh=generation_mae, best_iteration=best_step, nonimproving_iterations=stale))
        atomic_json(OUT / 'audit-progress.json', dict(iterations=rows, maxima=maxima))
        print('AUDIT_LP', step, price_mae, flush=True)
    assert stale == design['patience'] and best_step == summary['best_iteration']
    np.testing.assert_array_equal(np.load(OUT / 'best-parameters.npy'), np.load(OUT / f'iteration-{best_step:03d}/parameters.npy'))
    # Replay best smooth KKT residuals using independent SciPy prices, not the
    # producer's cubic interpolation. Rebuild the unchanged physical equations.
    theta = np.load(OUT / 'best-parameters.npy')
    zero = np.array([g['technology'] in ZERO_TECH for g in sealed['groups']])
    smooth_max = dict(primal_mw=0., stationarity_eur_mwh=0., complementarity_eur=0., price_export_difference=0.)
    stage = OUT / f'iteration-{best_step:03d}'
    with np.load(stage / 'smooth.npz') as z:
        exported_prices = z['prices']
        exported_values = z['values']
    for t, hour in enumerate(hours):
        p = problem(sealed, data, A, np.zeros((count, 11)), int(hour))
        with np.load(stage / f'hour-{hour:04d}.npz') as z:
            r = {k: z[k] for k in z.files}
        ids = p['active'][p['active'] < count]
        u = r['x'][:len(ids)] / (data['capacity'][hour, ids] / 1000)
        curve = curves(theta[t])
        price = curve(u)[np.arange(len(ids)), ids] - curve(.5)[ids]
        # curve(u) has one evaluation per active resource against all curves.
        shift = 80 * np.tanh(theta[t, ids, 0] / 4)
        source = data['source_cost'][hour, ids].copy()
        price[zero[ids]], shift[zero[ids]], source[zero[ids]] = 0, 0, 0
        gradient = np.r_[source + shift + price + .01 * u, 1e-6 * r['x'][len(ids):]]
        stationarity = float(abs(gradient + p['E'].T @ r['nu'] + p['G'].T @ r['lam']).max(initial=0))
        primal = max(float(abs(p['E'] @ r['x'] - p['b']).max(initial=0)), float(abs(p['equality'] @ r['x'] - p['full_b']).max(initial=0)), float(np.maximum(p['G'] @ r['x'] - p['h'], 0).max(initial=0)), float(abs(p['G'] @ r['x'] + r['slack'] - p['h']).max(initial=0))) * 1000
        complementarity = float(r['slack'] @ r['lam']) * 1000
        assert r['slack'].min() > 0 and r['lam'].min() > 0
        assert primal <= 1e-4 and stationarity <= 2e-7 and complementarity <= .05
        nu = np.zeros(len(p['full_b']))
        nu[p['equality_rows']] = r['nu']
        price_difference = float(abs(-nu[:nz] - exported_prices[t]).max())
        assert price_difference <= 1e-10
        full = np.zeros(A.shape[1])
        full[p['active']], full[p['fixed']] = r['x'], p['fixed_values']
        np.testing.assert_allclose(full, exported_values[t], atol=1e-10, rtol=0)
        for key, value in dict(primal_mw=primal, stationarity_eur_mwh=stationarity, complementarity_eur=complementarity, price_export_difference=price_difference).items():
            smooth_max[key] = max(smooth_max[key], value)
    atomic_json(OUT / 'audit.json', dict(status='all_iteration_LP_scores_and_stopping_plus_best_smooth_KKT_passed',
        lp_hours=len(history) * len(hours), best_smooth_hours=len(hours), iterations=rows, lp_maxima=maxima, smooth_maxima=smooth_max,
        summary_sha256=digest(OUT / 'summary.json'), auditor_sha256=digest(Path(__file__)), seconds=time.perf_counter() - began))


if __name__ == '__main__':
    run()
