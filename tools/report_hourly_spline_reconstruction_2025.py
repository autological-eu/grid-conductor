"""Compact audited January reconstruction report; no public model promotion."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from sigmoid_month_pairs_2025 import ROOT, FAMILIES, EMBER, digest
from supply_knot_network_2025 import load
from hourly_spline_reconstruction_2025 import OUT, PLAN


def write_csv(path, rows):
    with path.open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def run():
    summary = json.loads((OUT / 'summary.json').read_text())
    audit = json.loads((OUT / 'audit.json').read_text())
    assert audit['summary_sha256'] == digest(OUT / 'summary.json')
    assert audit['status'] == 'all_iteration_LP_scores_and_stopping_plus_best_smooth_KKT_passed'
    history = json.loads((OUT / 'history.json').read_text())
    ancestry = json.loads((OUT / 'ancestry.json').read_text()) if (OUT / 'ancestry.json').exists() else None
    recovery_start = ancestry['resumed_iteration'] if ancestry else np.inf
    assert digest(OUT / 'history.json') == summary['history_sha256']
    sealed, data, _, _, _ = load()
    hours = np.load(OUT / 'hours.npy')
    best = summary['best_iteration']
    with np.load(OUT / 'iteration-000/lp.npz') as z:
        initial_prices, initial_gen = z['row_duals'][:, :sealed['nz']], z['generation']
    with np.load(OUT / f'iteration-{best:03d}/lp.npz') as z:
        prices, gen = z['row_duals'][:, :sealed['nz']], z['generation']
    target = data['observed_prices'][hours]
    complete = np.isfinite(data['observed_prices']).all(axis=0)
    with np.load(OUT / f'iteration-{best:03d}/smooth.npz') as z:
        transfer = abs(prices[:, complete] - z['prices'][:, complete])
    initial_metrics, best_metrics, last_metrics = [summary[k]['lp'] for k in ['initial', 'best', 'last']]
    name = 'hourly-spline-reconstruction-2025'
    dest = ROOT / 'research'
    paths = []
    convergence = [dict(iteration=r['iteration'], lp_price_mae_eur_mwh=r['lp']['price_mae'], smooth_price_mae_eur_mwh=r['smooth']['price_mae'],
        lp_generation_mae_twh=r['lp']['generation_mae_twh'], lp_generation_normalized_mae=r['lp']['generation_normalized_mae'], joint_loss=r['loss'],
        best_so_far_iteration=r['best_iteration'], consecutive_nonimprovements=r['nonimproving_iterations'],
        execution_stage='original' if r['iteration'] < recovery_start else 'numerical_recovery', loop_session_seconds=r['elapsed_seconds']) for r in history]
    p = dest / f'{name}-iterations.csv'
    write_csv(p, convergence)
    paths.append(p)
    zones = []
    for j, zone in enumerate(sealed['zones']):
        known = np.isfinite(target[:, j])
        if not known.any():
            continue
        zones.append(dict(zone=zone, observed_hours=int(known.sum()), eligible_headline=bool(complete[j]),
            initial_mae_eur_mwh=float(abs(initial_prices[known, j] - target[known, j]).mean()),
            fitted_mae_eur_mwh=float(abs(prices[known, j] - target[known, j]).mean()),
            fitted_bias_eur_mwh=float((prices[known, j] - target[known, j]).mean()),
            fitted_correlation=float(np.corrcoef(prices[known, j], target[known, j])[0, 1]) if known.sum() > 1 and np.std(prices[known, j]) > 0 else ''))
    p = dest / f'{name}-zones.csv'
    write_csv(p, zones)
    paths.append(p)
    observed_gen = data['ember'][0]
    monthly = lambda g: np.column_stack([g[:, :, [sealed['technologies'].index(t) for t in EMBER[f]]].sum(axis=(0, 2)) / 1e6 for f in FAMILIES])
    ig, fg = monthly(initial_gen), monthly(gen)
    mix_rows = [dict(country=country, family=family, observed_twh=float(observed_gen[c, f]), initial_twh=float(ig[c, f]), fitted_twh=float(fg[c, f]))
        for c, country in enumerate(sealed['countries']) for f, family in enumerate(FAMILIES) if np.isfinite(observed_gen[c, f])]
    eligible = [r for r in zones if r['eligible_headline']]
    improved_zones = sum(r['fitted_mae_eur_mwh'] < r['initial_mae_eur_mwh'] for r in eligible)
    worse_zones = [r['zone'] for r in eligible if r['fitted_mae_eur_mwh'] > r['initial_mae_eur_mwh'] + 1e-6]
    improved_cells = sum(abs(r['fitted_twh'] - r['observed_twh']) < abs(r['initial_twh'] - r['observed_twh']) - 1e-10 for r in mix_rows)
    worse_cells = sum(abs(r['fitted_twh'] - r['observed_twh']) > abs(r['initial_twh'] - r['observed_twh']) + 1e-10 for r in mix_rows)
    p = dest / f'{name}-generation.csv'
    write_csv(p, mix_rows)
    paths.append(p)
    plt.rcParams.update({'svg.fonttype': 'none', 'font.size': 10})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    x = [r['iteration'] for r in history]
    axes[0].plot(x, [r['lp']['price_mae'] for r in history], 'o-', color='#176b87', label='Original LP')
    axes[0].plot(x, [r['smooth']['price_mae'] for r in history], '--', color='#bb5a2a', label='Smooth training solver')
    axes[0].axvline(best, color='#777777', linestyle=':', label=f'Selected iteration {best}')
    axes[0].set(xlabel='Completed full-month iteration', ylabel='Price MAE (€/MWh)', title='January reconstruction · all744 hours')
    axes[0].legend()
    axes[1].plot(x, [r['lp']['generation_mae_twh'] for r in history], 'o-', color='#176b87')
    axes[1].axvline(best, color='#777777', linestyle=':')
    axes[1].set(xlabel='Completed full-month iteration', ylabel='Monthly generation MAE (TWh)', title='Actual national/resource monthly totals')
    for ax in axes:
        ax.grid(alpha=.2)
    fig.tight_layout()
    p = dest / f'{name}-convergence.svg'
    fig.savefig(p)
    paths.append(p)
    plt.close(fig)
    fig, axes = plt.subplots(4, 1, figsize=(12, 9), sharex=True)
    for ax, zone in zip(axes, ['DE-LU', 'FR', 'ES', 'NO2']):
        j = sealed['zones'].index(zone)
        ax.plot(hours / 24 + 1, target[:, j], color='#222222', linewidth=1., label='Observed ENTSO-E')
        ax.plot(hours / 24 + 1, initial_prices[:, j], color='#bb5a2a', linewidth=.7, alpha=.65, label='Shared initialization')
        ax.plot(hours / 24 + 1, prices[:, j], color='#176b87', linewidth=.8, label='Fitted hourly curves')
        ax.set(ylabel='€/MWh', title=zone)
        ax.grid(alpha=.15)
    axes[0].legend(ncol=3)
    axes[-1].set_xlabel('January day (UTC, hourly observations)')
    fig.suptitle('In-sample hourly reconstruction · original LP prices')
    fig.tight_layout()
    p = dest / 'assets' / f'{name}-prices.png'
    fig.savefig(p, dpi=150)
    paths.append(p)
    plt.close(fig)
    for p in paths:
        if p.suffix == '.svg':
            p.write_text('\n'.join(s.rstrip() for s in p.read_text().splitlines()) + '\n')
    row = lambda label, m: f"| {label} | {m['price_mae']:.3f} | {m['generation_mae_twh']:.4f} | {m['generation_normalized_mae']:.4f} |"
    bands = ['| Observed price band €/MWh | Zone-hours | Initial MAE | Selected MAE |', '|---|---:|---:|---:|']
    observed = target[:, complete]
    for label, low, high in [('Below0', -np.inf, 0), ('0–50', 0, 50), ('50–100', 50, 100), ('100–200', 100, 200), ('200–500', 200, 500), ('500+', 500, np.inf)]:
        mask = (observed >= low) & (observed < high)
        if mask.any():
            a = abs(initial_prices[:, complete] - observed)[mask].mean()
            b = abs(prices[:, complete] - observed)[mask].mean()
            bands.append(f'| {label} | {int(mask.sum())} | {a:.2f} | {b:.2f} |')
    recovery_text = ''
    timing = f"Fitting-loop wall time was{summary['seconds_this_session'] / 60:.1f} minutes, excluding source setup and the separate audit."
    if ancestry:
        pilot = json.loads((OUT / 'recovery-pilot.json').read_text())
        recovery_text = f"""The original run failed during iteration20 at24 January15:00 UTC: its Newton complementarity collapsed while stationarity remained above tolerance. This failure was **not** counted as a price nonimprovement. A fresh recovery controller retains the exact economic objective, Adam checkpoint, regularizers, data, physical equations and stopping rule. A residual-backtracked barrier Newton fallback with a per-inequality barrier floor1e-12 fixes the failed solve; its directional gradient discrepancy is{pilot['gradient']['scaled_discrepancy']:.3g}. All original precision/acceptance gates remain unchanged. The743 successful partial-hour states were revalidated; parent source files and the failed checkpoint remain intact, with immutable artifacts hardlinked rather than bulk-copied. Numerical fallback is used only when the original warm/cold solve fails. This is one continuous mathematical fitting experiment with explicitly versioned numerical recovery, not a new fitted model comparison.

Reproduce the completed audit/report with `tools/audit_hourly_spline_reconstruction_2025.py --recovery` and `tools/report_hourly_spline_reconstruction_2025.py --recovery` using the scientific interpreter/PYTHONPATH documented in AGENTS.md.

"""
        timing = f"The original loop has at least{ancestry['original_observed_loop_seconds_lower_bound'] / 60:.1f} minutes of observed elapsed execution before failure; the recovery loop took another{summary['seconds_this_session'] / 60:.1f} minutes, excluding source setup and the separate audit. Raw per-iteration times in the CSV are session-relative and labelled by execution stage."
    text = f'''# Full-month hourly spline reconstruction

**January2025, all744 chronological hours across the European network. In-sample reconstruction, not predictive validation.** This experiment learns separate technology/zone spline adjustments for every hour. It does not change the accepted model or public country explorer.

## Result

The user-requested stopping rule completed: {len(history) - 1} updated iterations after initialization, ending after three consecutive iterations without a better original-LP full-month price MAE. Iteration **{best}** is retained; the final iteration is **{history[-1]['iteration']}**. A gain must exceed1e-6 EUR/MWh to count. The rule compares each candidate with the best so far, not just its immediate predecessor.

| State | LP price MAE €/MWh | Monthly generation MAE TWh | Normalized generation error |
|---|---:|---:|---:|
{row('Shared fitted initialization', initial_metrics)}
{row('Selected hourly fit', best_metrics)}
{row('Last evaluated iteration', last_metrics)}

Price MAE weights all744 hours and the same41 zones with complete annual observed-price coverage equally, not by demand. All48 zones remain in the physical network. Generation scores use known January national/resource cells from Ember, not invented hourly or zonal observations. Normalization divides each absolute monthly error by max(observed,0.25 TWh). Price-only parameter selection can sacrifice generation accuracy despite the joint training loss; retain both scores above.

Price MAE improves in{improved_zones}/{len(eligible)} scored zones; worsened zones: {', '.join(worse_zones) or 'none'}. Monthly absolute generation errors improve in{improved_cells} known country/resource cells and worsen in{worse_cells}; the remaining cells are unchanged within1e-10 TWh. The full CSVs retain these adverse results.

![Complete training and LP evaluation history]({name}-convergence.svg)

[Every iteration]({name}-iterations.csv) · [Every observed zone]({name}-zones.csv) · [Every known national generation cell]({name}-generation.csv).

## Model and fitting loop

Each hour/technology/bidding zone has one midpoint coefficient and five positive price increments, interpolated with a monotone cubic at0/20/40/60/80/100% of available output. The midpoint shift remains80×tanh(coefficient/4) EUR/MWh relative to the source-cost anchor; positive increments control the price spread around it. These inherited bounds and monotonicity remain modelling assumptions. The January shared spline proposal initializes those hourly curves exactly; its local-clock shift collapses to the actual hourly midpoint. There are {summary['active_parameters']:,} active hourly coefficients. Wind, solar and run-of-river retain zero economic bids. Original availability, source-cost anchors, physical grid equations and fixed reservoir injections are unchanged; no new storage fleet is added. Pooling and national allocation follow the [earlier spline model](supply-knots-lp-2025.md).

Every iteration clears **all744 hours** in the constrained smooth solver. Monthly dispatch is summed across those actual hours, with no16-hour sampling or monthly expansion. The loss is smooth hourly price MAE/40 plus normalized smooth monthly generation error, plus0.01 mean-squared coefficient departure from initialization and0.01 adjacent-hour departure variation. Adjacent penalties apply only when a resource is available in both hours; the month does not wrap. These penalties regularize hourly flexibility; they are assumptions, not identified bidding behaviour.

The first pass writes per-hour KKT witnesses. After assembling the true monthly loss, a second pass computes implicit price/dispatch adjoints and accumulates the full gradient. One Adam update with learning rate0.5 follows the complete batch. Zero-bid/unavailable parameters stay frozen. This avoids holding a month's KKT factorizations in memory. Existing source producers remain unchanged.

Each candidate also clears every hour through the original HiGHS LP, with20 divisible equal-MW tranches and exact interval-average economic spline bids. The LP has no technical quadratic regularizer. The smooth training solver has small technical curvature and stricter numerical precision; its loss and prices are not substituted for LP evaluation. Only the original-LP price MAE selects parameters and advances the three-iteration stopping rule. For the selected fit, smooth-versus-LP absolute price discrepancy averages{transfer.mean():.4f} EUR/MWh and reaches{transfer.max():.4f} EUR/MWh over the41 scored zones/all744 January hours; this is not an annual approximation guarantee.

## Hourly prices

![Germany, France, Spain and southern Norway hourly reconstruction](assets/{name}-prices.png)

These plots use observations that participated in fitting. Strong recovery here demonstrates historical fitting flexibility, not next-month forecasting skill, unique supply bids or reliable investment counterfactuals. Inactive/fully dispatched technologies can remain weakly identified; fitted bids can also compensate for errors in physical inputs or missing market mechanisms. January-specific coefficients require an additional predictive rule before use for unseen February hours.

Errors by observed price band retain negative-price and spike events. These are subdivisions of the same in-sample January scores, not new validation data.

{chr(10).join(bands)}

## Verification and limitations

Four focused tests cover exact shared-to-hourly initialization, shrinkage/temporal derivatives, true monthly generation sums and best-price stopping semantics. The European directional derivative discrepancy is4.34e-7 at the checked local step; a larger perturbation differed by.01096, retained in the local step-sweep evidence. Derivatives are local across active constraints, not globally smooth LP sensitivities. Three European pilot hours pass physical/optimality checks and warm-state replay. Numerical KKT precision was tightened rather than weakening existing acceptance gates.

Independent auditing reconstructs economic bids with SciPy PCHIP, replays **{audit['lp_hours']:,} LP hour witnesses across all iterations**, independently reconstructs national generation and observed errors, verifies best-parameter identity and the complete stopping history, and checks all744 selected smooth KKT states. LP maximum physical residual is{audit['lp_maxima']['primal_mw']:.3g} MW and objective gap{audit['lp_maxima']['duality_gap_eur']:.3g} EUR. Original1e-4 MW feasibility and0.05 EUR economic gates remain unchanged. Zero-priced renewable allocation can be nonunique; monthly generation follows the saved raw LP allocation and original source-capacity shares, not uniquely identified national dispatch.

{recovery_text}The first background launch ended after48 forward hours without a numerical failure record or cgroup OOM event. A single attached runner restarted the same sealed experiment; no completed optimization iteration was lost. {timing} These are training times, not single annual dispatch runtimes. Full parameters, KKT states and LP witnesses remain local ignored artifacts; compact evidence only is tracked.

[Machine-readable report receipt]({name}-receipt.json). The baseline, public explorer and disabled recurring reviews remain unchanged.
'''
    report = dest / f'{name}.md'
    report.write_text(text)
    paths.append(report)
    receipt = dict(scope=summary['scope'], summary_sha256=digest(OUT / 'summary.json'), audit_sha256=digest(OUT / 'audit.json'),
        config_sha256=digest(PLAN), reporter_sha256=digest(Path(__file__)), best_iteration=best, initial=initial_metrics, selected=best_metrics,
        artifacts_sha256={str(p.relative_to(ROOT)): digest(p) for p in paths})
    (dest / f'{name}-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--recovery', action='store_true')
    args = parser.parse_args()
    if args.recovery:
        from hourly_spline_numerical_recovery_2025 import OUT, PLAN
    run()
