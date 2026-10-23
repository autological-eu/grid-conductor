"""European end-to-end adjoint and exact warm-start checks before full training."""
import json
from pathlib import Path
import time
import numpy as np
import hourly_spline_reconstruction_2025 as h
from spline_europe_2025 import backward


def run():
    began = time.perf_counter()
    design, hours, initial, active = h.setup()
    dest = Path('/tmp/grid-hourly-spline-pilot')
    dest.mkdir(exist_ok=True)
    path = dest / 'initial.npy'
    np.save(path, initial)
    cases = []
    for hour in [12, 372, 720]:
        p = h.hour_problem(hour, hour, str(path))
        r = h.warm_solve(p['cost'], p, None)
        rr = h.warm_solve(p['cost'], p, r)
        np.testing.assert_allclose(rr['x'], r['x'], atol=1e-6, rtol=0)
        cases.append(dict(hour=hour, seconds=r['seconds'], iterations=r['iterations'], warm_iterations=rr['iterations'], certificate=r['certificate']))
        if hour != 12:
            continue
        rng = np.random.default_rng(154)
        gx = rng.normal(size=h.STATE[2].shape[1]) / 100
        gp = rng.normal(size=h.STATE[0]['nz']) / 40
        r['problem'] = p
        gradient = backward(r, gx, gp)[:, h.FIELDS]
        direction = rng.normal(size=gradient.shape) * active[hour, :, None]
        wanted = float((gradient * direction).sum())
        # A recorded step sweep found the .0005 direction leaves the local
        # differentiable region. Check the smaller .0001 direction explicitly;
        # retain the larger-step discrepancy in gradient-pilot-sweep.json.
        eps = .0001
        objectives = []
        for sign in [-1, 1]:
            state = initial.copy()
            state[hour] += sign * eps * direction
            perturbed = dest / ('minus.npy' if sign < 0 else 'plus.npy')
            np.save(perturbed, state)
            pp = h.hour_problem(hour, hour, str(perturbed))
            rp = h.warm_solve(pp['cost'], pp, r)
            full = np.zeros(h.STATE[2].shape[1])
            full[pp['active']], full[pp['fixed']] = rp['x'], pp['fixed_values']
            nu = np.zeros(len(pp['full_b']))
            nu[pp['equality_rows']] = rp['nu']
            objectives.append(float(full @ gx + (-nu[:len(gp)]) @ gp))
        finite = (objectives[1] - objectives[0]) / (2 * eps)
        discrepancy = abs(finite - wanted) / max(1., abs(wanted), abs(finite))
        if discrepancy > .001:
            raise ValueError(f'European hourly price/dispatch adjoint mismatch: {finite}, {wanted}, {discrepancy}')
    record = dict(status='passed', cases=cases, gradient=dict(adjoint=wanted, finite_difference=finite, scaled_discrepancy=discrepancy), seconds=time.perf_counter() - began,
        source_sha256=h.digest(Path(h.__file__)), pilot_sha256=h.digest(Path(__file__)))
    h.OUT.mkdir(exist_ok=True)
    h.atomic_json(h.OUT / 'pilot.json', record)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    run()
