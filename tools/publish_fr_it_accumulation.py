"""Expose published FR–Italy screening inputs without inventing interval data."""
import json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[1]
source=root/'public/research/entsoe-fast-targets.json';raw=source.read_bytes();data=json.loads(raw)
r=next(r for r in data['targets'] if r['border']=='FR>IT-North')
months=sorted([v for v in data['monthly']['rows'] if v['border']==r['border']],key=lambda v:v['month'])
assert len(months)==12
h=r['congested_quarters']*.25;s=r['average_positive_spread_eur_mwh'];k=r['slope_a']
assert sum(m['congested_quarters'] for m in months)==r['congested_quarters']
allocation=np.array([m['congested_quarters']*.25*s*s/(2*k)/1e6 for m in months])
assert abs(allocation.sum()-r['deadweight_loss_meur_year'])<1e-6
out=root/'public/research/fr-it-screening';out.mkdir(exist_ok=True)
fig,(a,b,c)=plt.subplots(3,1,figsize=(11,9),sharex=True)
x=np.arange(12);labels=[m['month'][5:] for m in months]
a.bar(x,[m['congested_quarters']*.25 for m in months],color='#0f766e');a.set(ylabel='Above-€5 event hours',title='FR → Italy North · published 2025 screening inputs')
b.plot(x,[m['average_positive_spread_eur_mwh'] for m in months],marker='o',color='#d97706');b.axhline(s,ls='--',color='#475569',label=f'Annual event mean €{s:.2f}/MWh');b.set(ylabel='Mean event spread (€/MWh)');b.legend()
c.bar(x,allocation,color='#0f766e',label='Annual bound allocated by event hours');c.plot(x,np.cumsum(allocation),marker='o',color='#b45309',label='Cumulative allocated bound');c.set(ylabel='Screening estimate (M€)',xlabel='Month of 2025 (UTC)',xticks=x,xticklabels=labels);c.legend()
fig.text(.1,.01,'Allocation uses the annual mean spread and annual slope in every event hour. It is not an observed hourly welfare series.',fontsize=9)
fig.tight_layout(rect=(0,.035,1,1));fig.savefig(out/'accumulation.svg',metadata={'Date':None});plt.close(fig)
result=dict(source_sha256=hashlib.sha256(raw).hexdigest(),annual=r,monthly=months,allocated_annual_bound_meur=allocation.tolist(),limitations=['No raw interval prices are available in this workspace.','Monthly allocations reproduce the annual mean-spread bound, not separately refitted monthly welfare.'])
(out/'explanation.json').write_text(json.dumps(result,indent=2)+'\n')
print('hours',h,'saturation MW',s/k,'500MW benefit MEUR',h*(s*500-.5*k*500**2)/1e6)
