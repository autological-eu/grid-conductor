"""Fresh twelve-month 100-update study; exact monthly means for prediction."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
import run_independent_hourly_transport_2025 as parent
from independent_hourly_transport_2025 import initialize, penalties, economic_nodes
from monthly_mean_forward_2025 import monthly_mean, audit_score
from forward_hourly_splines_2025 import month_hours
from sigmoid_month_pairs_2025 import ROOT, digest
from run_differentiable_spline_2025 import atomic_json, targets, fixed_month
from run_supply_knots_lp_2025 import joint_loss

OUT = ROOT/'data/bidding-zone-network-2025/monthly-mean-forward-100-v1'
PLAN = ROOT/'config/monthly-mean-forward-100-2025.json'


def save_fast(path, **values):
    temporary = path.with_suffix('.tmp.npz')
    with temporary.open('wb') as f:
        np.savez(f, **values)
    os.replace(temporary, path)


def sources(base):
    pinned = parent.provenance(base)
    for p in [PLAN, Path(__file__), ROOT/'tools/monthly_mean_forward_2025.py',
              ROOT/'tools/test_monthly_mean_forward_2025.py',
              ROOT/'tools/report_monthly_mean_forward_100_2025.py',
              ROOT/'tools/forward_learning_curves_2025.py']:
        pinned[str(p.relative_to(ROOT))] = digest(p)
    return pinned


def pilot(state, market):
    s, d, _, _, _ = state
    h = np.array([15, 111, 318, 567, 759, 815, 900])
    theta, active = initialize(s, d, h)
    theta += .03*np.random.default_rng(251).normal(size=theta.shape)*active[:, :, None]
    r = market.solve(theta, h, tolerance=1e-11)
    rng = np.random.default_rng(19)
    gq = rng.normal(size=r['quantities_gw'].shape); gp = rng.normal(size=r['prices'].shape)
    gp[:, ~np.isfinite(d['observed_prices']).all(axis=0)] = 0
    grad, info = market.backward(theta, r, gq, gp)
    if info['unidentified_rhs_max'] > 1e-8:
        raise ValueError('Unidentified pilot price target')
    checks = []
    for seed in [13, 23, 47]:
        direction = np.random.default_rng(seed).normal(size=theta.shape)*active[:, :, None]
        exact = float((grad*direction).sum())
        eps = 3e-6; values = []
        for sign in [1, -1]:
            rr = market.solve(theta+sign*eps*direction, h, p0=r['prices'], tolerance=1e-11)
            values.append(float((rr['quantities_gw']*gq).sum()+(rr['prices']*gp).sum()))
        finite = (values[0]-values[1])/(2*eps)
        error = abs(finite-exact)/max(1, abs(finite), abs(exact))
        if error >= .001:
            raise ValueError('Pilot gradient error: '+str(error))
        checks.append(dict(seed=seed, exact=exact, finite=finite, scaled_error=error))
    raw, support = monthly_mean(theta, d['capacity'][h], initialize(s, d, h)[0][0])
    curve = economic_nodes(theta); independently = economic_nodes(initialize(s, d, h)[0][0])
    for g in range(market.ng):
        present = d['capacity'][h, g] > 0
        if present.any():
            independently[g] = sum(curve[t, g] for t in np.flatnonzero(present))/present.sum()
    np.testing.assert_allclose(economic_nodes(raw), independently, atol=1e-10, rtol=0)
    return dict(status='passed', hours=h.tolist(), gradients=checks, certificate=r['certificate'],
                mean_node_error=float(abs(economic_nodes(raw)-independently).max()))


def fit_month(base, state, market, plan, month):
    s, d, A, _, capacity = state; design = plan['optimizer']
    folder = OUT/f'month-{month:02d}'; folder.mkdir(exist_ok=True)
    if (folder/'complete.json').exists():
        return
    hours = month_hours(month); future = month_hours(month+1) if month < 12 else None
    initial, active = initialize(s, d, hours); theta = initial.copy()
    m = np.zeros_like(theta); v = m.copy(); p0 = fp0 = None; start = 0
    journal = folder/'resume.npz'
    if journal.exists():
        with np.load(journal) as z:
            theta, m, v = z['theta'], z['m'], z['v']; start = int(z['step']); p0 = z['p0']
            fp0 = z['fp0'] if month < 12 else None
        if start and not (folder/f'{start-1:03d}.json').exists():
            raise ValueError('Incomplete journal commit; inspect before resuming')
    target = targets(d, hours, month)
    target['prices'][:, ~np.isfinite(d['observed_prices']).all(axis=0)] = np.nan
    fixed = fixed_month(s, d, hours); zero = np.zeros((market.ng, 10))
    for step in range(start, 101):
        began = time.perf_counter()
        if shutil.disk_usage(OUT).free < 2*1024**3:
            raise RuntimeError('Less than 2 GiB workspace headroom; no automatic deletion')
        atomic_json(OUT/'progress.json', dict(stage='fitting', month=month, iteration=step,
                    updates=100, months=12, pid=os.getpid(), updated_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())))
        r = market.solve(theta, hours, p0=p0)
        values = np.zeros((len(hours), A.shape[1])); values[:, :market.ng] = r['quantities_gw']
        loss, gx, gp, _, parts = joint_loss(s, d, capacity, design, zero, zero, r['prices'], values,
                                           hours, len(hours), target, fixed)
        reg, direct, regparts = penalties(theta, initial, active, design)
        backward_seconds = 0.; gradinfo = None; gradient = None
        if step < 100:
            b = time.perf_counter(); hourly, gradinfo = market.backward(theta, r, gx[:, :market.ng], gp)
            if gradinfo['unidentified_rhs_max'] > 1e-8:
                raise ValueError('Observed target materially projects onto unidentified price direction')
            gradient = (hourly+direct)*active[:, :, None]
            if not np.isfinite(gradient).all():
                raise ValueError('Nonfinite gradient')
            backward_seconds = time.perf_counter()-b
        b = time.perf_counter(); profile, support = monthly_mean(theta, d['capacity'][hours], initial[0])
        np.testing.assert_array_equal(theta[~active], initial[~active])
        # Separate straightforward reduction audits the exported monthly mean.
        actual_nodes = economic_nodes(theta); expected = economic_nodes(initial[0]).copy()
        for g in range(market.ng):
            present = d['capacity'][hours, g] > 0
            if present.any():
                expected[g] = np.add.reduce(actual_nodes[present, g], axis=0)/present.sum()
        mean_error = float(abs(economic_nodes(profile)-expected).max())
        if mean_error > 1e-10:
            raise ValueError('Monthly mean function replay failed')
        within, gen = audit_score(state, market, theta, r, month)
        rr = forward = fg = None
        if month < 12:
            # Broadcast explicitly to preserve prior-equilibrium warm starts in the
            # robust solver; the same single monthly function applies to every hour.
            raw = np.broadcast_to(profile, (len(future), *profile.shape))
            rr = market.solve(raw, future, p0=fp0)
            forward, fg = audit_score(state, market, raw, rr, month+1)
        profile_path = folder/f'{step:03d}-profile.npz'
        base.save(profile_path, theta=profile, support=support)
        # Compact hourly prices and generation totals retained at EVERY state.
        scores_path = folder/f'{step:03d}-scores.npz'
        compact = dict(training_hours=hours, training_prices=r['prices'],
                       training_generation_twh=np.array(within['monthly_generation_twh']))
        if forward:
            compact.update(validation_hours=future, validation_prices=rr['prices'],
                           validation_generation_twh=np.array(forward['monthly_generation_twh']))
        base.save(scores_path, **compact)
        if step % 10 == 0:
            base.save(folder/f'{step:03d}-parameters.npz', theta=theta)
        if step in [0, 100]:
            for kind, res, generated in [('within', r, gen), ('forward', rr, fg)]:
                if res is not None:
                    base.save(folder/f'{step:03d}-{kind}.npz', hours=res['hours'], prices=res['prices'],
                              quantities_gw=res['quantities_gw'], flows_gw=res['flows_gw'], generation=generated)
        row = dict(month=month, iteration=step, training_hours=len(hours), training_zone_mae=within['zone_mae'],
                   validation_hours=len(future) if future is not None else None,
                   validation_zone_mae=forward['zone_mae'] if forward else None,
                   within=within, forward=forward, loss=loss+reg, **parts, **regparts,
                   gradient_identification=gradinfo, backward_seconds=backward_seconds,
                   mean_node_replay_error_eur_mwh=mean_error,
                   audit_prediction_export_seconds=time.perf_counter()-b,
                   profile_sha256=digest(profile_path), scores_sha256=digest(scores_path),
                   parameter_checkpoint=step % 10 == 0)
        # The score is for state step AFTER exactly step parameter updates.
        if step < 100:
            m = .9*m+.1*gradient; v = .999*v+.001*gradient**2; t = step+1
            theta -= design['learning_rate']*(m/(1-.9**t))/(np.sqrt(v/(1-.999**t))+1e-8)
            theta[~active] = initial[~active]
        row['wall_seconds'] = time.perf_counter()-began
        atomic_json(folder/f'{step:03d}.json', row)
        save_fast(journal, theta=theta, m=m, v=v, step=step+1, p0=r['prices'],
                  fp0=rr['prices'] if rr is not None else np.empty((0, market.nz)))
        p0 = r['prices']; fp0 = rr['prices'] if rr is not None else None
        print('FIT', month, step, 'TRAIN', within['metrics']['price_mae'],
              'FORWARD', forward['metrics']['price_mae'] if forward else None, 'SECONDS', row['wall_seconds'], flush=True)
        if step % 5 == 0 or step == 100:
            from report_monthly_mean_forward_100_2025 import report
            report(OUT, s, d, final=False)
    atomic_json(folder/'complete.json', dict(month=month, updates=100, score_points=101))
    journal.unlink()


def run():
    OUT.mkdir(exist_ok=True)
    lock = (OUT/'job.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (OUT/'complete.json').exists() or (OUT/'failure.json').exists():
        raise ValueError('Inspect completed/failed study; no silent rerun')
    base, (state, market, network, _) = parent.setup()
    if parent.provenance(base) != json.loads((parent.OUT/'provenance.json').read_text()):
        raise ValueError('Parent source provenance changed')
    pinned = sources(base)
    if (OUT/'provenance.json').exists() and json.loads((OUT/'provenance.json').read_text()) != pinned:
        raise ValueError('Changed source; fresh root required')
    atomic_json(OUT/'provenance.json', pinned); atomic_json(OUT/'network.json', network)
    if not (OUT/'pilot.json').exists():
        atomic_json(OUT/'pilot.json', pilot(state, market))
    plan = json.loads(PLAN.read_text())
    for month in range(1, 13):
        fit_month(base, state, market, plan, month)
    if sources(base) != pinned:
        raise ValueError('Sources changed during study')
    from report_monthly_mean_forward_100_2025 import report
    report(OUT, state[0], state[1], final=True)
    atomic_json(OUT/'complete.json', dict(status='100_updates_all_12_months_fast_solver_complete',
                physical_verification='pending; no coupled-network adoption claim', scores_sha256=digest(OUT/'scores.json')))
    atomic_json(OUT/'progress.json', dict(stage='complete', months=12, updates=100, points=1212))


if __name__ == '__main__':
    try:
        run()
    except Exception:
        OUT.mkdir(exist_ok=True)
        atomic_json(OUT/'failure.json', dict(traceback=traceback.format_exc()))
        raise
