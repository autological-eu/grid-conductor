"""Plot the capped, water-infeasible Swedish injection price sensitivity."""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from baselines.compact.source import ROOT, grouped_fit_inputs


def main():
    folder = ROOT / 'data/bidding-zone-network-2025/swedish-hydro-injection-v1'
    summary = json.loads((folder / 'summary.json').read_text())
    with np.load(folder / 'prices.npz') as archive:
        capped = archive['capped_generation']
    schema, data, _ = grouped_fit_inputs()
    country = next(group['country_id'] for group in schema['groups'] if group['country'] == 'SE')
    tech = schema['technologies'].index('reservoir')
    observed = data['observed_generation'][:, country, tech]
    fixed = data['fixed_generation'][:, country, tech]
    months = np.arange('2025-01-01', '2026-01-01', dtype='datetime64[h]')
    months = months.astype('datetime64[M]').astype(int) % 12
    zones = ['NO1', 'NO2', 'NO3', 'NO4', 'NO5', 'SE1', 'SE2', 'SE3', 'SE4']
    records = summary['zone_metrics_on_feasible_hours_only']
    before = [records[z]['baseline_mae_eur_mwh'] for z in zones]
    after = [records[z]['injection_mae_eur_mwh'] for z in zones]
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), layout='constrained')
    x = np.arange(len(zones))
    axes[0].bar(x - .2, before, width=.4, label='Retained baseline')
    axes[0].bar(x + .2, after, width=.4, label='Capped observed hydro injection')
    axes[0].set(xticks=x, xticklabels=zones, ylabel='Price MAE (€/MWh)',
                title='Full-year LP price response; replacement violates water budget')
    axes[0].legend()
    x = np.arange(1, 13)
    for series, label in [(observed, 'Reported B12'), (fixed, 'Fixed model'),
                          (capped, 'Capped injection')]:
        axes[1].plot(x, [series[months == month].sum() / 1e6 for month in range(12)],
                     marker='o', label=label)
    axes[1].set(xticks=x, xlabel='2025 month', ylabel='Swedish reservoir generation (TWh)',
                title='Reported volume is above the source model’s cyclic water budget')
    axes[1].legend()
    out = ROOT / 'research/assets/swedish-hydro-injection-2025.svg'
    fig.savefig(out)
    plt.close(fig)
    print(out)


if __name__ == '__main__':
    main()
