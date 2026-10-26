"""Export fitted marginal bid curves at 18:00 local on the 15th of each month.

Read-only with respect to the monthly fit. This exporter is intentionally not
part of its pinned source list, so it can be added while the fit is running.
"""
import argparse
import csv
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fit_monthly_fast_splines_2025 import OUT as FIT
from hour_table_conditioner_2025 import feature_rows
from intraday_offer_bids_2025 import TIMEZONES
from monthly_lp_spline_inputs_2025 import aligned
from sigmoid_month_pairs_2025 import ROOT, digest


OUT = ROOT/'data/bidding-zone-network-2025/monthly-fast-curves-rate2-20-v1'
UTILIZATION = np.linspace(0, 1, 6)
EXAMPLES = {
    'DE-LU': ('gas', 'hard_coal', 'lignite', 'oil', 'onshore_wind', 'solar'),
    'FR': ('nuclear', 'gas', 'oil', 'onshore_wind', 'solar'),
}


def hour_for_local_month(zone, month):
    local = pd.Timestamp(f'2025-{month:02d}-15 18:00').tz_localize(TIMEZONES[zone[:2]])
    utc = local.tz_convert('UTC')
    hour = int((utc-pd.Timestamp('2025-01-01',tz='UTC'))/pd.Timedelta(hours=1))
    if not 0 <= hour < 8760:
        raise ValueError('Representative hour outside 2025')
    return hour, local.isoformat(), utc.isoformat()


def ready():
    if any(FIT.glob('failure*.json')):
        raise RuntimeError('Monthly fast fit failed; inspect failure receipts before curve export')
    return (FIT/'complete.json').exists() and all(
        (FIT/f'month-{month:02d}/complete.json').exists() for month in range(1,13))


def export():
    if not ready():
        raise RuntimeError('Twelve completed monthly fits are required for a cross-month figure')
    source = json.loads((FIT/'sources.json').read_text())
    changed = [path for path, sha in source.items() if digest(ROOT/path) != sha]
    if changed:
        raise ValueError('Fit source changed: '+', '.join(changed[:4]))
    _, state, market, _, _ = aligned()
    schema, data, _, _, _ = state
    market.reference = np.maximum(market.capacity.max(axis=0), .001)
    groups = schema['groups']
    rows = []
    witnesses = {}
    for month in range(1,13):
        folder = FIT/f'month-{month:02d}'
        receipt = json.loads((folder/'complete.json').read_text())
        saved = folder/'state-020.npz'
        if digest(saved) != receipt['final_state_sha256']:
            raise ValueError(f'Month {month} final state hash mismatch')
        witnesses[f'{month:02d}'] = digest(saved)
        with np.load(saved) as final:
            weights = final['weights'].copy()
            centers = final['centers'].copy()
        for zone in schema['zones']:
            hour, local, utc = hour_for_local_month(zone, month)
            X, _ = feature_rows(groups, data, np.array([hour]), market.reference, centers=centers)
            theta = np.einsum('tgf,gfk->tgk', X, weights)
            offers = market.offers(theta, np.array([hour]))
            for group_id, group in enumerate(groups):
                if group['zone'] != zone:
                    continue
                mw = float(market.capacity[hour, group_id]*1000)
                for u, price in zip(UTILIZATION, offers['anchors'][0,group_id]):
                    rows.append(dict(month=month, zone=zone, technology=group['technology'],
                        group_id=group_id, local_time=local, utc_time=utc, utc_hour=hour,
                        available_mw=mw, utilization_fraction=float(u),
                        cumulative_available_mw=float(u*mw), marginal_bid_eur_mwh=float(price),
                        zero_bid=bool(market.zero[group_id])))
    OUT.mkdir(exist_ok=True)
    csv_path = OUT/'all-zone-technology-monthly-curves-local-18.csv'
    with csv_path.open('w', newline='') as output:
        writer=csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    fig, axes = plt.subplots(2,6,figsize=(21,7),sharex=True)
    cmap=plt.get_cmap('viridis',12)
    for row, (zone, technologies) in enumerate(EXAMPLES.items()):
        for col, technology in enumerate(technologies):
            ax=axes[row,col]
            for month in range(1,13):
                sample=[item for item in rows if item['zone']==zone and
                    item['technology']==technology and item['month']==month]
                if sample:
                    ax.plot([100*x['utilization_fraction'] for x in sample],
                        [x['marginal_bid_eur_mwh'] for x in sample],
                        color=cmap(month-1),linewidth=1.3,label=f'{month:02d}')
            ax.set_title(f'{zone} · {technology.replace("_"," ")}')
            ax.grid(alpha=.2)
            if row==1:ax.set_xlabel('Share of hourly available MW (%)')
            if col==0:ax.set_ylabel('Marginal bid (€/MWh)')
        for col in range(len(technologies),6):axes[row,col].set_visible(False)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,title='Month',loc='lower center',ncol=12,bbox_to_anchor=(.5,-.03))
    fig.suptitle('Fitted fast-market offers at 18:00 local on each month’s 15th day')
    fig.tight_layout(rect=(0,.035,1,.95))
    figure=OUT/'example-monthly-curves.png';fig.savefig(figure,dpi=160,bbox_inches='tight');plt.close(fig)
    report=OUT/'report.md'
    report.write_text(
        '# Fitted monthly supply curves at a fixed local hour\n\n'
        'These are **fast transport-model bid functions**, not reconstructed exchange orders '
        'or an annual physical-LP result. Each line is the fitted marginal bid at 18:00 '
        'local on the 15th of a month, evaluated at 0, 20, 40, 60, 80 and 100% of '
        'that hour’s available MW. Calendar day, availability and fuel cost can therefore '
        'affect the plotted bid. The CSV includes the actual available MW and all modeled '
        'zones and technologies. Wind, solar and run-of-river bids are fixed near zero; '
        'reservoir hydro is a fixed injection outside these fitted offer groups. '
        'The curves were fit on each same month’s observed prices and monthly generation, '
        'so this figure is an in-sample description, not forward validation.\n\n'
        '![Monthly bid curves](example-monthly-curves.png)\n\n'
        '[All-zone curve data](all-zone-technology-monthly-curves-local-18.csv)\n')
    manifest=dict(status='complete',fit_source_sha256=digest(FIT/'sources.json'),
        fit_complete_sha256=digest(FIT/'complete.json'),month_state_sha256=witnesses,
        rows=len(rows),csv_sha256=digest(csv_path),figure_sha256=digest(figure),
        local_hour=18,local_day=15,points_per_curve=6)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--wait',action='store_true',help='Wait for the running monthly fit')
    args=parser.parse_args()
    if args.wait:
        while not ready():time.sleep(30)
    export()
