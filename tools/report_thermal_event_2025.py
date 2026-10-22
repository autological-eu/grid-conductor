"""Write a compact, non-publication event report from independently audited LPs."""
import csv
import gzip
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import scipy
import highspy
from scipy.sparse import load_npz

from generation_mix_2025 import ROOT, digest

OUT = ROOT / 'data/bidding-zone-network-2025/thermal-event-v1'
RUN = OUT / 'runs-v7'
LABELS = {
    'control': 'Current supply bids',
    'ramp': 'Running-unit ramps',
    'commitment': 'Startup + online-state relaxation',
    'weather_stress': 'Renewable availability stress',
    'weather_ramp': 'Renewable stress + ramps',
    'weather_commitment': 'Renewable stress + startup',
    'firm_stress': 'Renewable + thermal stress + startup',
}


def report():
    summary = json.loads((RUN / 'summary.json').read_text())
    audit = json.loads((RUN / 'audit.json').read_text())
    assert audit['summary_sha256'] == digest(RUN / 'summary.json')
    assert audit['status'] == 'all_daily_event_alternatives_independently_replayed'
    meta = json.loads((OUT / 'inputs-protocol-v2.json').read_text())
    source = dict(np.load(OUT / 'inputs.npz'))
    A = load_npz(OUT / 'network.npz')
    cases = summary['design']['cases']
    results = {name: dict(np.load(RUN / (name + '-implemented.npz'))) for name in cases}
    for name in cases:
        if not summary['cases'][name]['case_acceptable_supply']:
            LABELS[name] += ' [emergency]'
    event = 19 * 24 + 16 - meta['start_hour']
    earlier = 14 * 24 + 16 - meta['start_hour']
    rows = []
    for name in cases:
        s = summary['cases'][name]
        p = results[name]['prices']
        dual = results[name]['network_duals'][event]
        zi = meta['zones'].index('DE-LU')
        column = meta['ng'] + meta['nl'] + zi
        co = A[:, column].toarray().ravel()
        divisor = -co[zi]
        energy = float(co[meta['nz']:meta['nz'] + meta['islands']] @ dual[meta['nz']:meta['nz'] + meta['islands']] / divisor)
        network = float(co[meta['nz'] + meta['islands']:] @ dual[meta['nz'] + meta['islands']:] / divisor)
        assert abs(energy + network - p[event, zi]) < 1e-5
        rows.append(dict(case=name, january20_de=p[event, zi], january20_dk1=p[event, meta['zones'].index('DK1')], january20_dk2=p[event, meta['zones'].index('DK2')], january15_de=p[earlier, zi], evaluated_mae=s['mae_eur_mwh'], emergency_mwh=s['total_emergency_mwh'], energy_component=energy, network_component=network, solve_seconds=sum(d['solver_seconds'] for d in s['days'])))
    with (RUN / 'comparison.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none', 'svg.hashsalt': 'january-scarcity-2025'})
    colors = dict(zip(cases, ['#333333', '#2675a8', '#a0522d', '#2b9569', '#8f65b5', '#d08726', '#c12b45']))
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    hours = np.arange(168) / 24 + 15
    for ax, zone in zip(axes, ['DE-LU', 'DK1', 'DK2']):
        zi = meta['zones'].index(zone)
        ax.plot(hours, source['observed'][48:216, zi], color='black', linewidth=2, label='ENTSO-E SDAC')
        for name in ['control', 'commitment', 'weather_commitment', 'firm_stress']:
            ax.plot(hours, results[name]['prices'][48:, zi], color=colors[name], linewidth=1, alpha=.8, label=LABELS[name])
        ax.set_ylabel(zone + '\nEUR/MWh'); ax.grid(alpha=.2)
    axes[0].legend(fontsize=8, ncol=2); axes[-1].set_xlabel('January 2025, UTC day (168 evaluated hours)')
    fig.suptitle('January price spikes: measured prices and declared sensitivities')
    fig.tight_layout(); fig.savefig(ROOT / 'research/assets/january-scarcity-prices.png', dpi=140, metadata={'Software': 'Grid Conductor'}); fig.savefig(RUN / 'prices-preview.png', dpi=120); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    y = np.arange(len(rows)); labels = [LABELS[r['case']] for r in rows]
    axes[0].barh(y, [r['january20_de'] for r in rows], color=[colors[r['case']] for r in rows]); axes[0].axvline(583.4, color='black', linestyle='--', label='Observed 583.40'); axes[0].set_yticks(y, labels); axes[0].set_xlabel('DE-LU, January 20 16 UTC, EUR/MWh'); axes[0].legend()
    axes[1].barh(y, [r['evaluated_mae'] for r in rows], color=[colors[r['case']] for r in rows]); axes[1].set_yticks(y, [''] * len(rows)); axes[1].set_xlabel('168-hour equal-zone MAE, EUR/MWh')
    for ax in axes: ax.invert_yaxis(); ax.grid(axis='x', alpha=.2)
    fig.tight_layout(); fig.savefig(ROOT / 'research/assets/january-scarcity-comparison.png', dpi=140, metadata={'Software': 'Grid Conductor'}); fig.savefig(RUN / 'comparison-preview.png', dpi=120); plt.close(fig)
    explorer = ROOT / 'public/research/country-explorer-2025'
    manifest = json.loads((explorer / 'manifest.json').read_text())
    country = next(c for c in manifest['countries'] if c['code'] == 'DE')
    country_file = explorer / country['file']
    assert digest(country_file) == country['sha256']
    published = json.loads(gzip.decompress(country_file.read_bytes()))
    area = next(a for a in published['generation'] if a['id'] == 'country:DE')
    generation_lines = []
    absolute_hour = meta['start_hour'] + event
    for i, technology in enumerate(manifest['technologies']):
        if technology['id'] not in ['solar', 'onshore_wind', 'offshore_wind', 'gas', 'hard_coal', 'lignite', 'oil']:
            continue
        measured = published['series'][area['observed'][i]][absolute_hour]
        modeled = published['series'][area['model'][i]][absolute_hour]
        assert measured is not None and modeled is not None
        generation_lines.append(f"| {technology['label']} | {modeled / manifest['generation_scale']:.1f} | {measured / manifest['generation_scale']:.1f} |")
    solar_index = next(i for i,t in enumerate(manifest['technologies']) if t['id']=='solar')
    solar_bounds = [published['series'][area[k][solar_index]][absolute_hour]/manifest['generation_scale'] for k in ['lower','upper']]
    bid_lines = []
    for fuel in ['CCGT', 'OCGT', 'coal', 'lignite']:
        ids = [j for g in meta['groups'] if g['zone'] == 'DE-LU' and g['carrier'] == fuel for j in g['columns']]
        for j in ids:
            column = A[:, j].toarray().ravel()
            assert np.count_nonzero(column) == 1 and column[meta['zones'].index('DE-LU')] == 1
        bid_lines.append(f"| {fuel} | {source['availability'][event, ids].sum()/1000:.2f} | {source['baseline'][event, ids].sum()/1000:.2f} | {source['cost'][event, ids].min():.2f}–{source['cost'][event, ids].max():.2f} |")
    lines = ['# January 2025 scarcity and daily thermal bids', '',
        'Research experiment, 22 October 2026. No baseline promotion or website/model replacement.', '',
        '## What was tested', '',
        'Can running-unit ramps, startup delays and unavailable supply explain the missed January 20 price spike? Seven predeclared alternatives use the current oil/CHP supply book and the same Europe-wide network. No parameter was fitted to the spike.', '',
        'At **16:00 UTC (17:00 CET), January 20**, corrected ENTSO-E day-ahead prices were **€583.40/MWh** in DE-LU, DK1 and DK2. These are SDAC targets, with hourly averaging where needed; Germany selects A01 auction sequence 1. Existing non-oil bids retain calibration to earlier, incorrectly selected auction targets; no corrected-target refit was performed.', '',
        '## Source mismatch before adding constraints', '',
        'At the event hour, the published current-model generation allocation differs substantially from ENTSO-E. These are German national generation comparisons (not offers or day-ahead forecasts); renewable allocation within pooled offers is illustrative. Prices and national generation have different market/geographic definitions.', '',
        '| Technology | Current model MW | ENTSO-E generation MW |', '|---|---:|---:|', *generation_lines, '',
        f"The exported conditional solar-allocation bounds are {solar_bounds[0]:.1f}–{solar_bounds[1]:.1f} MW at this hour. Reallocating the pooled renewable dispatch cannot close that solar mismatch. These are bounds conditional on model inputs, not weather-uncertainty intervals.", '',
        'The model has too much solar and coal at this hour and too little gas and oil. Restricting ramps alone cannot correct a wrong resource profile or merit order. This comparison motivates the declared availability sensitivities; it does not establish that actual generation equals available supply.', '',
        '| German modeled supply | Available GW | Dispatched GW | Bid range EUR/MWh |', '|---|---:|---:|---:|', *bid_lines, '',
        'These thermal offer columns enter only the same German balance row. In the current fixed-GSK network, substituting unused German gas for German coal leaves net exports and passive flows unchanged. Thus these unused local MW are not blocked by an internal plant-to-grid constraint in this model. Actual plant availability, startup conditions, bids and transmission effects may differ. The model offers substantial additional thermal supply below €253/MWh; explaining €583.40 requires showing why those offers would be unavailable or substantially more expensive, rather than simply adding a generic ramp cap.', '',
        '## Results', '',
        f"The January 15 comparison uses 16:00 UTC, when observed DE-LU was €{source['observed'][earlier, meta['zones'].index('DE-LU')]:.2f}/MWh. MAE covers all {int(np.isfinite(source['observed'][:216]).all(axis=0).sum())} complete observed-price zones.", '',
        '| Alternative | Jan 20 DE-LU | DK1 | DK2 | Jan 15 DE-LU | 168h MAE | Emergency MWh* |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {LABELS[r['case']]} | {r['january20_de']:.2f} | {r['january20_dk1']:.2f} | {r['january20_dk2']:.2f} | {r['january15_de']:.2f} | {r['evaluated_mae']:.2f} | {r['emergency_mwh']:.6f} |")
    lines += ['', 'Prices and MAE are EUR/MWh. MAE gives equal weight to each complete observed-price zone and each evaluated hour; this is a seven-day event test, **not an annual accuracy estimate**. *Emergency use includes all 216 implemented hours, including warm-up. Emergency supply is the original €10,000/MWh diagnostic slack, not observed market supply. Any use, including unused forecast hours, disqualifies a case as a valid supply model; a successful mathematical solve alone does not qualify it. Overlapping forecasts are checked for maximum emergency MW rather than summed as if they were implemented energy.', '',
        '![Event-hour prices and whole-window errors](assets/january-scarcity-comparison.png)', '',
        '![Hourly prices in Germany and Denmark](assets/january-scarcity-prices.png)', '',
        'Maximum emergency supply in any 48-hour forecast (MW): ' + '; '.join(f"{name}: {audit['cases'][name]['maximum_forecast_emergency_mw']:.3f}" for name in cases) + '.', '',
        '## Formulation and interpretation', '',
        '- **Control:** current calibrated hourly supply bids, original fixed hydro, physical PTDF constraints and links, fixed demand. All offer quantities and costs match the retained oil/CHP book.',
        '- **Ramps:** shared limits on total coal/lignite/CCGT/OCGT group dispatch, across all price tranches. A unit already online is distinct from a unit starting from offline.',
        '- **Startup relaxation:** continuous online, starting and shutting-down MW, stable minimum output, startup lead times, minimum up/down time, ramps and startup/no-load costs. This is an aggregated LP relaxation, not binary plant commitment or recovered EUPHEMIA pricing.',
        '- **Renewable stress:** original solar availability ×0.5 and wind ×0.7, everywhere throughout the window. Wind/solar are reconstructed before pooling into offers; observed generation never replaces availability. These factors are hypothetical sensitivities, not verified weather corrections.',
        '- **Thermal stress:** the renewable stress plus startup relaxation and 30% unavailability of modeled gas/coal capacity. This is not a measured outage series.', '',
        'Nine daily decisions implement 24 hours each, with 48-hour perfect lookahead of the model inputs, which need not equal historical market forecasts. Dispatch, online MW and pending startup/shutdown history carry across midnight. January 13–14 warm up the model; January 15–21 provide 168 evaluated hours. January 22 is the last unimplemented forecast day. Initial online capacity is inferred from prior dispatch/minimum-load fractions, pending starts are zero and initial minimum durations are assumed satisfied; this is an initialization proxy.', '',
        '| Technology | Ramp (% capacity/hour) | Stable minimum | Startup lead | Minimum up/down | Startup €/MW | Online €/MW/h |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for technology, p in summary['design']['parameters'].items():
        lines.append(f"| {technology} | {100*p['ramp_fraction_per_hour']:.0f}% | {100*p['minimum_output_fraction']:.0f}% | {p['startup_lead_hours']}h | {p['minimum_up_hours']}/{p['minimum_down_hours']}h | {p['startup_eur_per_mw']} | {p['online_eur_per_mw_hour']} |")
    lines += ['', 'These are technology-class sensitivity assumptions. Fichtner/Agora gives orders of magnitude for ramping, minimum load and startup duration. Hard-coal and OCGT ramps here are stricter than its typical ranges. Even a 1%/minute running-unit ramp permits 60% of capacity per hour, so ordinary hourly changes can remain unconstrained. Offline startup can instead take hours. A single startup lead cannot represent hot/warm/cold plant states. Minimum durations, startup and no-load costs are experimental proxies, not measured fleet coefficients.', '',
        '### Network contribution at the January 20 German peak', '',
        'The free net-position column separates each LP marginal price into island energy and passive-network shadow-price terms. These are algebraic model contributions, not measured causes of the real market spike. In a degenerate LP, their split can depend on the selected optimal dual solution.', '',
        '| Alternative | Island energy | Passive network | Total |', '|---|---:|---:|---:|']
    for r in rows: lines.append(f"| {LABELS[r['case']]} | {r['energy_component']:.2f} | {r['network_component']:.2f} | {r['january20_de']:.2f} |")
    lines += ['', '## Verification and provenance', '',
        f"All 63 daily LP witnesses pass independent replay of original network equations, declared temporal constraints, state carry, bounds, costs and full primal/dual optimality. Maximum native residual: {audit['maximum_native_residual_mw']:.3g} MW; temporal residual: {audit['maximum_temporal_residual_mw']:.3g} MW; duality gap: €{audit['maximum_duality_gap_eur']:.3g}. The driver also solves ±0.1MW load perturbations at the German event hour and brackets the reported marginal price; the auditor checks the recorded slopes. Four toy tests cover ramp scarcity, startup carry, tranche grouping and mixed renewable stress.", '',
        'Sources are the frozen current physical book and oil/CHP witness; corrected original ENTSO-E A44 price snapshots; original PyPSA-Eur 2025 weather availability, retained geographic shares and IRENA linear capacity commissioning. Files and source hashes are bound in the ignored input, resource, run and audit receipts. The current published report/explorer are unchanged.', '',
        'Executable sequence: `prepare_thermal_event_2025.py`, protocol binding, `thermal_event_resources_2025.py`, `run_thermal_event_2025.py` (fresh: no reuse argument; checkpoint replay: `--reuse-version runs-v6`), `audit_thermal_event_2025.py`, then this report. Output folders are immutable: existing snapshots deliberately refuse overwrite. The protocol binder preserves the initial receipt after a pre-solve lookahead revision; it changes no physical array. The final driver replays and reuses completed daily witnesses instead of solving them twice. The initial 20-minute orchestration budget required a checkpoint continuation; physical cases and acceptance gates did not change. The final code/provenance replay links immutable witness files and makes no new solves. Reused partial-case days have zero newly spent solve time in the table, not zero original runtime.', '',
        'The native simplex backend failed numerically on a ramp block; the native-crossover attempt ended without a completed startup witness. Neither establishes physical infeasibility. The completed startup cases use SciPy’s bundled HiGHS IPM without native crossover, with unchanged feasibility/optimality gates. Two independent cases run concurrently; each case remains chronological. Runtime below measures recorded solve calls (excluding time originally spent on reused partial-case days), excluding input reconstruction, probes, audit and reporting; concurrent wall times are not comparable to production annual throughput.', '',
        '| Alternative | Recorded daily solve seconds* |', '|---|---:|']
    for r in rows: lines.append(f"| {LABELS[r['case']]} | {r['solve_seconds']:.1f} |")
    de = meta['zones'].index('DE-LU')
    stress_peak = 168 + int(results['firm_stress']['prices'][168:192, de].argmax())
    stress_peak_hour = stress_peak - 168
    stress_peak_price = results['firm_stress']['prices'][stress_peak, de]
    stress_peak_observed = source['observed'][stress_peak, de]
    by_name = {r['case']: r for r in rows}
    control = by_name['control']; commitment = by_name['commitment']; firm = by_name['firm_stress']
    lines += ['', '## What the experiment establishes', '',
        f"Running-unit ramps change the German event-hour price by €{by_name['ramp']['january20_de']-control['january20_de']:.4f}/MWh. Adding the declared startup/online-state model changes it from €{control['january20_de']:.2f} to €{commitment['january20_de']:.2f}/MWh; its whole-window MAE is €{commitment['evaluated_mae']:.2f}, compared with €{control['evaluated_mae']:.2f} for control.", '',
        f"The combined renewable/thermal/startup stress gives €{firm['january20_de']:.2f}/MWh, leaving an absolute €{abs(583.4-firm['january20_de']):.2f}/MWh event-hour discrepancy. It uses {firm['emergency_mwh']:.6f} MWh emergency supply across implemented hours. Even a closer stressed price would only demonstrate sensitivity under assumed availability; it would not identify the real cause.", '',
        f"The strict stress does produce a higher German price of €{stress_peak_price:.2f}/MWh on January 20 at {stress_peak_hour:02d}:00 UTC, two hours after the observed maximum; the observed price at that hour was €{stress_peak_observed:.2f}/MWh. Its emergency supply includes {summary['cases']['firm_stress']['evaluated_emergency_mwh']:.2f} MWh inside the evaluated week, as well as warm-up shortages. This is a mistimed, supply-gate-failing sensitivity, not recovery of the observed spike.", '',
        'These outcomes decide whether this particular thermal extension explains the event; they cannot establish that actual plant startup/ramping was irrelevant. Missing outages, heterogeneous units, forecasts and real bids can change the result. Do not fit a one-off scarcity adder or promote an event-window winner into the annual simulator.', '',
        '## Sources and next action', '',
        '- [SMARD: January 20, 2025 market event](https://www.smard.de/page/en/topic-article/217400/219038): high demand and low wind/solar forecasts, with day-ahead prices formed before actual generation is known.',
        '- [Fichtner/Agora, Flexibility in thermal power plants (2017)](https://www.agora-energiewende.org/fileadmin/Projekte/2017/Flexibility_in_thermal_plants/115_flexibility-report-WEB.pdf), especially technology comparison around pp.48–52.',
        '- [PyPSA unit-commitment formulation](https://docs.pypsa.org/latest/user-guide/optimization/unit-commitment/): ramping, startup, minimum durations and linearized commitment.', '',
        'Before changing production bids, reconcile the unusually high modeled German solar output on the event day against independent **day-ahead forecasts** and source timestamps/geographic weighting; acquire dated thermal outages/availability and cross-border constraints. Actual generation is useful validation, but cannot prove what supply was forecast or offered. Fixed hydro, continuous group states, static GSK and the short event window remain material limits. No claim of actual scarcity, strategic bidding or outage causation follows from a synthetic stress reproducing a high price.', '']
    dest = ROOT / 'research/january-scarcity-2025.md'
    dest.write_text('\n'.join(lines))
    receipt = dict(figures_sha256={name:digest(ROOT/'research/assets'/name) for name in ['january-scarcity-prices.png','january-scarcity-comparison.png']},runtime_versions=dict(numpy=np.__version__,scipy=scipy.__version__,native_highs=highspy.Highs().version()),report_sha256=digest(dest),producer_sha256=digest(Path(__file__)),summary_sha256=digest(RUN/'summary.json'),audit_sha256=digest(RUN/'audit.json'),comparison_sha256=digest(RUN/'comparison.csv'),country_manifest_sha256=digest(explorer/'manifest.json'),country_file_sha256=digest(country_file))
    (RUN/'report-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(rows,indent=2))

if __name__ == '__main__':
    report()
