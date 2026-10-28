"""Write compact figures and evidence table for audited monthly fits."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from flow_adjusted_zonal_clearing_2025 import DEST
from monthly_diurnal_splines_2025 import labels
from run_batched_transport_2025 import setup

ROOT=Path(__file__).resolve().parent.parent
FIT=DEST/'monthly-fit-v1-u100-r0.1'
ASSETS=ROOT/'research/assets'


def main():
    audit=json.loads((FIT/'audit.json').read_text())
    summaries=[json.loads((FIT/f'month-{m:02d}/summary.json').read_text()) for m in range(1,13)]
    months=np.arange(1,13)
    initial=np.array([s['initial_cleared']['price_mae'] for s in summaries]);final=np.array([s['fitted_cleared']['price_mae'] for s in summaries])
    g0=np.array([s['initial_cleared']['generation_mae_gw'] for s in summaries]);g1=np.array([s['fitted_cleared']['generation_mae_gw'] for s in summaries])
    fig,axes=plt.subplots(2,1,figsize=(9,6),sharex=True)
    axes[0].plot(months,initial,'o-',label='Neutral bids');axes[0].plot(months,final,'o-',label='Month fit')
    axes[0].set_ylabel('Price MAE (€/MWh)');axes[0].legend()
    axes[1].plot(months,g0,'o-',label='Neutral bids');axes[1].plot(months,g1,'o-',label='Month fit')
    axes[1].set_ylabel('Hourly technology generation MAE (GW)');axes[1].set_xlabel('2025 month')
    axes[1].set_xticks(months)
    for ax in axes:ax.grid(alpha=.25)
    fig.tight_layout();ASSETS.mkdir(exist_ok=True);fig.savefig(ASSETS/'flow-adjusted-monthly-errors-2025.png');plt.close(fig)

    histories=[json.loads((FIT/f'month-{m:02d}/history.json').read_text()) for m in range(1,13)]
    steps=np.arange(101)
    price_hist=np.array([[r['price_mae'] for r in h] for h in histories])
    gen_hist=np.array([[r['generation_mae_gw'] for r in h] for h in histories])
    fig,axes=plt.subplots(1,2,figsize=(10,3.5))
    axes[0].plot(steps,np.median(price_hist,axis=0));axes[0].set_ylabel('Median within-month price MAE (€/MWh)')
    axes[1].plot(steps,np.median(gen_hist,axis=0));axes[1].set_ylabel('Median within-month generation MAE (GW)')
    for ax in axes:ax.set_xlabel('Adam update');ax.grid(alpha=.25)
    fig.tight_layout();fig.savefig(ASSETS/'flow-adjusted-training-2025.png');plt.close(fig)

    state,market,_,_=setup();s,d,*_=state
    technologies=('gas','hard_coal','oil')
    fig,axes=plt.subplots(1,3,figsize=(12,3.8),sharex=True)
    for month in (1,4,7,10):
        stamp=np.datetime64(f'2025-{month:02d}-15T18','h')
        hour=int((stamp-np.datetime64('2025-01-01T00','h'))/np.timedelta64(1,'h'))
        with np.load(FIT/f'month-{month:02d}/curves.npz') as z:weights=z['weights']
        clock=labels(s['groups'],np.array([hour]))
        theta=weights[clock,np.arange(market.ng)]
        offers=market.offers(theta,np.array([hour]))
        for ax,tech in zip(axes,technologies):
            ids=[j for j,g in enumerate(s['groups']) if g['zone']=='DE-LU' and g['technology']==tech]
            if not ids:continue
            j=ids[0]
            ax.plot(np.arange(0,101,20),offers['anchors'][0,j],marker='o',label=f'{month:02d} ({offers["capacity"][0,j]:.1f} GW)')
            ax.set_title('DE-LU '+tech.replace('_',' '));ax.set_xlabel('% of hour-available output');ax.grid(alpha=.25)
    axes[0].set_ylabel('Bid anchor price (€/MWh)')
    for ax in axes:ax.legend(title='Month (capacity)',fontsize=7)
    fig.tight_layout();fig.savefig(ASSETS/'flow-adjusted-example-curves-2025.png');plt.close(fig)

    zones=sorted((r for r in audit['per_zone'] if r['matched_hours']),
                 key=lambda r:r['fitted_price_mae_eur_mwh'])
    fig,ax=plt.subplots(figsize=(9,9))
    ypos=np.arange(len(zones))
    ax.barh(ypos,[r['fitted_price_mae_eur_mwh'] for r in zones])
    ax.set_yticks(ypos,[f"{r['zone']} ({r['matched_hours']:,} h)" for r in zones],fontsize=8)
    ax.set_xlabel('Within-month fitted price MAE (€/MWh)');ax.grid(axis='x',alpha=.25)
    fig.tight_layout();fig.savefig(ASSETS/'flow-adjusted-zonal-errors-2025.png');plt.close(fig)

    forward=json.loads((FIT/'forward.json').read_text())
    rows=forward['rows'];x=np.array([r['test_month'] for r in rows])
    fig,ax=plt.subplots(figsize=(9,3.8))
    for key,label in [('neutral_price_mae','Neutral bids'),('within_month_price_mae','Same-month fit'),('price_mae','Prior-month bids')]:
        ax.plot(x,[r[key] for r in rows],marker='o',label=label)
    ax.set_xlabel('Test month, 2025');ax.set_ylabel('Price MAE (€/MWh)');ax.set_xticks(x)
    ax.grid(alpha=.25);ax.legend();fig.tight_layout()
    fig.savefig(ASSETS/'flow-adjusted-forward-2025.png');plt.close(fig)

    weights=np.array([s['fitted_cleared']['matched_price_cells'] for s in summaries])
    gw=np.array([s['fitted_cleared']['generation_cells'] for s in summaries])
    result=dict(price_mae_neutral=float(np.average(initial,weights=weights)),price_mae_fitted=float(np.average(final,weights=weights)),
        generation_mae_neutral_gw=float(np.average(g0,weights=gw)),generation_mae_fitted_gw=float(np.average(g1,weights=gw)),
        matched_price_cells=int(weights.sum()),generation_cells=int(gw.sum()),
        total_fit_seconds=sum(s['total_seconds'] for s in summaries),
        verified_months=audit['months'])
    (FIT/'aggregate.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
