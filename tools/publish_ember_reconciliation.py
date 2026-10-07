"""Publish current-release reference separately from retained old pilot evidence."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reconcile_ember_release import read_generation
from hourly_renewable_estimates import digest


def run():
    root=Path('data/pypsa-eur/ember-current-release')
    audit=json.loads((root/'reconciliation.json').read_text())
    if digest(root/'monthly.csv')!=audit['current_sha256']:raise ValueError('Current source changed')
    out=Path('public/research/irena-capacity-2025')
    compact={k:v for k,v in audit.items() if k not in ['changes','old_only','current_only']}
    compact['old_only_records']=len(audit['old_only']);compact['current_only_records']=len(audit['current_only'])
    (out/'ember-release-reconciliation.json').write_text(json.dumps(compact,indent=2)+'\n')
    current=read_generation(root/'monthly.csv',True)
    original=json.loads((out/'summary.json').read_text())
    updated=json.loads(json.dumps(original))
    import pycountry
    for r in updated['wind_solar_comparison']:
        c='XKX' if r['country']=='XK' else pycountry.countries.get(alpha_2=r['country']).alpha_3
        values=[current.get((c,r['technology'],f'2025-{m:02d}-01')) for m in range(1,13)]
        r['observed_generation_mwh']=None if any(v is None for v in values) else sum(values)*1e6
    updated['current_ember_sha256']=audit['current_sha256'];updated['current_ember_url']=audit['current_url']
    updated['reference_note']='Current Ember generation reference; original capacity variants unchanged. Earlier summary.json retained.'
    (out/'current-reference-summary.json').write_text(json.dumps(updated,indent=2)+'\n')
    plt.rcParams['svg.fonttype']='none';fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,t in zip(axes,['wind','solar']):
        rows=[next(v for v in updated['wind_solar_comparison'] if v['country']==c and v['technology']==t) for c in ['DE','FR','ES','PL']]
        for i,k in enumerate(['source_available_mwh','linear','observed_generation_mwh']):
            vals=[(v['variants']['linear_2025']['annual_available_mwh'] if k=='linear' else v[k])/1e6 for v in rows]
            ax.bar([j+(i-1)*.25 for j in range(4)],vals,width=.25,label=['Original available','IRENA linear capacity available','Current Ember generated'][i])
        ax.set_xticks(range(4),['DE','FR','ES','PL']);ax.set_title(t);ax.set_ylabel('TWh in 2025');ax.legend(fontsize=8)
    fig.tight_layout();p=out/'current-reference-comparison.svg';fig.savefig(p)
    p.write_text('\n'.join(l.rstrip() for l in p.read_text().splitlines())+'\n')
if __name__=='__main__':run()
