"""Publish compact renewable reconstruction diagnostics and reproducible SVGs."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def run():
    root=Path('data/pypsa-eur/hourly-renewable-estimates-v1')
    report=json.loads((root/'summary.json').read_text())
    out=Path('public/research/hourly-renewables-2025');out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    plt.rcParams.update({'svg.fonttype':'none','font.size':10})
    selected=['DE','FR','ES','PL']
    fig,axes=plt.subplots(2,4,figsize=(15,7),sharex=True)
    for i,tech in enumerate(['wind','solar']):
        for j,country in enumerate(selected):
            row=next(r for r in report['countries'] if r['country']==country and r['technology']==tech)
            ax=axes[i,j];ax.plot(range(1,13),[m['available_energy_mwh']/1e6 for m in row['months']],label='Weather availability')
            ax.plot(range(1,13),[np.nan if m['observed_generation_mwh'] is None else m['observed_generation_mwh']/1e6 for m in row['months']],label='Ember generation')
            ax.set_title(country+' '+tech);ax.set_ylabel('TWh/month');ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8);fig.suptitle('Available energy versus observed generation — different quantities, no forced fit')
    fig.tight_layout();fig.savefig(out/'monthly.svg');plt.close(fig)
    with np.load(root/'hourly.npz') as data:
        fig,axes=plt.subplots(2,1,figsize=(12,6))
        for ax,tech in zip(axes,['wind','solar']):
            # First week in June; reconstruction uses the whole June total.
            start=3624;stop=start+168
            ax.plot(np.arange(168),data['FR_'+tech+'_available_mw'][start:stop]/1000,label='Original availability')
            ax.plot(np.arange(168),data['FR_'+tech+'_reconstructed_generation_mw'][start:stop]/1000,label='Monthly-constrained estimate')
            ax.set_title('France '+tech+' · 1–7 June 2025 UTC');ax.set_ylabel('GW');ax.grid(alpha=.2);ax.legend()
        axes[-1].set_xlabel('Hour from 1 June 00:00 UTC');fig.tight_layout();fig.savefig(out/'hourly.svg');plt.close(fig)
    statuses={}
    for row in report['countries']:
        for m in row['months']:statuses[m['status']]=statuses.get(m['status'],0)+1
    print('series',len(report['countries']),'countries',len({r['country'] for r in report['countries']}),'months',statuses)
    for c in selected:
        for t in ['wind','solar']:
            r=next(r for r in report['countries'] if r['country']==c and r['technology']==t)
            obs=[m['observed_generation_mwh'] for m in r['months']]
            print(c,t,round(r['capacity_mw']/1000,3),round(r['available_energy_mwh']/1e6,3),None if any(v is None for v in obs) else round(sum(obs)/1e6,3))
if __name__=='__main__':run()
