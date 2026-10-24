"""Add audited full-month bid-refinement results and per-zone comparison data."""
import csv
import json
from pathlib import Path
import numpy as np
import run_fast_fit_physical_transfer_2025 as study
from sigmoid_month_pairs_2025 import ROOT, digest
from run_differentiable_spline_2025 import atomic_json


def run():
    out = study.OUT; refined = out/'refined-physical'
    assert not (refined/'failure.json').exists()
    summary = json.loads((refined/'summary.json').read_text())
    assert summary['status'] == 'full_february_refinement_and_independent_replay_complete'
    sources = json.loads((refined/'provenance.json').read_text())
    assert all(digest(ROOT/p) == sha for p, sha in sources.items())
    assert digest(refined/'provenance.json') == summary['provenance_sha256']
    audit = json.loads((out/'transfer-audit.json').read_text())
    original = json.loads((out/'transfer-summary.json').read_text())
    assert audit['summary_sha256'] == digest(out/'transfer-summary.json')
    selected = original['selected_iteration']
    for record in summary['cases']:
        path = refined/f"february-{record['iteration']:03d}.npz"
        assert digest(path) == record['witness_sha256'] == record['audit']['witness_sha256']
        pars = out/f"iteration-{record['iteration']:03d}/shared-parameters.npy"
        assert digest(pars) == record['parameter_sha256']
        assert record['hours'] == 672 and record['bins'] == 100
    base = study.setup_controller()
    assert base.provenance() == json.loads((out/'provenance.json').read_text())
    state, _, _, _ = base.setup(); source, data, _, _, _ = state
    arrays = []
    for step in [0, selected]:
        for path in [out/f'iteration-{step:03d}/forward.npz', out/f'physical-{step:03d}-02.npz',
                     refined/f'february-{step:03d}.npz']:
            with np.load(path) as z:
                np.testing.assert_array_equal(z['hours'], np.arange(744,1416))
                arrays.append(z['prices'])
    path = ROOT/'research/assets/fast-fit-physical-transfer-zones-2025.csv'
    complete = np.isfinite(data['observed_prices']).all(axis=0)
    with path.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['zone','february_hours','fast_neutral_mae','physical20_neutral_mae',
                         'physical100_neutral_mae','fast_selected_mae','physical20_selected_mae','physical100_selected_mae'])
        for j in np.flatnonzero(complete):
            observed = data['observed_prices'][744:1416,j]
            writer.writerow([source['zones'][j],672]+[float(abs(p[:,j]-observed).mean()) for p in arrays])
    report = ROOT/'research/fast-fit-physical-transfer-2025.md'
    text = report.read_text().split('\n## Full-February finer-bid check\n')[0]
    text = text.replace('February price-MAE nonimprovements of at least 1e-6 EUR/MWh.',
                        'February price-MAE nonimprovements, using a 1e-6 EUR/MWh improvement threshold.')
    text = text.replace('The physical-network February MAE changes by',
                        'At 20 tranches, the physical-network February MAE changes by')
    text = text.replace('Physical price MAE |', 'Physical (20) price MAE |')
    neutral, fitted = summary['cases']
    assert neutral['iteration'] == 0 and fitted['iteration'] == selected
    change = fitted['metrics']['price_mae']-neutral['metrics']['price_mae']
    improvement = -change/neutral['metrics']['price_mae']*100
    text += f'''
## Full-February finer-bid check

Because individual sampled prices moved materially at finer bid resolution,
repeat **all 672 February hours/all 48 zones** at 100 tranches for both frozen
neutral and selected offers. No refitting or reselection occurs. Each case also
passes independent integrated-cost/physical/metric replay at the original gates.

| Curves | Physical (100) price MAE EUR/MWh | Generation MAE TWh | Forward + certificate seconds |
|---|---:|---:|---:|
|Neutral|{neutral['metrics']['price_mae']:.3f}|{neutral['metrics']['generation_mae_twh']:.4f}|{neutral['info']['seconds']:.2f}|
|Selected ({selected})|{fitted['metrics']['price_mae']:.3f}|{fitted['metrics']['generation_mae_twh']:.4f}|{fitted['info']['seconds']:.2f}|

Finer-resolution physical price MAE improves **{-change:.3f} EUR/MWh
({improvement:.1f}%)**. The fast-trained curves therefore improve this original
physical-network evaluation as well as the fast model. This does not establish
that they are optimal for the physical model, or that the remaining fast/physical
score difference comes solely from network constraints: transport costs, inverse
smoothing and bid discretization also differ. The physical LP remains a declared
discretization of the learned offer functions, not a cubic-curve reinterpretation.

Full-month 20/100-tranche comparisons are now available, but no continuum-limit
or all-month generalization claim follows. The combined replays cover
**{audit['witness_hours']+1344:,} witness hours**, counting repeated evaluations
of the same calendar hours under different models/curve states. Refinement
receipts are in the study's ignored `refined-physical` directory.

[Per-zone February comparison, both bid resolutions](assets/fast-fit-physical-transfer-zones-2025.csv).
'''
    report.write_text(text)
    result = dict(status='audited_refinement_report_complete', selected_iteration=selected,
                  report_sha256=digest(report), zone_csv_sha256=digest(path),
                  refinement_summary_sha256=digest(refined/'summary.json'),
                  original_audit_sha256=digest(out/'transfer-audit.json'), producer_sha256=digest(__file__))
    atomic_json(refined/'report.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    run()
