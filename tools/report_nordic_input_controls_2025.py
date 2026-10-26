"""Concise comparisons for the completed demand/ROR/source-method diagnostics."""
import csv,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json
BASE=ROOT/'data/bidding-zone-network-2025'
OUT=BASE/'nordic-input-controls-report-v1'
def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'summary.json').exists():raise ValueError('Existing report sealed')
 paths={'previous':BASE/'nordic-network-stock-retiming-v1','demand':BASE/'norway-demand-controls-v1','ror':BASE/'nordic-ror-reconciliation-v1'};studies={};pins={str(__import__('pathlib').Path(__file__).relative_to(ROOT)):digest(__file__)}
 for key,folder in paths.items():
  studies[key]=json.loads((folder/'summary.json').read_text());audit=json.loads((folder/'audit.json').read_text());assert audit['summary_sha256']==digest(folder/'summary.json')
  for p in [folder/'summary.json',folder/'audit.json']:pins[str(p.relative_to(ROOT))]=digest(p)
 for p in [paths['ror']/'river-audit.json',paths['ror']/'river-inputs.json',ROOT/'data/bidding-zone-source-audit-2025/nve-stock-aggregation-v1/summary.json']:pins[str(p.relative_to(ROOT))]=digest(p)
 source=ROOT/'data/pypsa-eur/ember-current-release/monthly.csv';receipt=json.loads(source.with_name('receipt.json').read_text());assert digest(source)==receipt['sha256'];pins[str(source.relative_to(ROOT))]=digest(source);ember=pd.read_csv(source,usecols=['Date','ISO 3 code','Area type','Electricity source','Generation (TWh)']);ember=ember[ember['Area type'].str.lower().str.startswith('country')&ember['Electricity source'].eq('Hydro')];s=json.loads((BASE/'sigmoid-month-pairs-v1/inputs.json').read_text());rows=[];hydro=[]
 for kind in ['previous','demand','ror']:
  endpoint='metered_proportional_scope_control' if kind=='demand' else 'maxBorderFlow';case=next(c for c in studies[kind]['cases'] if c.get('endpoint',c.get('kind'))==endpoint)
  for record in case['months']:
   month=record['month'];rows.append(dict(case=kind,month=month,price_mae=record['metrics']['price_mae'],generation_mae_twh=record['metrics']['generation_mae_twh']))
   path=paths[kind]/f'{endpoint}-{month:02d}.npz';pins[str(path.relative_to(ROOT))]=digest(path)
   with np.load(path) as z:gen=z['generation']
   for country,iso in [('NO','NOR'),('SE','SWE'),('FI','FIN')]:
    match=ember[ember['ISO 3 code'].eq(iso)&ember.Date.str.startswith(f'2025-{month:02d}')];assert len(match)==1;target=float(match['Generation (TWh)'].iloc[0]);ids=[s['technologies'].index(t) for t in ['reservoir','ror']];value=float(gen[:,s['countries'].index(country),ids].sum()/1e6);hydro.append(dict(case=kind,month=month,country=country,modeled_hydro_twh=value,ember_hydro_twh=target,difference_twh=value-target))
 fig,axes=plt.subplots(1,2,figsize=(11,4.2));x=np.arange(2)
 for i,kind in enumerate(['previous','demand','ror']):axes[0].bar(x+(i-1)*.24,[r['price_mae'] for r in rows if r['case']==kind],.24,label={'previous':'Stock + JAO control','demand':'Demand shares sensitivity','ror':'Consistent ROR inflow'}[kind])
 axes[0].set(xticks=x,xticklabels=['January','February'],ylabel='Europe price MAE EUR/MWh');axes[0].legend(fontsize=7)
 for i,kind in enumerate(['previous','ror']):axes[1].bar(x+(i-.5)*.28,[r['modeled_hydro_twh'] for r in hydro if r['case']==kind and r['country']=='SE'],.28,label=kind)
 axes[1].plot(x,[r['ember_hydro_twh'] for r in hydro if r['case']=='ror' and r['country']=='SE'],'ko',label='Ember observed total hydro');axes[1].set(xticks=x,xticklabels=['January','February'],ylabel='Swedish hydro TWh');axes[1].legend(fontsize=7);fig.tight_layout();fig.savefig(OUT/'input-controls.png',dpi=150);plt.close(fig)
 for name,data in [('scores',rows),('hydro',hydro)]:
  with (OUT/(name+'.csv')).open('w',newline='') as f:writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
 atomic_json(OUT/'summary.json',dict(status='verified_control_report_not_baseline_promotion',scores=rows,hydro=hydro,sources=pins));print(json.dumps(dict(scores=rows,hydro=hydro)),flush=True)
if __name__=='__main__':run()
