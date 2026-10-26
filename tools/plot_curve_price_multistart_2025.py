"""Plot two independently audited selected fast-market bid examples."""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from export_monthly_fast_curves_2025 import hour_for_local_month
from fit_batched_transport_all_months_2025 import direct_market
from hour_table_conditioner_2025 import feature_rows
from monthly_lp_spline_inputs_2025 import aligned
from sigmoid_month_pairs_2025 import ROOT


FIT=ROOT/'data/bidding-zone-network-2025/curve-price-multistart-10-v1'
FIGURE=ROOT/'research/assets/curve-price-multistart-selected-2025.png'
PANELS={'DE-LU':('gas','hard_coal','oil','solar'),
        'FR':('nuclear','gas','oil','solar')}


def run():
    audited=json.loads((FIT/'independent-audit.json').read_text())
    if audited['status']!='complete':raise ValueError('Independent audit required')
    _,state,source,_,_=aligned();s,d,*_=state
    market=direct_market(source)
    fig,axes=plt.subplots(2,4,figsize=(14,6),sharex=True)
    for row,(zone,technologies) in enumerate(PANELS.items()):
        for col,technology in enumerate(technologies):
            ax=axes[row,col]
            groups=[i for i,g in enumerate(s['groups']) if g['zone']==zone and g['technology']==technology]
            if len(groups)!=1:raise ValueError('Expected one zone-resource group')
            group=groups[0]
            for month,color in ((1,'#2764ad'),(4,'#d46335')):
                start=audited['selected_by_in_sample_joint_data_loss'][str(month)]
                file=FIT/f'{start}-month-{month:02d}'/f'month-{month:02d}'/'state-010.npz'
                with np.load(file) as z:weights=z['weights'];centers=z['centers']
                hour,_,_=hour_for_local_month(zone,month)
                X,_=feature_rows(s['groups'],d,np.array([hour]),market.reference,centers=centers)
                theta=np.einsum('tgf,gfk->tgk',X,weights)
                offer=market.offers(theta,np.array([hour]))
                available=market.capacity[hour,group]*1000
                ax.plot(np.linspace(0,100,6),offer['anchors'][0,group],marker='o',
                    markersize=2.5,color=color,label=f'{month:02d}: {available:,.0f} MW')
            ax.set_title(zone+' · '+technology.replace('_',' '))
            ax.grid(alpha=.2)
            ax.legend(fontsize=7)
            if row==1:ax.set_xlabel('Share of available output (%)')
            if col==0:ax.set_ylabel('Marginal bid (€/MWh)')
    fig.suptitle('Selected in-sample fitted offers · 18:00 local on 15 January/April 2025')
    fig.tight_layout()
    fig.savefig(FIGURE,dpi=145,bbox_inches='tight')
    plt.close(fig)
    print(FIGURE)


if __name__=='__main__':run()
