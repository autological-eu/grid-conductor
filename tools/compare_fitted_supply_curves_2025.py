"""Extract saved May fits on identical June availability; no fitting or clearing."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import expit
from supply_knot_splines_2025 import KNOTS, spline

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/bidding-zone-network-2025'
OLD = BASE / 'sigmoid-month-pairs-v1'
NEW = BASE / 'supply-knots-lp-v1'
NAME = 'fitted-spline-sigmoid-comparison-2025'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def run():
    # Verify actual source/proposal bytes, not merely historic success receipts.
    provenance = read(NEW / 'provenance.json')
    for rel, sha in provenance.items():
        assert digest(ROOT / rel) == sha, rel
    source = read(OLD / 'inputs.json')
    assert digest(OLD / 'inputs.npz') == source['input_sha256']
    old_pair, new_pair = read(OLD / 'pair-05-06.json'), read(NEW / 'pair-05-06.json')
    assert digest(OLD / 'proposal-05.json') == old_pair['proposal']['sha256']
    assert digest(NEW / 'proposal-05.json') == new_pair['proposal_sha256']
    layout = read(NEW / 'layout.json')
    assert layout['source_groups'] == source['groups']
    old_theta = np.array(read(OLD / 'proposal-05.json')['theta'])
    new_theta = np.array(read(NEW / 'proposal-05.json')['theta'])
    hour = int((np.datetime64('2025-06-15T12') - np.datetime64('2025-01-01T00')) / np.timedelta64(1, 'h'))
    with np.load(OLD / 'inputs.npz') as z:
        available, costs, features = z['capacity'][hour], z['source_cost'][hour], z['features'][hour]
    zero = read(ROOT / 'config/supply-knots-lp-2025.json')['zero_economic_bid']
    mapping = np.array(layout['mapping'])
    # Sigmoid inverse has infinite endpoints. Show its actual 1–99% interior,
    # and the finite spline's complete range; never fabricate sigmoid endpoints.
    u = np.linspace(.01, .99, 99)
    dense = np.linspace(0, 1, 301)
    rows, summary = [], []
    plt.rcParams.update({'svg.fonttype': 'none', 'font.size': 10})
    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    for ax, tech, label in zip(axes.flat,
            ['gas', 'hard_coal', 'lignite', 'oil', 'biomass', 'solar'],
            ['Gas', 'Hard coal', 'Lignite', 'Oil / CHP', 'Biomass', 'Solar']):
        curve = next(j for j, g in enumerate(layout['groups']) if g['zone'] == 'DE-LU' and g['technology'] == tech)
        ids = np.flatnonzero((mapping == curve) & (available > 0))
        assert len(ids) and all(source['groups'][j]['technology'] == tech and source['groups'][j]['zone'] == 'DE-LU' for j in ids)
        original_ids = [j for j, g in enumerate(source['groups'])
                        if g['zone'] == 'DE-LU' and g['technology'] == tech and available[j] > 0]
        assert ids.tolist() == original_ids, 'Pooled curve lost original source availability'
        cap = available[ids]
        total = cap.sum()
        groups = [source['groups'][j] for j in ids]
        pars = old_theta[[g['parameter'] for g in groups]]
        shifts = (np.array([features[g['zone_id']] for g in groups]) * pars[:, :5]).sum(axis=1)
        shifts = np.clip(shifts, -80, 80)
        centers, spreads = costs[ids] + shifts, np.exp(pars[:, 5])
        # Sum source quantities at each price, then invert the technology total.
        low = np.full(len(u), np.min(centers - 40 * spreads))
        high = np.full(len(u), np.max(centers + 40 * spreads))
        for _ in range(80):
            mid = (low + high) / 2
            quantity = (cap * expit((mid[:, None] - centers) / spreads)).sum(axis=1)
            low = np.where(quantity < u * total, mid, low)
            high = np.where(quantity >= u * total, mid, high)
        old_price = (low + high) / 2
        recovered = (cap * expit((old_price[:, None] - centers) / spreads)).sum(axis=1)
        error = float(abs(recovered - u * total).max())
        assert error < 1e-7
        anchor = float(cap @ costs[ids] / total)
        par = new_theta[curve]
        inc = .001 + 20 * np.logaddexp(0, par[5:])
        shift = 80 * np.tanh(features[layout['groups'][curve]['zone_id']] @ par[:5] / 4)

        def fitted(v):
            return np.zeros(len(v)) if tech in zero else anchor + shift + spline(v, np.repeat(inc[None, :], len(v), axis=0))[0]

        new_price, nodes = fitted(dense), fitted(KNOTS)
        assert np.diff(new_price).min() >= -1e-9
        # Check the plotted interpolation independently against SciPy PCHIP.
        from scipy.interpolate import PchipInterpolator
        assert abs(PchipInterpolator(KNOTS, nodes)(dense) - new_price).max() < 1e-8
        ax.plot(u * 100, old_price, color='#bb5a2a', linewidth=2, linestyle='--', label='Earlier sigmoid fit')
        ax.plot(dense * 100, new_price, color='#176b87', linewidth=2, label='Fitted six-node spline')
        ax.scatter(KNOTS * 100, nodes, color='#176b87', s=28, zorder=3)
        ax.axhline(0, color='#777777', linewidth=.6, alpha=.5)
        ax.set(title=f'{label} · {total / 1000:.2f} GW available', xlabel='Share of available output (%)', ylabel='Bid (€/MWh)', xlim=(0, 100))
        ax.set_xticks(KNOTS * 100)
        ax.grid(alpha=.15)
        if tech in zero:
            ax.text(.04, .94, 'Spline experiment: zero renewable bid', transform=ax.transAxes, va='top', fontsize=9, color='#176b87')
        for fraction, p, s in zip(u, old_price, fitted(u)):
            rows.append(dict(zone='DE-LU', hour_utc='2025-06-15T12:00:00Z', technology=tech,
                supply_fraction=float(round(fraction, 2)), available_mw=float(total), offered_mw=float(fraction * total),
                sigmoid_bid_eur_mwh=float(p), spline_bid_eur_mwh=float(s)))
        summary.append(dict(technology=tech, available_gw=float(total / 1000), original_source_groups=len(ids),
            sigmoid_median_eur_mwh=float(old_price[49]), spline_median_eur_mwh=float(fitted(np.array([.5]))[0]),
            spline_nodes_eur_mwh=nodes.tolist(), maximum_inverse_quantity_error_mw=error))
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, frameon=False, bbox_to_anchor=(.5, .04))
    fig.suptitle('Learned technology supply curves · DE-LU\n15 June 2025, 12:00 UTC · both fitted on May', fontsize=15)
    fig.text(.5, .015, 'Identical available MW. Dots = spline nodes. Sigmoid shown at 1–99%; endpoints diverge. Different fitting assumptions.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .10, 1, .92))
    dest = ROOT / 'research'
    asset = dest / 'assets' / f'{NAME}.png'
    fig.savefig(asset, dpi=150)
    svg = dest / f'{NAME}.svg'
    fig.savefig(svg)
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    plt.close(fig)
    csv_path = dest / f'{NAME}.csv'
    with csv_path.open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    files = [OLD / 'inputs.json', OLD / 'inputs.npz', OLD / 'proposal-05.json', OLD / 'pair-05-06.json',
        NEW / 'proposal-05.json', NEW / 'pair-05-06.json', NEW / 'layout.json', NEW / 'provenance.json',
        ROOT / 'config/supply-knots-lp-2025.json', ROOT / 'tools/supply_knot_splines_2025.py', Path(__file__).resolve(),
        asset, svg, csv_path]
    receipt = dict(scope='Saved-parameter curve extraction only; no fitting, clearing or model promotion',
        hour=hour, zone='DE-LU', training_month=5, example_month=6, curves=summary,
        sha256={str(p.relative_to(ROOT)): digest(p) for p in files})
    (dest / f'{NAME}-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    run()
