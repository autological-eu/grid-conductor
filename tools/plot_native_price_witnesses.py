"""Plot provisional price-bias sensitivity, preserving individual node identity."""
import argparse
import json
import math
from pathlib import Path

from monthly_dispatch import digest


def plot(source, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    report = json.loads(source.read_text())
    if (report['status'] != 'fixed_inventory_price_sensitivity_not_validation'
            or report['year'] != 2025 or report['hours'] != 8760
            or report['producer_sha256'] != digest(Path(__file__).parent/'compare_native_price_witnesses.py')
            or any(report['acceptance'].values())):
        raise ValueError('Unpromoted complete, source-checked sensitivity required')
    nodes = [row for row in report['nodes'] if 'metrics' in row]
    if len(nodes) != report['compared_nodes'] or len({row['node'] for row in nodes}) != len(nodes):
        raise ValueError('Complete unique compared nodes required')
    countries = sorted({row['country'] for row in nodes})
    all_values = [row['metrics']['bias_eur_mwh'][key] for row in nodes for key in ['reference', 'candidate']]
    if not all_values or any(type(value) not in (int, float) or not math.isfinite(value) for value in all_values):
        raise ValueError('Finite paired price biases required')
    low, high = min(all_values+[0.]), max(all_values+[0.])
    pad = max(5., .08*(high-low))
    fig, ax = plt.subplots(figsize=(9, 8))
    for index, country in enumerate(countries):
        rows = [row for row in nodes if row['country'] == country]
        ax.scatter([row['metrics']['bias_eur_mwh']['reference'] for row in rows],
                   [row['metrics']['bias_eur_mwh']['candidate'] for row in rows],
                   color=plt.get_cmap('tab20')(index % 20), marker='o' if index < 20 else '^',
                   s=34, alpha=.85, label=country)
    ax.plot([low-pad, high+pad], [low-pad, high+pad], color='#475569', linewidth=1,
            linestyle='--', label='Unchanged bias')
    ax.axhline(0., color='#cbd5e1', linewidth=.8)
    ax.axvline(0., color='#cbd5e1', linewidth=.8)
    ax.set_xlim(low-pad, high+pad)
    ax.set_ylim(low-pad, high+pad)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel(f"{report['reference']['id']} bias: model − observed (€/MWh)")
    ax.set_ylabel(f"{report['candidate']['id']} bias: model − observed (€/MWh)")
    ax.grid(alpha=.15)
    fig.suptitle('Inventory sensitivity of provisional nodal-price bias', fontsize=14)
    ax.set_title('Same 2025 observations; each dot is one model node. Not empirical validation.', fontsize=9)
    fig.legend(*ax.get_legend_handles_labels(), loc='lower center', ncol=6, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, .12, 1, .94))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, metadata={'Description':'Sensitivity JSON SHA256 '+digest(source)+
                                 '; plot producer SHA256 '+digest(Path(__file__))})
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve prior plot evidence')
    plot(args.input, args.output)
