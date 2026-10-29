"""Plot one verified hour's accepted offer steps and transferred monthly bids."""
import csv
import json
from datetime import datetime, timezone

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from generation_mix_2025 import ROOT, digest
from hour_table_conditioner_2025 import feature_rows
from monthly_fast_lp_costs_2025 import offer_groups
from monthly_lp_spline_inputs_2025 import aligned
from run_mixed_flow_fast_joint_lp_2025 import FIT, OUT, inputs
from solar_anchor_bids_2025 import model

STAMP='2025-01-20T12:00:00+00:00'
HOUR=int((datetime.fromisoformat(STAMP)-datetime(2025,1,1,tzinfo=timezone.utc)).total_seconds()/3600)
PANELS=[('DE-LU','gas'),('DE-LU','hard_coal'),('DE-LU','lignite'),
        ('DE-LU','oil'),('DE-LU','biomass'),('FR','nuclear')]
FIG=ROOT/'research/assets/monthly-bids-vs-baseline-2025.png'
TABLE=ROOT/'research/monthly-bids-vs-baseline-2025.csv'


def steps(cap,price):
    order=np.argsort(price,kind='stable');width=cap[order]
    x=np.r_[0,np.cumsum(width)]/width.sum()*100
    y=price[order]
    return x,y


def run():
    inputs()
    sealed=json.loads((OUT/'inputs.json').read_text())
    if digest(OUT/'costs.npz')!=sealed['costs_sha256']:
        raise ValueError('Changed transferred offer costs')
    _,state,market,_,_=aligned();schema,data,*_=state
    _,accepted,lp=model();grouped,_=offer_groups(schema,accepted,lp)
    with np.load(FIT/'month-01/curves.npz') as z:weights=z['weights']
    with np.load(OUT/'costs.npz') as z:transferred=z['cost'][HOUR]
    if weights.shape!=(24,market.ng,6):raise ValueError('Changed curve shape')
    X,_=feature_rows(schema['groups'],data,np.array([HOUR]),
        np.maximum(market.capacity.max(axis=0),.001),np.zeros((market.ng,2)))
    theta=np.einsum('tgf,gfk->tgk',X, np.pad(weights.transpose(1,0,2),((0,0),(0,2),(0,0))))
    anchors=market.offers(theta,np.array([HOUR]))['anchors'][0]
    lookup={(row['zone'],row['technology']):g for g,row in enumerate(schema['groups'])}
    fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    rows=[]
    for ax,(zone,tech) in zip(axes.ravel(),PANELS):
        g=lookup[(zone,tech)];ids=grouped[g]
        if not ids:raise ValueError('No pure LP offer columns for '+str((zone,tech)))
        cap=lp['availability'][HOUR,ids]
        keep=cap>1e-8;cap=cap[keep];columns=np.array(ids)[keep]
        if not len(cap):raise ValueError('Zero available offer capacity')
        baseline=lp['cost'][HOUR,columns];mapped=transferred[columns]
        xb,yb=steps(cap,baseline);xm,ym=steps(cap,mapped)
        ax.stairs(yb,xb,label='Accepted offer steps',color='#334155',lw=1.6)
        ax.stairs(ym,xm,label='Transferred LP offer steps',color='#d97706',lw=1.6)
        ax.plot(np.linspace(0,100,6),anchors[g],'-o',label='Learned six-anchor curve',
                color='#2563eb',lw=2.1,ms=3.5)
        ax.set(xlim=(0,100),title=f'{zone} · {tech.replace("_"," ")}',
               xlabel='Share of this hour’s available MW',ylabel='Bid EUR/MWh')
        ax.grid(alpha=.18)
        rows.append(dict(zone=zone,technology=tech,hour_utc=STAMP,
            available_mw=float(cap.sum()),pure_offer_columns=len(columns),
            accepted_bid_min=float(baseline.min()),accepted_bid_max=float(baseline.max()),
            transferred_bid_min=float(mapped.min()),transferred_bid_max=float(mapped.max()),
            **{f'learned_anchor_{i*20}_eur_mwh':float(anchors[g,i]) for i in range(6)}))
    handles,labels=axes.ravel()[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',ncol=3,bbox_to_anchor=(.5,1.045),frameon=False)
    fig.suptitle('20 January 2025, 12:00 UTC · accepted source capacity and joint LP',y=1.095,fontsize=14)
    FIG.parent.mkdir(exist_ok=True)
    fig.savefig(FIG,dpi=160,bbox_inches='tight');plt.close(fig)
    with TABLE.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(FIG.relative_to(ROOT),TABLE.relative_to(ROOT))


if __name__=='__main__':run()
