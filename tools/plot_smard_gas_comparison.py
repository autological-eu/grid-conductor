"""Plot a reported German gas reference and conditional model diagnostic."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from monthly_dispatch import digest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preview', type=Path)
    args = parser.parse_args()
    report = json.loads(args.input.read_text())
    if (report['status'] != 'german_gas_reported_consistency_and_conditional_dispatch_diagnostic_not_validation'
            or report['year'] != 2025 or report['hours'] != 8760 or any(report['acceptance'].values())
            or [r['month'] for r in report['monthly']] != list(range(1, 13))):
        raise ValueError('Complete explicitly unaccepted 2025 diagnostic required')
    fig, ax = plt.subplots(figsize=(10, 5.2), layout='constrained')
    x = [r['month'] for r in report['monthly']]
    for key, label, color, style, marker in [
        ('smard_mwh', 'SMARD reported gas', '#265baf', '-', 'o'),
        ('entsoe_reported_mwh', 'ENTSO-E reported gas (almost identical)', '#d78213', '--', 'x'),
        ('native_ccgt_ocgt_mwh', 'Candidate 006 native CCGT + OCGT', '#12816c', '-', 's')]:
        ax.plot(x, [r[key]/1e6 for r in report['monthly']], label=label, color=color, linestyle=style, marker=marker)
    ax.set(xlabel='2025 UTC calendar month', ylabel='Reported / model gas-generation energy (TWh)',
           title='German gas-generation diagnostic — observed consistency, model mismatch', xticks=x, ylim=(0, None))
    ax.grid(alpha=.2)
    ax.legend(loc='upper right', fontsize=9)
    fig.suptitle('Fixed-inventory feasible trajectory; not a converged optimum or empirical acceptance', fontsize=10)
    fig.savefig(args.output, metadata={'Description': f'Input SHA256 {digest(args.input)}; plot producer SHA256 {digest(Path(__file__))}'})
    if args.preview:
        fig.savefig(args.preview, dpi=130)
    plt.close(fig)
