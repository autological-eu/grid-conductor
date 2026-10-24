"""Patience-stopped fast training, then frozen-curve original-physics replay."""
import fcntl
import json
import shutil
import traceback
from pathlib import Path
import numpy as np
import run_batched_transport_fit_2025 as previous
from sigmoid_month_pairs_2025 import ROOT, digest, metric
from supply_knot_network_2025 import generation
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json
from transport_curve_physical_transfer_2025 import clear

PARENT = previous.OUT
OUT = ROOT / 'data/bidding-zone-network-2025/fast-fit-physical-transfer-v1'
PLAN = ROOT / 'config/fast-fit-physical-transfer-2025.json'


def setup_controller():
    base = previous.configure()
    base.OUT = OUT
    base.PLAN = PLAN
    before = base.provenance
    def provenance():
        result = before()
        paths = [Path(__file__), PLAN, ROOT/'tools/transport_curve_physical_transfer_2025.py',
                 ROOT/'tools/test_transport_curve_transfer_2025.py',
                 PARENT/'provenance.json', PARENT/'history.json', PARENT/'resume.npz',
                 OUT/'physical-pilot.json', ROOT/'tools/pilot_fast_fit_physical_transfer_2025.py']
        result.update({str(p.relative_to(ROOT)): digest(p) for p in paths})
        return result
    base.provenance = provenance
    return base


def prepare():
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'failure.json').exists(), 'Inspect failed study before resuming'
    pilot = json.loads((OUT/'physical-pilot.json').read_text())
    assert pilot['status'] == 'passed'
    assert all(digest(ROOT/p) == sha for p, sha in pilot['sources'].items())
    history = json.loads((PARENT/'history.json').read_text())
    assert len(history) == 4 and history[-1]['iteration'] == 3
    for name in ['annual.json', 'annual.npz', 'pilot.json', 'history.json', 'resume.npz']:
        if not (OUT/name).exists():
            shutil.copy2(PARENT/name, OUT/name)
    for row in history:
        folder = f"iteration-{row['iteration']:03d}"
        if not (OUT/folder).exists():
            shutil.copytree(PARENT/folder, OUT/folder)
    pilot = json.loads((OUT/'pilot.json').read_text())
    for path in [Path(__file__), PLAN, ROOT/'tools/transport_curve_physical_transfer_2025.py',
                 ROOT/'tools/test_transport_curve_transfer_2025.py']:
        pilot['sources'][str(path.relative_to(ROOT))] = digest(path)
    atomic_json(OUT/'pilot.json', pilot)
    atomic_json(OUT/'inherited.json', dict(source=str(PARENT.relative_to(ROOT)),
                iterations=[0,1,2,3], history_sha256=digest(PARENT/'history.json'),
                resume_sha256=digest(PARENT/'resume.npz'), annual_recomputed=False))


def run():
    OUT.mkdir(exist_ok=True)
    lock = (OUT/'controller.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (OUT/'transfer-summary.json').exists():
        raise ValueError('Already complete; inspect saved results')
    prepare()
    base = setup_controller()
    if not (OUT/'summary.json').exists():
        base.run()
    assert base.provenance() == json.loads((OUT/'provenance.json').read_text())
    summary = json.loads((OUT/'summary.json').read_text())
    assert summary['stop_reason'] == 'forward_patience', 'Budget exit is not convergence'
    history = json.loads((OUT/'history.json').read_text())
    assert history[-1]['stale'] == 3
    selected = summary['best_iteration']
    state, market, _, _ = base.setup()
    source, data, _, _, capacity = state
    cases = []
    for step in sorted({0, selected}):
        folder = OUT/f'iteration-{step:03d}'
        theta = np.load(folder/'shared-parameters.npy')
        assert digest(folder/'shared-parameters.npy') == history[step]['parameter_sha256']
        for month in [1, 2]:
            path = OUT/f'physical-{step:03d}-{month:02d}.npz'
            if path.exists():
                record = json.loads(path.with_suffix('.json').read_text())
                assert digest(path) == record['witness_sha256']
                cases.append(record); continue
            hours = month_hours(month)
            def progress(done, total):
                atomic_json(OUT/'progress.json', dict(stage='original-physical-network-transfer',
                            iteration=step, month=month, done=done, total=total, zones=48))
            witness, info = clear(state, market, theta, hours, bins=20, progress=progress)
            generated = generation(source, data, capacity, witness['quantities_gw']*1000, hours)
            score, monthly = metric(source, data, witness['prices'], generated, hours, month)
            witness['generation'] = generated
            base.save(path, **witness)
            record = dict(iteration=step, month=month, hours=len(hours), metrics=score,
                          monthly_generation_twh=monthly.tolist(), info=info,
                          parameter_sha256=digest(folder/'shared-parameters.npy'), witness_sha256=digest(path))
            atomic_json(path.with_suffix('.json'), record); cases.append(record)
            print('PHYSICAL', step, month, score, info, flush=True)
    probe_hours = np.array([15,111,318,567,759,815,900,1928])
    # March is outside this January→February comparison; retain full-month scope.
    probe_hours = probe_hours[probe_hours < 1416]
    theta = np.load(OUT/f'iteration-{selected:03d}/shared-parameters.npy')
    fine, fine_info = clear(state, market, theta, probe_hours, bins=100)
    base.save(OUT/'physical-fine-probe.npz', **fine)
    comparison = []
    for t, hour in enumerate(probe_hours):
        month = 1 if hour < 744 else 2
        with np.load(OUT/f'physical-{selected:03d}-{month:02d}.npz') as coarse:
            j = int(np.flatnonzero(coarse['hours'] == hour)[0])
            mask = np.isfinite(data['observed_prices']).all(axis=0)
            comparison.append(dict(hour=int(hour), price_max_difference=float(abs(fine['prices'][t,mask]-coarse['prices'][j,mask]).max()),
                                   quantity_max_difference_mw=float(abs(fine['quantities_gw'][t]-coarse['quantities_gw'][j]).max()*1000)))
    atomic_json(OUT/'transfer-summary.json', dict(status='patience_fit_and_original_physical_transfer_complete',
                selected_iteration=selected, last_iteration=history[-1]['iteration'], stop_reason='three_forward_nonimprovements',
                history_sha256=digest(OUT/'history.json'), cases=cases,
                discretization_probe=dict(bins=100,hours=probe_hours.tolist(),info=fine_info,comparisons=comparison,
                    witness_sha256=digest(OUT/'physical-fine-probe.npz')), independent_audit='pending'))
    atomic_json(OUT/'progress.json', dict(stage='fit-and-transfer-complete-awaiting-audit', selected_iteration=selected))


if __name__ == '__main__':
    try:
        run()
    except Exception:
        OUT.mkdir(exist_ok=True)
        atomic_json(OUT/'failure.json', dict(traceback=traceback.format_exc()))
        raise
