"""Plot all compared countries' individual-node conditional price error ranges."""
import argparse,json,math
from pathlib import Path
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(source,output):
    report=json.loads(source.read_text())
    if report['status']!='provisional_fixed_inventory_price_diagnostic_not_validation' or any(report['acceptance'].values()):
        raise ValueError('Explicit provisional diagnostic required')
    groups=defaultdict(list)
    for row in report['nodes']:
        if row['status']=='conditional_nodal_vs_observed_zonal_diagnostic_not_validation':groups[row['country']].append(row)
    names=sorted(groups)
    if not names:raise ValueError('No compared countries')
    fig,axes=plt.subplots(1,2,figsize=(10,max(5,len(names)*.3)),sharey=True,layout='constrained')
    for i,name in enumerate(names):
        rows=groups[name]
        for ax,key,color in zip(axes,('bias_eur_mwh','mae_eur_mwh'),('#0369a1','#b45309')):
            values=[r[key] for r in rows]
            if not all(math.isfinite(v) for v in values):raise ValueError('Nonfinite node error')
            ax.plot([min(values),max(values)],[i,i],color=color,linewidth=3)
            ax.scatter(values,[i]*len(values),color=color,s=12,alpha=.6)
    axes[0].set_yticks(range(len(names)),[f'{n} ({len(groups[n])} nodes)' for n in names]);axes[0].invert_yaxis()
    axes[0].set_title('Signed bias');axes[1].set_title('Mean absolute error')
    for ax in axes:
        ax.set_xlabel('€/MWh');ax.axvline(0,color='#64748b',linewidth=.7);ax.grid(axis='x',alpha=.2)
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('2025 fixed-inventory nodal vs observed zonal prices\nDots: individual nodes; lines: min–max across nodes, not uncertainty intervals')
    fig.savefig(output,format='svg',metadata={'Date':None,'Description':'All provisionally compared national country groups; no accepted zonal aggregation, calibration or annual-optimum claim.'});plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();plot(a.source,a.output)
