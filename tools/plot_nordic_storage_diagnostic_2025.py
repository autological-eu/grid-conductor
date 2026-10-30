"""Plot retained 2025 Nordic price residuals and observed Swedish hydro."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from baselines.compact.evaluation import physical_lp, saved_annual
from baselines.compact.source import ROOT, grouped_fit_inputs


def main():
    schema, data, _ = grouped_fit_inputs()
    model = physical_lp()
    _, witness = saved_annual()
    zones = model['zones']
    names = ['NO1', 'NO2', 'NO3', 'NO4', 'NO5', 'SE1', 'SE2', 'SE3', 'SE4']
    price = witness['row_duals'][:, :model['nz']]
    observed = data['observed_prices']
    stamps = np.arange('2025-01-01', '2026-01-01', dtype='datetime64[h]')
    months = stamps.astype('datetime64[M]').astype(int) % 12
    monthly = np.array([[np.mean(abs(price[(months == month), zones.index(name)] -
                                      observed[(months == month), zones.index(name)]))
                         for month in range(12)] for name in names])
    bias = np.array([np.mean(price[:, zones.index(name)] - observed[:, zones.index(name)])
                     for name in names])
    sweden = next(group['country_id'] for group in schema['groups'] if group['country'] == 'SE')
    hydro = schema['technologies'].index('reservoir')
    fixed = data['fixed_generation'][:, sweden, hydro]
    reported = data['observed_generation'][:, sweden, hydro]
    if not np.isfinite(reported).all():
        raise ValueError('Incomplete Swedish reservoir target')
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), layout='constrained')
    image = axes[0].imshow(monthly, aspect='auto', cmap='magma', vmin=0, vmax=90)
    axes[0].set(yticks=np.arange(len(names)), yticklabels=names,
                xticks=np.arange(12), xticklabels=[f'{m:02d}' for m in range(1, 13)],
                xlabel='2025 month', title='Current LP: monthly day-ahead price MAE (€/MWh)')
    fig.colorbar(image, ax=axes[0], label='€/MWh')
    axes[1].bar(names, bias, color=['#3572b0' if value < 0 else '#c65c44' for value in bias])
    axes[1].axhline(0, color='black', linewidth=.7)
    axes[1].set(ylabel='Model minus observed €/MWh',
                title='Annual bias changes sign between southern and northern Norway/Sweden')
    week = stamps.astype('datetime64[W]').astype(int) - stamps[0].astype('datetime64[W]').astype(int)
    observed_week = np.bincount(week, weights=reported) / 1000
    fixed_week = np.bincount(week, weights=fixed) / 1000
    axes[2].plot(observed_week, label=f'Observed A75 reservoir: {reported.sum()/1e6:.1f} TWh')
    axes[2].plot(fixed_week, label=f'Fixed model schedule: {fixed.sum()/1e6:.1f} TWh')
    axes[2].set(xlabel='Week of 2025', ylabel='GWh per week',
                title='Sweden: reservoir energy differs in volume and timing')
    axes[2].legend()
    output = ROOT / 'research/assets/nordic-storage-diagnostic-2025.svg'
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)
    print(output)

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), layout='constrained')
    for zone in ['NO2', 'NO4', 'SE2', 'SE4']:
        index = zones.index(zone)
        errors = [np.mean(price[months == month, index] - observed[months == month, index])
                  for month in range(12)]
        axes[0].plot(np.arange(1, 13), errors, marker='o', label=zone)
    axes[0].axhline(0, color='black', linewidth=.7)
    axes[0].set(ylabel='Model minus ENTSO-E (€/MWh)',
                title='Monthly mean price bias: the Nordic error changes with season')
    axes[0].legend(ncol=4)
    monthly_observed = [reported[months == month].sum() / 1e6 for month in range(12)]
    monthly_fixed = [fixed[months == month].sum() / 1e6 for month in range(12)]
    x = np.arange(1, 13)
    axes[1].bar(x - .2, monthly_observed, width=.4, label='Observed source category')
    axes[1].bar(x + .2, monthly_fixed, width=.4, label='Fixed model schedule')
    axes[1].set(xlabel='2025 month', ylabel='TWh', xticks=x,
                title='Swedish reservoir generation: monthly volume and timing mismatch')
    axes[1].legend()
    output = ROOT / 'research/assets/nordic-seasonal-patterns-2025.svg'
    fig.savefig(output)
    plt.close(fig)
    print(output)


if __name__ == '__main__':
    main()
