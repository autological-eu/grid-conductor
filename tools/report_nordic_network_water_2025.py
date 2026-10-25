"""Compact local plots/CSV from independently verified Nordic diagnostics."""
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_network_stock_retiming_2025 import OUT,WATER,NORWAY
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json

def run():
 summary=json.loads((OUT/'summary.json').read_text());audit=json.loads((OUT/'audit.json').read_text());assert audit['summary_sha256']==digest(OUT/'summary.json')
 water=json.loads((WATER/'summary.json').read_text());no=json.loads((NORWAY/'summary.json').read_text());rows=[]
 fig,axes=plt.subplots(2,1,figsize=(15,8),sharex=True)
 for month,ax in zip([1,2],axes):
  controls=water['cases'][month-1]['zones'];zones=[r['zone'] for r in controls];x=np.arange(len(zones));before=np.array([r['before_mae'] for r in controls]);watermae=np.array([r['after_mae'] for r in controls])
  ax.plot(x,before,'o-',ms=3,label='Original frozen model');ax.plot(x,watermae,'o-',ms=3,label='NO+SE stock reconstruction')
  for case in summary['cases']:
   record=next(r for r in case.get('months',[]) if r['month']==month)
   if 'metrics' not in record:continue
   ax.plot(x,[r['after_mae'] for r in record['zones']],'o-',ms=3,label=case['endpoint']+' + water retiming')
   for r in record['zones']:rows.append(dict(month=month,endpoint=case['endpoint'],original_mae=float(before[zones.index(r['zone'])]),**r))
  ax.set(title='January' if month==1 else 'February',ylabel='Price MAE EUR/MWh');ax.grid(axis='y',alpha=.25);ax.legend(fontsize=8,ncol=2)
 axes[-1].set(xticks=x,xticklabels=zones);axes[-1].tick_params(axis='x',rotation=90);fig.tight_layout();fig.savefig(OUT/'all-zone-price-mae.png',dpi=150);plt.close(fig)
 with (OUT/'zone-comparison.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 aggregate=[]
 for case in summary['cases']:
  for record in case.get('months',[]):
   if 'metrics' not in record:continue
   z=record['zones'];north=lambda x:x.startswith(('NO','SE','DK')) or x=='FI'
   aggregate.append(dict(endpoint=case['endpoint'],month=record['month'],europe_mae=record['metrics']['price_mae'],nordic_mae=float(np.mean([r['after_mae'] for r in z if north(r['zone'])])),other_mae=float(np.mean([r['after_mae'] for r in z if not north(r['zone'])])),nordic_water_only_mae=float(np.mean([r['water_only_mae'] for r in z if north(r['zone'])])),other_water_only_mae=float(np.mean([r['water_only_mae'] for r in z if not north(r['zone'])]))))
 atomic_json(OUT/'report-data.json',dict(aggregates=aggregate,summary_sha256=digest(OUT/'summary.json'),audit_sha256=digest(OUT/'audit.json'),producer_sha256=digest(__file__)))
 lines=['# Nordic water and border reconciliation','','Goal OPEN. Frozen bids;48 modeled European areas/41 complete hourly ENTSO-E price targets, all1416Jan/Feb hours.','', '| Case | January MAE | February MAE |','|---|---:|---:|','| Original |21.9535|31.6688|','| Norway stock anchoring |22.6023|26.4329|','| Norway + Sweden stocks |20.6759|24.8520|']
 for case in summary['cases']:
  scores={r['month']:r['metrics']['price_mae'] for r in case.get('months',[]) if 'metrics' in r};lines.append('| '+case['endpoint']+' + retiming |'+ '|'.join(f'{scores[m]:.4f}' if m in scores else 'FAILED' for m in [1,2])+'|')
 lines+=['','![Every price zone, gains and regressions](all-zone-price-mae.png)','','[Per-zone price MAE and signed bias](zone-comparison.csv)','','Published max-border-flow and max-exchange are independent directional envelope CONTROLS, not exact FB domains, not verified NTC and not interchangeable.118raw daily responses cover both endpoints1416hours with SHA receipts. Incompatible source bounds are rejected; original unmapped corridors remain explicit. No ad-hoc capacity derating.','','Applying them to the fixed stock-corrected schedule initially produced200/136infeasible hours. A separate minimum-slack LP diagnosed surplus .214153/.109555TWh, no deficit. That slack is not used as emergency supply or a price forecast. Offline network/water projection retimes existing hydro while preserving each country monthly energy, January and February end stocks, inflow/spill/turbine bounds and original generation availability. No observed price enters the projection; zero interior margin used. Both controls then pass all1416hour feasibility checks and independent full market replay.','','Price improvement does not establish a complete Nordic fix: Denmark worsens and positive SE2 bias persists. Bid coefficients remain January-fitted at February-development-selected1.0/update29; these are controlled retrospective input diagnostics, not untouched forward tests. Swedish inflow may depend on production accounting; unchanged ROR sources and geographic capacity shares remain limitations. Missing Swedish weeks14/27 prevent annual input release. No annual corrected price score, public deployment or baseline promotion.']
 (OUT/'report.md').write_text('\n'.join(lines)+'\n');print(json.dumps(aggregate),flush=True)
if __name__=='__main__':run()
