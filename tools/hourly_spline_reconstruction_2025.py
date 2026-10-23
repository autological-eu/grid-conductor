"""Full-month hourly spline inverse reconstruction with actual LP selection.

Existing numerical producers are imported, never changed. Each gradient update
uses every hour and exact monthly generation totals. Hour-local KKT witnesses
are saved on disk; a second adjoint pass avoids retaining a month's factorizations.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import fcntl
import json
import multiprocessing
import os
from pathlib import Path
import resource
import time
import traceback

import numpy as np
from scipy.sparse import hstack
from differentiable_spline_clearing import solve, factor_kkt, fraction
from sigmoid_month_pairs_2025 import ROOT, OUT as SOURCE, digest, metric, certify, split
from run_differentiable_spline_2025 import atomic_json, targets, fixed_month
from run_supply_knots_lp_2025 import joint_loss
from supply_knot_network_2025 import load, cost_for, generation
from spline_europe_2025 import problem, backward, ZERO_TECH

PLAN = ROOT / 'config/hourly-spline-reconstruction-2025.json'
OUT = ROOT / 'data/bidding-zone-network-2025/hourly-spline-reconstruction-v1'
PRIOR = ROOT / 'data/bidding-zone-network-2025/supply-knots-lp-v1'
STATE = None
PROBLEMS = {}
THETA = {}
FIELDS = [0, 5, 6, 7, 8, 9]


def expand(parameters):
    out = np.zeros((len(parameters), 10))
    out[:, FIELDS] = parameters
    return out


def initialize(sealed, data, hours, shared):
    groups = sealed['groups']
    theta = np.zeros((len(hours), len(groups), 6))
    zi = [g['zone_id'] for g in groups]
    theta[:, :, 0] = np.einsum('tgf,gf->tg', data['features'][hours][:, zi], shared[:, :5])
    theta[:, :, 1:] = shared[None, :, 5:]
    active = data['capacity'][hours] > 0
    active[:, [g['technology'] in ZERO_TECH for g in groups]] = False
    return theta, active


def penalties(theta, initial, active, design):
    delta = theta - initial
    n = max(1, int(active.sum()) * theta.shape[-1])
    gradient = 2 * design['hourly_shrinkage'] * delta * active[:, :, None] / n
    ridge = design['hourly_shrinkage'] * float((delta[active] ** 2).sum()) / n
    adjacent = active[:-1] & active[1:]
    difference = delta[1:] - delta[:-1]
    m = max(1, int(adjacent.sum()) * theta.shape[-1])
    temporal = design['temporal_penalty'] * float((difference[adjacent] ** 2).sum()) / m
    g = 2 * design['temporal_penalty'] * difference * adjacent[:, :, None] / m
    gradient[1:] += g
    gradient[:-1] -= g
    return ridge + temporal, gradient, dict(hourly_shrinkage=ridge, temporal_penalty=temporal)


def should_keep(score, best, design):
    return score < best - design['minimum_price_improvement_eur_mwh']


def warm_solve(cost, p, previous):
    """Same Newton equations/tolerances; optionally initialize all KKT variables."""
    if previous is None:
        previous = solve(cost, p['E'], p['b'], p['G'], p['h'], x0=p['x0'])
    E, b, G, h = p['E'], p['b'], p['G'], p['h']
    n, ne = len(previous['x']), len(b)
    x, nu, slack, lam = [previous[k].copy() for k in ['x', 'nu', 'slack', 'lam']]
    # Reopen the interior before changing bids; reusing near-zero slack/duals
    # directly can trap a predictor-corrector step at the previous active set.
    slack = np.maximum(slack, 1e-4)
    lam = np.maximum(lam, 1e-4)
    began = time.perf_counter()
    for iteration in range(90):
        value, grad, H = cost.evaluate(x)
        rd, rp, ri = grad + E.T @ nu + G.T @ lam, E @ x - b, G @ x + slack - h
        gap = float(slack @ lam)
        primal = max(float(abs(rp).max(initial=0)), float(np.maximum(G @ x - h, 0).max(initial=0)), float(abs(ri).max(initial=0)))
        if primal <= 2e-10 and abs(rd).max(initial=0) <= 2e-9 and gap <= 1e-8:
            return dict(x=x, nu=nu, slack=slack, lam=lam, objective=value, iterations=iteration + 1,
                certificate=dict(primal_mw=primal * 1000, stationarity_eur_mwh=float(abs(rd).max(initial=0)), complementarity_eur=gap * 1000), seconds=time.perf_counter() - began)
        linear = factor_kkt(H, E, G, slack / lam)
        def direction(complementarity):
            d = linear(np.r_[-rd, -rp, complementarity / lam - ri])
            dx, dn, dl = d[:n], d[n:n + ne], d[n + ne:]
            return dx, dn, dl, -ri - G @ dx
        dx, dn, dl, ds = direction(slack * lam)
        ap, ad = fraction(slack, ds), fraction(lam, dl)
        mu, mu_aff = gap / len(h), float((slack + ap * ds) @ (lam + ad * dl) / len(h))
        sigma = min(1., max(0., mu_aff / mu) ** 3)
        dx, dn, dl, ds = direction(slack * lam + ds * dl - sigma * mu)
        ap, ad = fraction(slack, ds, .995), fraction(lam, dl, .995)
        x += ap * dx
        slack += ap * ds
        nu += ad * dn
        lam += ad * dl
        if not np.isfinite(x).all() or min(slack.min(), lam.min()) <= 0:
            raise ValueError('Invalid warm-start Newton iterate')
    raise RuntimeError(f'Warm Newton did not converge: primal={primal}, stationarity={abs(rd).max()}, gap={gap}')


def worker_init():
    resource.setrlimit(resource.RLIMIT_AS, (5 * 1024 ** 3,) * 2)


def hour_problem(index, hour, state_path):
    sealed, data, A, _, _ = STATE
    if state_path not in THETA:
        THETA.clear()
        THETA[state_path] = np.load(state_path, mmap_mode='r')
    theta = expand(THETA[state_path][index])
    if hour not in PROBLEMS:
        PROBLEMS[hour] = problem(sealed, data, A, np.zeros((len(theta), 11)), hour)
    p = PROBLEMS[hour].copy()
    ids = p['active'][p['active'] < len(theta)]
    p['cost'] = cost_for(sealed, data, theta, hour, ids, len(p['active']) - len(ids))
    # Hour-specific scalar midpoint: collapse clock to [1,0,0,0,0].
    p['cost'].features[:] = 0
    p['cost'].features[:, 0] = 1
    p['cost'].__post_init__()
    return p


def forward_job(index, hour, state_path, stage, previous_stage):
    sealed, _, A, _, _ = STATE
    p = hour_problem(index, hour, state_path)
    previous = None
    prior_path = Path(previous_stage) / f'hour-{hour:04d}.npz' if previous_stage else None
    if prior_path is not None and prior_path.exists():
        with np.load(prior_path) as z:
            previous = {k: z[k] for k in ['x', 'nu', 'slack', 'lam']}
    fallback = None
    try:
        r = warm_solve(p['cost'], p, previous)
    except (RuntimeError, ValueError, FloatingPointError) as exc:
        if previous is None:
            raise
        fallback = str(exc)
        r = warm_solve(p['cost'], p, None)
    full = np.zeros(A.shape[1])
    full[p['active']], full[p['fixed']] = r['x'], p['fixed_values']
    if abs(p['equality'] @ r['x'] - p['full_b']).max(initial=0) * 1000 > 1e-4:
        raise ValueError('Original equality replay failed')
    certificate = r['certificate']
    if certificate['primal_mw'] > 1e-4 or certificate['complementarity_eur'] > .05:
        raise ValueError('Original physical/economic acceptance gate failed')
    nu = np.zeros(len(p['full_b']))
    nu[p['equality_rows']] = r['nu']
    path = Path(stage) / f'hour-{hour:04d}.npz'
    temporary = path.with_suffix('.tmp.npz')
    np.savez(temporary, **{k: r[k] for k in ['x', 'nu', 'slack', 'lam']})
    os.replace(temporary, path)
    return index, -nu[:sealed['nz']], full, certificate, r['iterations'], r['seconds'], fallback


def backward_job(index, hour, state_path, stage, gx, gp):
    p = hour_problem(index, hour, state_path)
    with np.load(Path(stage) / f'hour-{hour:04d}.npz') as z:
        r = {k: z[k] for k in ['x', 'nu', 'slack', 'lam']}
    r['problem'] = p
    gradient = backward(r, gx, gp)[:, FIELDS]
    return index, gradient


def lp_clear(sealed, data, A, emergency, hourly_theta, hours, bins):
    from nve_hydro_diagnostics import solver
    from run_regional_water_candidate_2025 import guarded_hour
    count = len(sealed['groups'])
    ng = count * bins + emergency.shape[1]
    matrix = hstack([A[:, np.repeat(np.arange(count), bins)], emergency, A[:, count:]], format='csc')
    offers = []
    for t, hour in enumerate(hours):
        ids = np.flatnonzero(data['capacity'][hour] > 0)
        c = np.zeros((count, bins))
        cost = cost_for(sealed, data, expand(hourly_theta[t]), int(hour), ids, regularizer=0)
        cost.features[:] = 0
        cost.features[:, 0] = 1
        cost.__post_init__()
        c[ids] = cost.interval_bids(bins)
        offers.append(c.ravel())
    costs = np.c_[offers, data['emergency_cost'][hours]]
    av = np.c_[np.repeat(data['capacity'][hours] / bins, bins, axis=1), data['emergency_available'][hours]]
    model = {k: data[k][hours] for k in ['load', 'island_rhs', 'link_min', 'link_max']}
    model.update(A=matrix, cost=costs, availability=av, ng=ng, nl=sealed['nl'], nz=sealed['nz'], zones=sealed['zones'], ratings=data['ratings'], islands=[None] * data['island_rhs'].shape[1])
    h = solver(model)
    h.setOptionValue('primal_feasibility_tolerance', 1e-8)
    x, y, objectives = np.zeros((len(hours), matrix.shape[1])), np.zeros((len(hours), matrix.shape[0])), np.zeros(len(hours))
    for t, hour in enumerate(hours):
        record, value = guarded_hour(h, model, t, data['flow'][hour])
        if value is None:
            h = solver(model)
            h.setOptionValue('primal_feasibility_tolerance', 1e-8)
            record, value = guarded_hour(h, model, t, data['flow'][hour])
        if value is None:
            raise RuntimeError(f'Original LP failed: {hour}, {record}')
        x[t], y[t], objectives[t] = value, h.getSolution().row_dual, record['objective_eur']
    if np.maximum(x[:, count * bins:ng], 0).sum() > 1e-6:
        raise ValueError('Artificial emergency dispatch')
    checks = certify(matrix, costs, av, data, hours, x, y, objectives, ng, sealed['nl'], sealed['nz'])
    q = x[:, :count * bins].reshape(len(hours), count, bins).sum(axis=2)
    return dict(values=x, row_duals=y, objectives=objectives, hours=hours, quantities=q), checks


def setup():
    global STATE
    design = json.loads(PLAN.read_text())
    for name, sha in json.loads((PRIOR / 'provenance.json').read_text()).items():
        if digest(ROOT / name) != sha:
            raise ValueError('Changed source provenance: ' + name)
    STATE = load()
    sealed, data, _, _, _ = STATE
    month = design['month']
    hours, _ = split(month, month + 1)
    source = PRIOR / f'proposal-{month:02d}.json'
    proposal = json.loads(source.read_text())
    pair = json.loads((PRIOR / f'pair-{month:02d}-{month + 1:02d}.json').read_text())
    if digest(source) != pair['proposal_sha256']:
        raise ValueError('Changed own-month initializer')
    initial, active = initialize(sealed, data, hours, np.array(proposal['theta']))
    return design, hours, initial, active


def save_array(path, value):
    temporary = path.with_suffix('.tmp.npy')
    np.save(temporary, value)
    os.replace(temporary, path)


def run():
    OUT.mkdir(exist_ok=True)
    lock = (OUT / 'job.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    design, hours, initial, active = setup()
    pilot = json.loads((OUT / 'pilot.json').read_text())
    if pilot['status'] != 'passed' or pilot['source_sha256'] != digest(Path(__file__).resolve()):
        raise ValueError('Run the current European gradient pilot before fitting')
    sealed, data, A, emergency, source_capacity = STATE
    paths = [PLAN, Path(__file__).resolve(), OUT / 'pilot.json', ROOT / 'tools/pilot_hourly_spline_reconstruction_2025.py', PRIOR / 'proposal-01.json', PRIOR / 'provenance.json', SOURCE / 'inputs.json', SOURCE / 'inputs.npz']
    paths += [ROOT / 'tools' / n for n in ['supply_knot_splines_2025.py', 'supply_knot_network_2025.py', 'spline_europe_2025.py', 'differentiable_spline_clearing.py', 'run_supply_knots_lp_2025.py']]
    provenance = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    if (OUT / 'provenance.json').exists() and json.loads((OUT / 'provenance.json').read_text()) != provenance:
        raise ValueError('Changed sealed producer; use a fresh experiment')
    atomic_json(OUT / 'provenance.json', provenance)
    save_array(OUT / 'initial.npy', initial)
    np.save(OUT / 'hours.npy', hours)
    target = targets(data, hours, design['month'])
    complete = np.isfinite(data['observed_prices']).all(axis=0)
    # Match stopping-score coverage; unknown observations remain unknown.
    target['prices'][:, ~complete] = np.nan
    fixed = fixed_month(sealed, data, hours)
    theta, m, v = initial.copy(), np.zeros_like(initial), np.zeros_like(initial)
    step, stale, best, best_step, history = 0, 0, float('inf'), None, []
    if (OUT / 'resume.npz').exists():
        with np.load(OUT / 'resume.npz') as z:
            theta, m, v, step = z['theta'], z['m'], z['v'], int(z['step'])
        history = json.loads((OUT / 'history.json').read_text())
        # A crash after evaluation but before the atomic Adam checkpoint must
        # replay that iteration without counting it twice toward patience.
        history = [r for r in history if r['iteration'] < step]
        if history:
            best_record = [r for r in history if r['improved_lp_price']][-1]
            best, best_step = best_record['lp']['price_mae'], best_record['iteration']
            stale = history[-1]['nonimproving_iterations']
    if (OUT / 'summary.json').exists():
        raise RuntimeError('Already complete; inspect saved results instead of duplicating')
    began = time.perf_counter()
    with ProcessPoolExecutor(max_workers=design['workers'], initializer=worker_init, mp_context=multiprocessing.get_context('fork')) as pool:
        while True:
            stage = OUT / f'iteration-{step:03d}'
            stage.mkdir(exist_ok=True)
            state_path = stage / 'parameters.npy'
            save_array(state_path, theta)
            previous = str(OUT / f'iteration-{step - 1:03d}') if step else None
            pp, xx = np.zeros((len(hours), sealed['nz'])), np.zeros((len(hours), A.shape[1]))
            certificates, iterations, fallbacks = [], [], []
            futures = [pool.submit(forward_job, t, int(h), str(state_path), str(stage), previous) for t, h in enumerate(hours)]
            for done, future in enumerate(as_completed(futures), 1):
                t, p, x, cert, nit, seconds, fallback = future.result()
                pp[t], xx[t] = p, x
                certificates.append(cert)
                iterations.append(nit)
                if fallback:
                    fallbacks.append(dict(hour=int(hours[t]), reason=fallback))
                if done % 24 == 0 or done == len(hours):
                    atomic_json(OUT / 'progress.json', dict(stage='full-month-forward', iteration=step, completed_hours=done, total_hours=len(hours), elapsed_seconds=time.perf_counter() - began))
                    print('FORWARD', step, done, len(hours), flush=True)
            zero = np.zeros((len(sealed['groups']), 10))
            loss, gx, gp, _, parts = joint_loss(sealed, data, source_capacity, design, zero, zero, pp, xx, hours, len(hours), target, fixed)
            penalty, direct, penalty_parts = penalties(theta, initial, active, design)
            w, lp_certificate = lp_clear(sealed, data, A, emergency, theta, hours, design['lp_tranches_per_curve'])
            w['generation'] = generation(sealed, data, source_capacity, w['quantities'], hours)
            metrics, monthly = metric(sealed, data, w['row_duals'][:, :sealed['nz']], w['generation'], hours, design['month'])
            smooth_gen = generation(sealed, data, source_capacity, xx[:, :len(sealed['groups'])] * 1000, hours)
            smooth_metrics, _ = metric(sealed, data, pp, smooth_gen, hours, design['month'])
            score = metrics['price_mae']
            improved = should_keep(score, best, design)
            if improved:
                best, best_step, stale = score, step, 0
                save_array(OUT / 'best-parameters.npy', theta)
            else:
                stale += 1
            np.savez_compressed(stage / 'lp.npz', **w)
            np.savez_compressed(stage / 'smooth.npz', prices=pp, values=xx, hours=hours)
            record = dict(iteration=step, loss=loss + penalty, **parts, **penalty_parts, lp=metrics, smooth=smooth_metrics,
                improved_lp_price=improved, nonimproving_iterations=stale, best_iteration=best_step,
                monthly_generation_twh=monthly.tolist(), lp_certificate=lp_certificate,
                smooth_certificate={k: max(c[k] for c in certificates) for k in certificates[0]},
                mean_newton_iterations=float(np.mean(iterations)), cold_fallbacks=fallbacks,
                parameter_sha256=digest(state_path), lp_sha256=digest(stage / 'lp.npz'), elapsed_seconds=time.perf_counter() - began)
            history = [r for r in history if r['iteration'] < step] + [record]
            atomic_json(OUT / 'history.json', history)
            print('ITERATION', step, 'LP', metrics, 'stale', stale, 'best', best_step, flush=True)
            if stale >= design['patience']:
                for name, sha in provenance.items():
                    if digest(ROOT / name) != sha:
                        raise ValueError('Producer changed during fitting: ' + name)
                atomic_json(OUT / 'summary.json', dict(status='stopped_after_three_nonimproving_LP_price_iterations', month=design['month'], hours=len(hours),
                    scope=design['scope'], best_iteration=best_step, best_lp_price_mae=best, initial=history[0], best=history[best_step], last=record,
                    evaluated_iterations=len(history), best_parameter_sha256=digest(OUT / 'best-parameters.npy'), history_sha256=digest(OUT / 'history.json'),
                    seconds_this_session=time.perf_counter() - began, active_parameters=int(active.sum()) * 6))
                atomic_json(OUT / 'progress.json', dict(stage='complete', best_iteration=best_step, iterations=len(history), hours=len(hours)))
                break
            gradient = direct.copy()
            futures = [pool.submit(backward_job, t, int(h), str(state_path), str(stage), gx[t], gp[t]) for t, h in enumerate(hours)]
            for done, future in enumerate(as_completed(futures), 1):
                t, g = future.result()
                gradient[t] += g
                if done % 48 == 0 or done == len(hours):
                    atomic_json(OUT / 'progress.json', dict(stage='full-month-adjoint', iteration=step, completed_hours=done, total_hours=len(hours)))
            gradient *= active[:, :, None]
            if not np.isfinite(gradient).all():
                raise ValueError('Nonfinite full-month gradient')
            record['gradient_norm'] = float(np.linalg.norm(gradient))
            atomic_json(OUT / 'history.json', history)
            m, v = .9 * m + .1 * gradient, .999 * v + .001 * gradient ** 2
            t = step + 1
            theta -= design['learning_rate'] * (m / (1 - .9 ** t)) / (np.sqrt(v / (1 - .999 ** t)) + 1e-8)
            theta[~active] = initial[~active]
            step += 1
            temporary = OUT / 'resume.tmp.npz'
            np.savez_compressed(temporary, theta=theta, m=m, v=v, step=step)
            os.replace(temporary, OUT / 'resume.npz')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (5 * 1024 ** 3,) * 2)
    try:
        run()
    except Exception:
        if OUT.exists():
            atomic_json(OUT / 'failure.json', dict(traceback=traceback.format_exc()))
        raise
