"""Full-February bid-resolution sensitivity; frozen neutral/selected curves."""
import fcntl
import json
import traceback
from pathlib import Path
import numpy as np
import run_fast_fit_physical_transfer_2025 as study
from transport_curve_physical_transfer_2025 import clear
from report_fast_fit_physical_transfer_2025 import physical_replay
from sigmoid_month_pairs_2025 import ROOT, digest, metric
from forward_hourly_splines_2025 import month_hours
from supply_knot_network_2025 import generation
from run_differentiable_spline_2025 import atomic_json

OUT = study.OUT/'refined-physical'


def run():
    OUT.mkdir(exist_ok=True)
    lock = (OUT/'job.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert not (OUT/'summary.json').exists(), 'Refinement already complete'
    assert not (OUT/'failure.json').exists(), 'Inspect failed refinement first'
    base = study.setup_controller()
    assert base.provenance() == json.loads((study.OUT/'provenance.json').read_text())
    parent = json.loads((study.OUT/'transfer-summary.json').read_text())
    selected = parent['selected_iteration']
    paths = [Path(__file__), ROOT/'tools/transport_curve_physical_transfer_2025.py',
             ROOT/'tools/report_fast_fit_physical_transfer_2025.py',
             study.OUT/'provenance.json', study.OUT/'transfer-summary.json',
             study.OUT/f'iteration-{selected:03d}/shared-parameters.npy',
             study.OUT/'iteration-000/shared-parameters.npy']
    pinned = {str(p.relative_to(ROOT)):digest(p) for p in paths}
    if (OUT/'provenance.json').exists():
        assert json.loads((OUT/'provenance.json').read_text()) == pinned
    atomic_json(OUT/'provenance.json', pinned)
    state, market, _, _ = base.setup(); source, data, _, _, capacity = state
    hours = month_hours(2); cases = []
    for step in [0, selected]:
        path = OUT/f'february-{step:03d}.npz'
        if path.exists():
            record = json.loads(path.with_suffix('.json').read_text())
            assert record['witness_sha256'] == digest(path)
            cases.append(record); continue
        theta_path = study.OUT/f'iteration-{step:03d}/shared-parameters.npy'
        theta = np.load(theta_path)
        def progress(done, total):
            atomic_json(OUT/'progress.json', dict(stage='full-February-100-tranche-physical',
                        iteration=step, done=done, hours=total, zones=48))
        witness, info = clear(state, market, theta, hours, bins=100, progress=progress)
        generated = generation(source, data, capacity, witness['quantities_gw']*1000, hours)
        score, monthly = metric(source, data, witness['prices'], generated, hours, 2)
        witness['generation'] = generated
        base.save(path, **witness)
        check, audited = physical_replay(state, market, theta, path, 100, month=2)
        for key in ['price_mae','generation_mae_twh','generation_normalized_mae']:
            np.testing.assert_allclose(audited[key], score[key], atol=1e-9, rtol=0)
        record = dict(iteration=step, hours=len(hours), bins=100, metrics=score,
                      monthly_generation_twh=monthly.tolist(), info=info, audit=check,
                      parameter_sha256=digest(theta_path), witness_sha256=digest(path))
        atomic_json(path.with_suffix('.json'), record); cases.append(record)
        print('REFINED_PHYSICAL', step, score, info, flush=True)
    assert pinned == {str(p.relative_to(ROOT)):digest(p) for p in paths}
    atomic_json(OUT/'summary.json', dict(status='full_february_refinement_and_independent_replay_complete',
                hours_per_case=672,zones=48,bins=100,cases=cases,provenance_sha256=digest(OUT/'provenance.json')))
    atomic_json(OUT/'progress.json', dict(stage='full-February-refinement-and-audit-complete'))


if __name__ == '__main__':
    try:
        run()
    except Exception:
        OUT.mkdir(exist_ok=True)
        atomic_json(OUT/'failure.json', dict(traceback=traceback.format_exc()))
        raise
