"""Recompute all annual observation metrics from saved quantities and prices."""
import json
import numpy as np
import pypsa
from compile_transport_corridors_2025 import NATIVE
from forward_hourly_splines_2025 import month_hours
from sigmoid_month_pairs_2025 import digest, metric
from supply_knot_network_2025 import generation
from run_differentiable_spline_2025 import atomic_json
import run_batched_transport_fit_2025 as controller


def run():
    controller.configure()
    out = controller.OUT
    if (out / 'failure.json').exists():
        raise ValueError('Inspect failed study before accepting results')
    audit = json.loads((out / 'audit.json').read_text())
    assert audit['status'] == 'passed_independent_transport_equation_replay'
    saved = json.loads((out / 'annual.json').read_text())
    assert digest(out / 'annual.npz') == saved['witness_sha256']
    state, _, _, _ = controller.controller.recovery.setup()
    source, data, network_matrix, _, capacity = state
    # Check native ordering against retained island-injection columns. Links
    # enter island/PTDF rows, not the original zonal generation-balance rows.
    native = pypsa.Network(NATIVE)
    native.determine_network_topology()
    islands = list(native.sub_networks.index)
    expected = np.zeros((len(islands), len(native.links)))
    for k, (_, link) in enumerate(native.links.iterrows()):
        expected[islands.index(native.buses.at[link.bus0, 'sub_network']), k] -= 1
        expected[islands.index(native.buses.at[link.bus1, 'sub_network']), k] += 1
    start = len(source['groups'])
    assert len(islands) == data['island_rhs'].shape[1]
    rows = slice(len(source['zones']), len(source['zones']) + len(islands))
    actual = network_matrix[rows, start:start + len(native.links)].toarray()
    np.testing.assert_allclose(actual, expected, atol=1e-12, rtol=0)
    link_order_error = float(abs(actual - expected).max())
    with np.load(out / 'annual.npz') as witness:
        np.testing.assert_array_equal(witness['hours'], np.arange(8760))
        prices = witness['prices']
        quantities = witness['quantities_gw']
    mask = np.isfinite(data['observed_prices']).all(axis=0)
    price_mae = float(abs(prices[:, mask] - data['observed_prices'][:, mask]).mean())
    cells, total = 0, 0.
    for month, record in enumerate(saved['months'], 1):
        hours = month_hours(month)
        generated = generation(source, data, capacity, quantities[hours] * 1000, hours)
        score, _ = metric(source, data, prices[hours], generated, hours, month)
        for name, value in score.items():
            np.testing.assert_allclose(value, record['metrics'][name], atol=1e-10, rtol=0)
        cells += score['generation_cells']
        total += score['generation_cells'] * score['generation_mae_twh']
    mix_mae = total / cells
    np.testing.assert_allclose([price_mae, mix_mae],
                               [saved['price_mae'], saved['generation_mae_twh']],
                               atol=1e-10, rtol=0)
    result = dict(status='passed_annual_observation_metric_replay', hours=8760,
                  zones=prices.shape[1], observed_zones=int(mask.sum()),
                  price_mae=price_mae, generation_mae_twh=mix_mae,
                  generation_cells=cells, witness_sha256=digest(out / 'annual.npz'),
                  native_link_order_island_injection_error=link_order_error,
                  audit_sha256=digest(out / 'audit.json'),
                  producer_sha256=digest(__file__))
    atomic_json(out / 'annual-metrics-audit.json', result)
    finalize_report(out, audit)
    print(json.dumps(result))


def finalize_report(out, audit):
    """Finish the report after observation replay, preserving sealed producers."""
    path = controller.ROOT / 'research/batched-transport-dispatch-2025.md'
    text = path.read_text().replace('`batched-transport-dispatch-v1`',
                                    '`batched-transport-fit-v1`')
    marker = '\n## Recovery and reproducibility\n'
    text = text.split(marker)[0]
    # Normalize prose spacing in the original compact report template.
    import re
    text = re.sub(r'(?<=[A-Za-z])(?=\d)', ' ', text)
    text = re.sub(r'(?<=\d)(?=[A-Za-z])', ' ', text)
    # Leave filenames/identifiers and exact run-root spelling intact.
    text = text.replace('-v 1`', '-v1`')
    text += marker + '''
The first numerical attempt stalled at hour 318. Direction-preserving Newton
steps repaired that case; a later warm-start failure at hour 1928 cleared from a
model-only cold start. The final policy uses cold initialization for neutral
annual inference, warm starts for fitted curves, and cold/coordinate retries
when required. All retries are included in forward timings; no economic bounds
or feasibility tolerances were relaxed. The failed roots remain preserved.

The annual solve completed before a file-saving namespace error stopped the
first fitting controller. A fresh controller corrected that plumbing and reused
the exact SHA-verified annual witness. The 145.26 seconds is the original annual
forward computation, not the duration of loading its saved results. There is
one completed market candidate, with numerical recovery ancestry, not four
competing economic models. Source arrays and full witnesses remain ignored.

Training encounters 7–32 unidentified price directions per January batch. Their
target-gradient projection is below 3e-18, so the pseudoinverse does not discard
material observed-price errors. This does not establish unique prices for every
unobserved area. The pilot's worst directional discrepancy is 1.42e-6, against
the declared 0.001 gate. Four focused tests pass. Independent annual replay's
maximum balance error is 1.01e-6 MW; a separate metric audit reconstructs all
2,916 observed monthly generation cells and the full-year hourly price MAE.

**Interpretation:** full January fitting plus full February prediction now takes
4.8–5.3 seconds per updated iteration. The cold, unfitted annual screen still
takes 145 seconds; those are distinct workloads. February price MAE improves
42.28 → 34.91 EUR/MWh and generation MAE 0.3485 → 0.3291 TWh after three updates.
This is a promising differentiable training prototype, not the completed
twelve-month forward-validation protocol. Next, test all adjacent-month pairs
and sensitivity to corridor capacities and the transport coefficient before
considering adoption. Fixed hydro and removed network physics remain material
limitations.

Reproduce the bounded study using
`PYTHONPATH=tools OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
data/pypsa-eur/upstream/.pixi/envs/default/bin/python
tools/run_batched_transport_fit_2025.py` in the repository root. Its sealed
completed output refuses duplicate execution. Then run
`tools/audit_transport_annual_metrics_2025.py` with the same Python/environment
to replay annual observation metrics and finish this report. Local receipts are
under `data/bidding-zone-network-2025/batched-transport-fit-v1`; the original
completed annual producer is `batched-transport-robust-v1`. This report is a
repository research artifact; no website publication or baseline change follows.
'''
    path.write_text(text)


if __name__ == '__main__':
    run()
