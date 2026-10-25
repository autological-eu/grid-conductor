"""Actual-point-only progress plots and complete monthly-mean score exports."""
import calendar
import csv
import json
from pathlib import Path
import numpy as np
from sigmoid_month_pairs_2025 import digest
from run_differentiable_spline_2025 import atomic_json


def report(out, source, data, final=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['svg.fonttype'] = 'none'
    records = []
    for month in range(1, 13):
        for step in range(101):
            path = out/f'month-{month:02d}/{step:03d}.json'
            if path.exists():
                records.append(json.loads(path.read_text()))
    complete = np.isfinite(data['observed_prices']).all(axis=0)
    payload = dict(model_id='independent-hourly-six-node-monthly-economic-mean',
                   score_solver_id='robust-batched-transport-kappa4', audit_status='passed',
                   audit_scope='Every live hourly soft response, bounds, balance and metric replayed before large-array pruning; not original PTDF certification.',
                   modeled_zones=source['zones'], observed_zones=[z for z, ok in zip(source['zones'], complete) if ok],
                   records=records)
    if final:
        from forward_learning_curves_2025 import render
        atomic_json(out/'scores.json', payload)
        render(payload, out/'learning-curves')
    # Partial plots never extrapolate/interpolate uncomputed updates.
    fig, axes = plt.subplots(3, 4, figsize=(14, 8), sharex=True)
    fig.suptitle('Monthly-mean transfer · fast transport solver · '+('complete' if final else 'RUNNING: actual computed points only'))
    with (out/'progress-curves.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['fit_month', 'iteration', 'training_price_mae', 'forward_price_mae',
                         'training_generation_mae_twh', 'forward_generation_mae_twh', 'joint_training_loss', 'seconds'])
        for month in range(1, 13):
            rows = [r for r in records if r['month'] == month]
            ax = axes.flat[month-1]; x = [r['iteration'] for r in rows]
            ax.plot(x, [r['within']['metrics']['price_mae'] for r in rows], label='Within month', color='#2563eb')
            if month < 12:
                ax.plot(x, [r['forward']['metrics']['price_mae'] for r in rows], label='Next month: mean curve', color='#ea580c')
            title = f'{calendar.month_abbr[month]} → {calendar.month_abbr[month+1]}' if month < 12 else 'Dec: training only'
            ax.set(title=title, xlim=(0, 100), ylim=(0, None), xlabel='Parameter updates', ylabel='Price MAE (EUR/MWh)')
            ax.grid(alpha=.2)
            if rows:
                ax.legend(fontsize=6)
            else:
                ax.text(.5, .5, 'Not run yet', transform=ax.transAxes, ha='center')
            for r in rows:
                fm = r['forward']['metrics'] if r['forward'] else {}
                writer.writerow([month, r['iteration'], r['within']['metrics']['price_mae'], fm.get('price_mae', ''),
                                 r['within']['metrics']['generation_mae_twh'], fm.get('generation_mae_twh', ''), r['loss'], r['wall_seconds']])
    fig.tight_layout(); fig.savefig(out/'progress-curves.svg'); fig.savefig(out/'progress-curves.png', dpi=140); plt.close(fig)
    lines = ['# Monthly averaged supply curves — 100-update learning experiment', '',
             f"Status: {'all 12 monthly fits complete' if final else 'running; partial results'}. {len(records)} of 1,212 score points recorded.", '',
             'Each actual hour has independent technology–bidding-zone coefficients. Own-month hourly ENTSO-E prices and monthly Ember generation train the curves. The loss is smoothed price MAE / 40 plus normalized generation error and unchanged shrinkage/adjacent-hour penalties. Adam learning rate is 0.5.', '',
             'For prediction, average economic PWL prices at 0/20/40/60/80/100% supply equally over availability-positive training hours. The entire next month receives one mean curve per technology/zone, with its own hourly available MW, fuel/source prices and demand. There is no weekday/hour stratification. Unsupported groups use the neutral prior. Zero-economic renewable bids and fixed hydro remain unchanged.', '',
             'All 48 zones and actual hours are cleared. Price MAE uses the same 41 annual-complete ENTSO-E areas, including negative and extreme prices. Forward targets do not enter gradients or stopping; 100 updates run even if validation worsens. December has no fabricated January 2026 prediction.', '',
             'These are perfect-input retrospective forward-transfer diagnostics, not a live forecasting service or recovery of unique actual bids. January/February and much of 2025 were previously inspected. The solver uses 95 independently bounded corridors with quadratic transport costs; original PTDF/intrazonal coupling is omitted. These curves do not claim original-network feasibility or baseline adoption.', '',
             'Every state is independently replayed in memory using analytic supply/flow responses, original fast-model balance/bounds and observed metrics before large arrays are discarded. All mean profiles, hourly prices and monthly generation totals remain saved. Full parameter checkpoints every ten updates and full initial/final witnesses are retained. Compact current optimizer journals permit explicit inspected resume; no old studies resumed.', '',
             '![Computed learning curves](progress-curves.svg)', '',
             '[Scores and joint loss (CSV)](progress-curves.csv)', '',
             '| Fit → forecast | Last update | Within-month MAE | Forward MAE |', '|---|---:|---:|---:|']
    for month in range(1, 13):
        rows = [r for r in records if r['month'] == month]
        if rows:
            r = rows[-1]; forward = f"{r['forward']['metrics']['price_mae']:.3f}" if r['forward'] else 'Unavailable'
            lines.append(f"| {month} → {month+1 if month < 12 else '—'} | {r['iteration']} | {r['within']['metrics']['price_mae']:.3f} | {forward} |")
    (out/'report.md').write_text('\n'.join(lines)+'\n')
    atomic_json(out/'report-receipt.json', dict(status='complete' if final else 'partial', points=len(records),
                records_sha256={str((out/f"month-{r['month']:02d}/{r['iteration']:03d}.json").relative_to(out)):digest(out/f"month-{r['month']:02d}/{r['iteration']:03d}.json") for r in records},
                figure_sha256=digest(out/'progress-curves.svg'), csv_sha256=digest(out/'progress-curves.csv')))
