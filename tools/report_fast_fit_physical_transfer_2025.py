"""Independent curve-cost/constraint replay and fast-to-physical comparison."""
import csv
import json
from pathlib import Path
import numpy as np
from scipy.sparse import hstack
import run_fast_fit_physical_transfer_2025 as study
from monthly_diurnal_splines_2025 import labels, expand
from sigmoid_month_pairs_2025 import ROOT, digest, metric, certify
from supply_knot_network_2025 import generation
from report_batched_transport_2025 import replay
from run_differentiable_spline_2025 import atomic_json


def integrated_bids(market, theta, hours, groups, bins):
    """Independent quadratic primitives, not producer midpoint interpolation."""
    raw = expand(theta, labels(groups, hours))
    increments = .001 + 20*np.logaddexp(0, raw[..., 1:])
    nodes = np.concatenate([np.zeros((*raw.shape[:2], 1)), np.cumsum(increments, axis=-1)], axis=-1)
    center = (nodes[..., 2] + nodes[..., 3]) / 2
    anchors = market.source[hours, :, None] + 80*np.tanh(raw[..., 0, None]/4) + nodes - center[..., None]
    anchors += .01*np.linspace(0, 1, 6)
    anchors[:, market.zero] = .01*np.linspace(0, 1, 6)
    u = np.linspace(0, 1, bins+1)
    k = np.minimum((u*5).astype(int), 4)
    z = u-k*.2
    slope = np.diff(anchors, axis=-1)/.2
    areas = .1*(anchors[..., :-1]+anchors[..., 1:])
    prefix = np.concatenate([np.zeros((*areas.shape[:2], 1)), np.cumsum(areas, axis=-1)], axis=-1)
    primitive = prefix[..., k]+anchors[..., k]*z+.5*slope[..., k]*z*z
    return np.diff(primitive, axis=-1)*bins


def physical_replay(state, market, theta, path, bins, month=None):
    source, data, original, _, capacity = state
    with np.load(path) as z:
        witness = {k:z[k] for k in z.files}
    hours = witness['hours']; count = len(source['groups']); ng = count*bins
    matrix = hstack([original[:, np.repeat(np.arange(count), bins)], original[:, count:]], format='csc')
    costs = integrated_bids(market, theta, hours, source['groups'], bins).reshape(len(hours), ng)
    available = np.repeat(data['capacity'][hours]/bins, bins, axis=1)
    checks = certify(matrix, costs, available, data, hours, witness['values'],
                     witness['row_duals'], witness['objectives'], ng, source['nl'], source['nz'])
    q = witness['values'][:, :ng].reshape(len(hours), count, bins).sum(axis=2)
    np.testing.assert_allclose(q, witness['quantities_gw']*1000, atol=1e-7, rtol=0)
    np.testing.assert_array_equal(witness['prices'], witness['row_duals'][:, :48])
    generated = generation(source, data, capacity, q, hours)
    if 'generation' in witness:
        np.testing.assert_allclose(generated, witness['generation'], atol=1e-7, rtol=0)
    score = None
    if month is not None:
        score, _ = metric(source, data, witness['prices'], generated, hours, month)
    return dict(hours=len(hours), bins=bins, certificate=checks, witness_sha256=digest(path)), score


def run():
    out = study.OUT
    assert not (out/'failure.json').exists()
    base = study.setup_controller()
    assert base.provenance() == json.loads((out/'provenance.json').read_text())
    summary = json.loads((out/'transfer-summary.json').read_text())
    history = json.loads((out/'history.json').read_text())
    assert digest(out/'history.json') == summary['history_sha256']
    best = float('inf'); stale = 0; selected = None
    for i, row in enumerate(history):
        improved = row['forward']['metrics']['price_mae'] < best-1e-6
        if improved:
            best = row['forward']['metrics']['price_mae']; selected = i; stale = 0
        else:
            stale += 1
        assert row['improved'] == improved and row['stale'] == stale
        assert stale < 3 or i == len(history)-1
    assert stale == 3 and selected == summary['selected_iteration']
    state, market, _, _ = base.setup()
    source, data, _, _, _ = state
    checks = []
    for step in sorted({0, selected, len(history)-1}):
        theta = np.load(out/f'iteration-{step:03d}/shared-parameters.npy')
        assert digest(out/f'iteration-{step:03d}/shared-parameters.npy') == history[step]['parameter_sha256']
        for kind, month in [('within', 1), ('forward', 2)]:
            path = out/f'iteration-{step:03d}/{kind}.npz'
            check, _, _, score = replay(state, market, path, theta, month)
            assert check['witness_sha256'] == history[step][kind+'_sha256']
            for name in ['price_mae', 'generation_mae_twh', 'generation_normalized_mae']:
                np.testing.assert_allclose(score[name], history[step][kind]['metrics'][name], atol=1e-9, rtol=0)
            checks.append(dict(model='fast', iteration=step, kind=kind, **check))
    for case in summary['cases']:
        step, month = case['iteration'], case['month']
        theta = np.load(out/f'iteration-{step:03d}/shared-parameters.npy')
        assert digest(out/f'iteration-{step:03d}/shared-parameters.npy') == case['parameter_sha256']
        path = out/f'physical-{step:03d}-{month:02d}.npz'
        check, score = physical_replay(state, market, theta, path, 20, month)
        assert check['witness_sha256'] == case['witness_sha256']
        for name in ['price_mae', 'generation_mae_twh', 'generation_normalized_mae']:
            np.testing.assert_allclose(score[name], case['metrics'][name], atol=1e-9, rtol=0)
        checks.append(dict(model='physical', iteration=step, month=month, **check))
    theta = np.load(out/f'iteration-{selected:03d}/shared-parameters.npy')
    probe, _ = physical_replay(state, market, theta, out/'physical-fine-probe.npz', 100)
    assert probe['witness_sha256'] == summary['discretization_probe']['witness_sha256']
    checks.append(dict(model='physical-fine', **probe))
    audit = dict(status='passed_fast_fit_physical_transfer_replay', selected_iteration=selected,
                 last_iteration=len(history)-1, witness_hours=sum(c['hours'] for c in checks),
                 cases=checks, history_sha256=digest(out/'history.json'),
                 summary_sha256=digest(out/'transfer-summary.json'), producer_sha256=digest(__file__))
    atomic_json(out/'transfer-audit.json', audit)
    report(summary, history, audit, state)
    atomic_json(out/'progress.json', dict(stage='patience-fit-physical-transfer-and-audit-complete',
                selected_iteration=selected, last_iteration=len(history)-1, witness_hours=audit['witness_hours']))
    print(json.dumps({k:v for k,v in audit.items() if k!='cases'}))


def report(summary, history, audit, state):
    out = study.OUT; selected = summary['selected_iteration']; last = len(history)-1
    assets = ROOT/'research/assets'
    with (assets/'fast-fit-physical-transfer-iterations-2025.csv').open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['iteration','jan_mae','feb_mae','feb_mix_twh','stale','improved','core_seconds','inherited'])
        for r in history:
            w.writerow([r['iteration'], r['within']['metrics']['price_mae'], r['forward']['metrics']['price_mae'],
                        r['forward']['metrics']['generation_mae_twh'],r['stale'],r['improved'],
                        r['forward_seconds']+r['backward_seconds']+r['prediction_seconds'],r['iteration']<=3])
    rows = []
    for step, label in [(0,'Neutral'),(selected,'Selected')]:
        for month, kind in [(1,'within'),(2,'forward')]:
            fast = history[step][kind]['metrics']
            physical = next(c for c in summary['cases'] if c['iteration']==step and c['month']==month)
            rows.append(f"|{label} ({step})|{'January fit' if month==1 else 'February validation'}|{fast['price_mae']:.3f}|{physical['metrics']['price_mae']:.3f}|{fast['generation_mae_twh']:.4f}|{physical['metrics']['generation_mae_twh']:.4f}|{physical['info']['seconds']:.2f}|")
    comparisons = summary['discretization_probe']['comparisons']
    worst_price = max(c['price_max_difference'] for c in comparisons)
    worst_quantity = max(c['quantity_max_difference_mw'] for c in comparisons)
    times = [r['forward_seconds']+r['backward_seconds']+r['prediction_seconds'] for r in history[4:]]
    physical_neutral = next(c for c in summary['cases'] if c['iteration']==0 and c['month']==2)
    physical_selected = next(c for c in summary['cases'] if c['iteration']==selected and c['month']==2)
    delta = physical_selected['metrics']['price_mae']-physical_neutral['metrics']['price_mae']
    text = f'''# Fit fast, evaluate with coupled physical constraints — 2025

Full January fitting (744 hours) and full February validation (672 hours) retain
all 48 existing modeled areas. Fast fitting stops after three consecutive
February price-MAE nonimprovements of at least 1e-6 EUR/MWh. It selects update
**{selected}** and stops at **{last}**. The learned offers are then frozen and
dispatched with the original combined physical network, without further fitting.

The physical-network February MAE changes by **{delta:+.3f} EUR/MWh** when using
selected rather than neutral curves. Compare the physical column within the
table; comparing fast with physical also changes the network model.

| Curves (update) | Month | Fast price MAE | Physical price MAE | Fast mix MAE TWh | Physical mix MAE TWh | Physical seconds |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

Price MAE uses the same 41 annual-complete hourly ENTSO-E zones. Generation MAE
uses 243 observed monthly country/family Ember cells per month, not fabricated
hourly generation targets. Actual hourly demand, availability, fuel/source costs,
allocation rules and the fixed hydro schedule are unchanged.

## Fitting and stopping

Continue the exact parameters and Adam state from the previous three-update
experiment. Updates 0–3 and the neutral annual witness are inherited, not rerun.
Each later update solves all January hours, differentiates the full-month price
and generation loss, then predicts every February hour with February's own
physical inputs. Parameters have 24 shared local-hour curves per technology/zone;
they are not independent calendar-hour fits. Zero-economic-bid renewables remain
frozen. Shrinkage, daily smoothing and learning rate are unchanged.

New core fitting/gradient/prediction phases take **{min(times):.2f}–{max(times):.2f}s**
per update, excluding source loading, checkpoint/metric overhead and this audit.
February targets select the best update and stopping time. They are not used
in gradients, but this is validation for model selection, not an untouched test
or a full-year fitted score. No iteration-budget exit is reported as convergence.

## What transfers, and what changes

Transfer the six learned monotone offer nodes at 0/20/40/60/80/100% available MW,
with the same hourly source anchors and small technical slope. Do not reinterpret
those parameters as the previous cubic-spline family. The constrained LP uses
20 equal supply tranches per technology; each price is the exact integral average
of the learned piecewise-linear marginal offer over that tranche. Integrated
cost at tranche boundaries is preserved. Within-tranche dispatch is an explicit
approximation; the fast inverse-response smoothing is also absent from this LP.

Restore all original PTDF, AC-island and internal-line constraints, signed native
links, load/island right-hand sides and physical flow offsets. The fast model's
quadratic corridor transport cost is removed. No emergency supply is included.
Native LP witnesses pass the original 1e-4 MW feasibility, 0.05 EUR duality-gap/
complementarity and 1e-5 EUR/MWh free-reduced-cost gates. This is the original
physical constraint system with new bids, not a native PyPSA objective-match claim.

A matched {len(comparisons)}-hour check increases bids from 20 to 100 tranches.
The largest observed-zone price difference is **{worst_price:.4f} EUR/MWh**;
the largest technology-quantity difference is **{worst_quantity:.2f} MW**.
This is a discretization sensitivity check, not a full-month convergence proof.
It does not isolate every effect of removing inverse smoothing.

## Verification, scope and next use

Two export tests check exact integrated cost, monotonicity, zero-bid convention
and actual-hour identity. A seven-European-hour physical pilot passes before
training. An independent implementation integrates piecewise quadratic costs
from raw parameters, reconstructs physical matrices/bounds and replays prices,
quantities, objectives, dual certificates and observed metrics. The independent
fast response replay covers initial, selected and final proposals. Together,
**{audit['witness_hours']:,} witness hours** are checked.

All results/optimizer states remain local and ignored under
`data/bidding-zone-network-2025/fast-fit-physical-transfer-v1`. Producers,
configuration and input/result hashes are sealed there. The report is generated
by `tools/report_fast_fit_physical_transfer_2025.py`. The prior study's sources
are unchanged. No baseline promotion, website publication, annual fitted
acceptance or dynamic-storage capability is implied.

[Full iteration history](assets/fast-fit-physical-transfer-iterations-2025.csv)
'''
    (ROOT/'research/fast-fit-physical-transfer-2025.md').write_text(text)


if __name__ == '__main__':
    run()
