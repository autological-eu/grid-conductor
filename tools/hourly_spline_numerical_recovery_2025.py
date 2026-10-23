"""Fresh-provenance recovery of a failed full-month iteration.

Economic objective, gradients, Adam state, physics and all gates are unchanged.
Only a failed Newton solve uses damped barrier steps instead of an undamped
predictor/corrector. Completed parent witnesses are hardlinked and revalidated.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import time
import numpy as np
import hourly_spline_reconstruction_2025 as base
from differentiable_spline_clearing import factor_kkt, fraction

PARENT = base.OUT
OUT = base.ROOT / 'data/bidding-zone-network-2025/hourly-spline-reconstruction-recovery-v1'
PLAN = base.ROOT / 'config/hourly-spline-reconstruction-recovery-2025.json'
ORIGINAL_FORWARD = base.forward_job


def residual(cost, E, b, G, h, x, nu, slack, lam, tau):
    value, grad, H = cost.evaluate(x)
    rd, rp, ri = grad + E.T @ nu + G.T @ lam, E @ x - b, G @ x + slack - h
    rc = slack * lam - tau
    merit = float(np.linalg.norm(np.r_[rd, rp, ri, rc]))
    return value, H, rd, rp, ri, rc, merit


def damped_solve(cost, p, previous=None):
    began = time.perf_counter()
    E, b, G, h = p['E'], p['b'], p['G'], p['h']
    n, ne = E.shape[1], len(b)
    if previous is None:
        x = np.r_[cost.capacity * .5, np.zeros(cost.extra_count)]
        nu, slack, lam = np.zeros(ne), np.maximum(1., h - G @ x), np.ones(len(h))
    else:
        x, nu, slack, lam = [previous[k].copy() for k in ['x', 'nu', 'slack', 'lam']]
        slack, lam = np.maximum(slack, 1e-4), np.maximum(lam, 1e-4)
    backtracks = 0
    for iteration in range(250):
        gap = float(slack @ lam)
        tau = max(1e-12, min(.05, .1 * gap / len(h)))
        value, H, rd, rp, ri, rc, merit = residual(cost, E, b, G, h, x, nu, slack, lam, tau)
        primal = max(float(abs(rp).max(initial=0)), float(np.maximum(G @ x - h, 0).max(initial=0)), float(abs(ri).max(initial=0)))
        if primal <= 2e-10 and abs(rd).max(initial=0) <= 2e-9 and gap <= 1e-8:
            return dict(x=x, nu=nu, slack=slack, lam=lam, objective=value, iterations=iteration + 1,
                certificate=dict(primal_mw=primal * 1000, stationarity_eur_mwh=float(abs(rd).max(initial=0)), complementarity_eur=gap * 1000),
                seconds=time.perf_counter() - began, backtracks=backtracks)
        linear = factor_kkt(H, E, G, slack / lam)
        direction = linear(np.r_[-rd, -rp, rc / lam - ri])
        dx, dn, dl = direction[:n], direction[n:n + ne], direction[n + ne:]
        ds = -ri - G @ dx
        alpha = min(fraction(slack, ds, .995), fraction(lam, dl, .995))
        for attempt in range(60):
            xn, nn, sn, ln = x + alpha * dx, nu + alpha * dn, slack + alpha * ds, lam + alpha * dl
            if min(sn.min(), ln.min()) > 0 and np.isfinite(xn).all():
                new_merit = residual(cost, E, b, G, h, xn, nn, sn, ln, tau)[-1]
                if new_merit <= (1 - 1e-4 * alpha) * merit:
                    break
            alpha *= .5
            backtracks += 1
        else:
            raise RuntimeError(f'Damped barrier line search failed: merit={merit}')
        x, nu, slack, lam = xn, nn, sn, ln
    raise RuntimeError(f'Damped barrier iteration limit: primal={primal}, stationarity={abs(rd).max()}, gap={gap}')


def replay_or_recover(index, hour, state_path, stage, previous_stage):
    path = Path(stage) / f'hour-{hour:04d}.npz'
    p = None
    if path.exists():
        p = base.hour_problem(index, hour, state_path)
        with np.load(path) as z:
            r = {k: z[k] for k in ['x', 'nu', 'slack', 'lam']}
        method = 'replayed_parent_partial_witness'
    else:
        try:
            return ORIGINAL_FORWARD(index, hour, state_path, stage, previous_stage)
        except (RuntimeError, ValueError, FloatingPointError) as exc:
            p = base.hour_problem(index, hour, state_path)
            previous = None
            if previous_stage:
                with np.load(Path(previous_stage) / f'hour-{hour:04d}.npz') as z:
                    previous = {k: z[k] for k in ['x', 'nu', 'slack', 'lam']}
            r = damped_solve(p['cost'], p, previous)
            method = 'damped_barrier_recovery: ' + str(exc)
    _, _, rd, rp, ri, _, _ = residual(p['cost'], p['E'], p['b'], p['G'], p['h'], r['x'], r['nu'], r['slack'], r['lam'], 0)
    primal = max(float(abs(rp).max(initial=0)), float(np.maximum(p['G'] @ r['x'] - p['h'], 0).max(initial=0)), float(abs(ri).max(initial=0)))
    gap = float(r['slack'] @ r['lam'])
    if primal > 2e-10 or abs(rd).max(initial=0) > 2e-9 or gap > 1e-8 or min(r['slack'].min(), r['lam'].min()) <= 0:
        raise ValueError('Recovered/replayed witness fails unchanged precision gates')
    sealed, _, A, _, _ = base.STATE
    full = np.zeros(A.shape[1])
    full[p['active']], full[p['fixed']] = r['x'], p['fixed_values']
    if abs(p['equality'] @ r['x'] - p['full_b']).max(initial=0) * 1000 > 1e-4:
        raise ValueError('Original full physical equality failed')
    nu = np.zeros(len(p['full_b']))
    nu[p['equality_rows']] = r['nu']
    certificate = dict(primal_mw=primal * 1000, stationarity_eur_mwh=float(abs(rd).max(initial=0)), complementarity_eur=gap * 1000)
    if not path.exists():
        temporary = path.with_suffix('.tmp.npz')
        np.savez(temporary, **{k: r[k] for k in ['x', 'nu', 'slack', 'lam']})
        os.replace(temporary, path)
    return index, -nu[:sealed['nz']], full, certificate, r.get('iterations', 0), r.get('seconds', 0.), method


def pilot():
    design, hours, initial, active = base.setup()
    hour = 567
    state_path = PARENT / 'iteration-020/parameters.npy'
    p = base.hour_problem(hour, hour, str(state_path))
    with np.load(PARENT / f'iteration-019/hour-{hour:04d}.npz') as z:
        previous = {k: z[k] for k in ['x', 'nu', 'slack', 'lam']}
    r = damped_solve(p['cost'], p, previous)
    r['problem'] = p
    rng = np.random.default_rng(568)
    gx = rng.normal(size=base.STATE[2].shape[1]) / 100
    gp = rng.normal(size=base.STATE[0]['nz']) / 40
    gradient = base.backward(r, gx, gp)[:, base.FIELDS]
    direction = rng.normal(size=gradient.shape) * active[hour, :, None]
    wanted = float((gradient * direction).sum())
    theta = np.load(state_path)
    OUT.mkdir(exist_ok=True)
    eps = .0001
    objectives = []
    for sign in [-1, 1]:
        state = theta.copy()
        state[hour] += sign * eps * direction
        path = OUT / ('pilot-minus.npy' if sign < 0 else 'pilot-plus.npy')
        np.save(path, state)
        pp = base.hour_problem(hour, hour, str(path))
        rr = damped_solve(pp['cost'], pp, r)
        full = np.zeros(base.STATE[2].shape[1])
        full[pp['active']], full[pp['fixed']] = rr['x'], pp['fixed_values']
        nu = np.zeros(len(pp['full_b']))
        nu[pp['equality_rows']] = rr['nu']
        objectives.append(float(full @ gx - nu[:len(gp)] @ gp))
    finite = (objectives[1] - objectives[0]) / (2 * eps)
    error = abs(finite - wanted) / max(1., abs(finite), abs(wanted))
    record = dict(status='passed' if error <= .001 else 'failed', hour=hour, utc='2025-01-24T15:00:00Z',
        certificate=r['certificate'], iterations=r['iterations'], backtracks=r['backtracks'], seconds=r['seconds'],
        gradient=dict(epsilon=eps, finite_difference=finite, adjoint=wanted, scaled_discrepancy=error),
        controller_sha256=base.digest(Path(__file__)), parent_parameter_sha256=base.digest(state_path))
    base.atomic_json(OUT / 'recovery-pilot.json', record)
    print(json.dumps(record, indent=2))
    if error > .001:
        raise ValueError('Recovery pilot gradient failed unchanged local gate')


def prepare():
    OUT.mkdir(exist_ok=True)
    if (OUT / 'provenance.json').exists():
        return
    parent_config = json.loads(base.PLAN.read_text())
    design = json.loads(PLAN.read_text())
    for key, value in parent_config.items():
        if key != 'name' and design[key] != value:
            raise ValueError('Recovery changed economic/training specification: ' + key)
    history = json.loads((PARENT / 'history.json').read_text())
    if history[-1]['iteration'] != 19 or not (PARENT / 'failure.json').exists():
        raise ValueError('Expected preserved failed iteration20 checkpoint')
    with np.load(PARENT / 'resume.npz') as z:
        if int(z['step']) != 20:
            raise ValueError('Unexpected Adam resume iteration')
        np.testing.assert_array_equal(z['theta'], np.load(PARENT / 'iteration-020/parameters.npy'))
    # Hardlinks preserve immutable parent evidence without duplicating bulk data.
    for folder in sorted(PARENT.glob('iteration-*')):
        target = OUT / folder.name
        target.mkdir(exist_ok=True)
        for path in folder.iterdir():
            if path.is_file() and not (target / path.name).exists():
                os.link(path, target / path.name)
    for name in ['history.json', 'resume.npz', 'best-parameters.npy', 'initial.npy', 'hours.npy', 'pilot.json']:
        if not (OUT / name).exists():
            os.link(PARENT / name, OUT / name)
    progress = json.loads((PARENT / 'progress.json').read_text())
    ancestry = dict(parent=str(PARENT.relative_to(base.ROOT)), resumed_iteration=20, reused_partial_hours=743,
        original_observed_loop_seconds_lower_bound=max(history[-1]['elapsed_seconds'], progress['elapsed_seconds']),
        changes='Damped Newton/barrier recovery only; original objective, optimizer, parameters, source data and acceptance gates unchanged',
        sha256={name: base.digest(PARENT / name) for name in ['provenance.json', 'history.json', 'resume.npz', 'failure.json', 'iteration-020/parameters.npy']})
    base.atomic_json(OUT / 'ancestry.json', ancestry)


def prepare_and_run():
    if not PLAN.exists():
        raise RuntimeError('Declare fresh numerical-recovery configuration first')
    design = json.loads(PLAN.read_text())
    if design['recovery_controller_sha256'] != base.digest(Path(__file__)):
        raise ValueError('Changed recovery controller')
    pilot = json.loads((OUT / 'recovery-pilot.json').read_text())
    if pilot['status'] != 'passed' or pilot['controller_sha256'] != base.digest(Path(__file__)):
        raise ValueError('Run current recovery pilot first')
    prepare()
    base.OUT, base.PLAN, base.forward_job = OUT, PLAN, replay_or_recover
    base.run()
    if base.digest(Path(__file__)) != design['recovery_controller_sha256']:
        raise ValueError('Recovery controller changed during execution')
    base.atomic_json(OUT / 'recovery-completion.json', dict(status='same_objective_and_gates_recovery_completed',
        summary_sha256=base.digest(OUT / 'summary.json'), controller_sha256=base.digest(Path(__file__)),
        ancestry_sha256=base.digest(OUT / 'ancestry.json')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pilot', action='store_true')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (5 * 1024 ** 3,) * 2)
    try:
        if args.pilot:
            pilot()
        else:
            prepare_and_run()
    except Exception:
        import traceback
        OUT.mkdir(exist_ok=True)
        base.atomic_json(OUT / 'failure.json', dict(traceback=traceback.format_exc()))
        raise
