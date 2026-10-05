"""Plot published numerical annual lower/upper bounds; no optimum implied."""
import argparse,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(previous,current,output):
    old=json.loads(previous.read_text());new=json.loads(current.read_text())
    rows=[old,new]
    if (old['status']!='annual_numerical_bounds_not_converged'
            or new['status']!='replayed_economic_annual_bounds_not_validated'
            or old['input_sha256']!=new['input_sha256']):raise ValueError('Source-matched replayed annual bound reports required')
    fig,ax=plt.subplots(figsize=(8,4.8),layout='constrained')
    for i,row in enumerate(rows):
        low=row['lower_support_eur']/1e9;high=row['annual_feasible_cost_eur']/1e9
        if not all(math.isfinite(v) for v in (low,high)) or not 0<=low<=high:raise ValueError('Invalid numerical bounds')
        ax.plot([i,i],[low,high],color='#64748b',linewidth=5,alpha=.55)
        ax.scatter(i,low,color='#0369a1',s=70,label='Replayed lower support' if i==0 else None,zorder=3)
        ax.scatter(i,high,color='#15803d',marker='s',s=70,label='Feasible annual cost' if i==0 else None,zorder=3)
        ax.annotate(f'€{high:.3f}bn',(i,high),xytext=(12,0),textcoords='offset points',va='center')
        ax.annotate(f'€{low:.3f}bn',(i,low),xytext=(12,0),textcoords='offset points',va='center')
        ax.annotate(f'Gap {(high-low)/high:.2%}',(i,(high+low)/2),xytext=(12,0),textcoords='offset points',va='center',color='#475569')
    ax.set_xticks([0,1],['Initial relaxation','Economic calendar + new cuts'])
    ax.set_xlim(-.35,1.65);ax.set_ylim(0,56);ax.set_ylabel('Annual model operating cost (€ billion)')
    ax.set_title('2025 numerical bounds: feasible dispatch, unresolved optimisation gap')
    ax.grid(axis='y',alpha=.2);ax.legend(loc='lower left');ax.spines[['top','right']].set_visible(False)
    fig.savefig(output,format='svg',metadata={'Date':None,'Description':'Floating-point numerical lower/upper bounds; not an interval certificate, empirical validation or investment benefit.'});plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('previous','current','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();plot(a.previous,a.current,a.output)
