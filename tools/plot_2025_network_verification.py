"""Plot published matched-window evidence; no new solve or annualisation."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parents[1]
source=root/'public/research/network-benchmark-2025/comparison.json'
r=json.loads(source.read_text()); rows=r['results']
assert r['hours']==48 and r['status']=='conditional_window_objective_parity_passed_not_annual_validation'
assert [x['id'] for x in rows]==['baseline','se-pl-plus-500','battery-100-400']
for x in rows:
    assert abs((x['fast_cost_eur']-x['native_cost_eur'])-x['difference_eur'])<1e-8
out=source.parent
plt.rcParams.update({'font.size':11,'svg.fonttype':'none'})
colors=['#334155','#059669']
fig,axes=plt.subplots(1,2,figsize=(9,4),layout='constrained')
for ax,row,title in zip(axes,rows[1:],['Sweden–Poland +500 MW','Poland battery: 100 MW / 400 MWh']):
    values=[row['native_benefit_eur'],row['fast_benefit_eur']]
    ax.bar(['Native PyPSA','Fast Kirchhoff'],values,color=colors)
    ax.set_title(title);ax.set_ylabel('Operating-cost saving (€ / 48 h)')
    ax.set_ylim(0,max(values)*1.25)
    for i,v in enumerate(values):ax.text(i,v,f'€{v:,.2f}',ha='center',va='bottom')
fig.suptitle('Matched intervention savings · 1–2 January 2025\nSeparate vertical scales; not annual benefits',fontsize=13)
fig.savefig(out/'verification-benefits.svg');plt.close(fig)
fig,ax=plt.subplots(figsize=(8,3.6),layout='constrained')
labels=['Baseline','Transmission +500 MW','Battery 100 MW / 400 MWh']
values=[abs(x['difference_eur']) for x in rows]
ax.barh(labels,values,color=colors[1]);ax.set_xscale('log');ax.axvline(.01,color='#dc2626',linestyle='--',label='€0.01 acceptance threshold')
ax.set_xlim(1e-6,.03);ax.set_xlabel('Absolute fast minus native total cost (€; logarithmic scale)')
for i,v in enumerate(values):ax.text(v*1.15,i,f'€{v:.8f}',va='center',fontsize=10)
ax.set_title('All three matched objective differences are below one cent');ax.legend(loc='lower right')
fig.savefig(out/'verification-errors.svg');plt.close(fig)
fig,ax=plt.subplots(figsize=(8,3.8),layout='constrained')
for i,(key,name,color) in enumerate([('native_seconds','Native PyPSA',colors[0]),('fast_seconds','Fast Kirchhoff',colors[1])]):
    values=[x[key] for x in rows];ys=[j+(i-.5)*.35 for j in range(3)]
    ax.barh(ys,values,height=.33,label=name,color=color)
    for y,v in zip(ys,values):ax.text(v+.3,y,f'{v:.2f}s',va='center',fontsize=10)
ax.set_yticks(range(3),labels);ax.set_xlim(0,34);ax.set_xlabel('Recorded elapsed time (seconds)');ax.legend()
ax.set_title('Recorded single-trial timings · no demonstrated speed advantage\nConcurrent workloads and solver/thread settings differ',fontsize=12)
fig.savefig(out/'verification-timings.svg');plt.close(fig)
print('Generated three SVG figures from comparison SHA-256 '+hashlib.sha256(source.read_bytes()).hexdigest())
