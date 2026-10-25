"""Read-only five-rate comparison including fresh1.0/2.0 experiments."""
import json,csv,time,argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sigmoid_month_pairs_2025 import ROOT,digest
OLD=ROOT/'data/bidding-zone-network-2025/hour-table-learning-rates-v1'
OUT=ROOT/'data/bidding-zone-network-2025/higher-hour-table-learning-rates-v1'
def trial_folder(rate):return (OLD if rate<1 else OUT)/f'lr-{rate:g}'

def report():
 histories={}
 for rate in [.05,.15,.5,1.,2.]:
  p=trial_folder(rate)/'history.json'
  if p.exists():histories[rate]=json.loads(p.read_text())
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 lines=['# Local-hour supply curves: five matched Adam learning rates','',
 'Five separate January fits, each with100 updates plus initialization. February is evaluated after every update. All744January/672February hours,48 modeled areas and41 price targets remain. Rates run sequentially; partial histories are not complete comparisons.', '',
 '| Adam rate | Status | Last update | January MAE EUR/MWh | February MAE EUR/MWh |','|---|---|---:|---:|---:|']
 with (OUT/'learning-curves.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['rate','iteration','jan_price_mae','feb_price_mae','jan_mix_twh','feb_mix_twh','jan_data_loss','feb_data_loss','regularizer'])
  for rate in [.05,.15,.5,1.,2.]:
   folder=trial_folder(rate);rows=histories.get(rate,[]);status='complete' if (folder/'complete.json').exists() else 'FAILED' if (folder/'failure.json').exists() else 'running' if rows or (folder/'provenance.json').exists() else 'not started'
   if not rows:lines.append(f'| {rate} | {status} | — | — | — |');continue
   r=rows[-1];lines.append(f'| {rate} | {status} | {r["iteration"]} | {r["training"]["metrics"]["price_mae"]:.4f} | {r["forward"]["metrics"]["price_mae"]:.4f} |')
   for ax,key,label in zip(axes,['training','forward'],['January training','February forward']):
    ax.plot([r['iteration'] for r in rows],[r[key]['metrics']['price_mae'] for r in rows],label=f'Adam {rate}');ax.set(title=label,xlabel='Parameter updates',ylabel='Price MAE EUR/MWh',xlim=(0,100));ax.legend();ax.grid(alpha=.2)
   for r in rows:w.writerow([rate,r['iteration'],r['training']['metrics']['price_mae'],r['forward']['metrics']['price_mae'],r['training']['metrics']['generation_mae_twh'],r['forward']['metrics']['generation_mae_twh'],r['price_loss']+r['generation_loss'],r['forward_data_loss'],r['regularizer']])
 fig.tight_layout();fig.savefig(OUT/'comparison.png');plt.close(fig)
 lines+=['','![Matched learning-rate curves](comparison.png)','','[Complete computed score CSV](learning-curves.csv)','',
 'One independently parameterized curve per local hour/technology/zone, shared across month days. Two additive daily conditions are January-centered weekend and available/reference fraction. The24-hour tables have cyclic adjacent-hour regularization0.001; raw departures from neutral have ridge0.001. Nine positive slope coefficients integrate into quadratic monotone spline bids. Each rate starts from identical60-slope/-30-markup bids and zero daily adjustments. Fuel/carbon cost anchors remain explicit.', '',
 'The reference quantity remains the annual available-MW envelope proxy, not verified nameplate capacity. Actual hourly availability, demand, fixed hydro, near-zero renewable bids and the same fast95-corridor transport model stay unchanged. Original PTDF/internal feasibility is not claimed. Price errors are ENTSO-E hourly MAE; generation errors use monthly country/family Ember cells. Training gradients use January only; February is already model-development validation, not an untouched test.', '',
 'This suite compares learning rates within the NEW hourly-table representation. It is not an isolated learning-rate comparison against the old smooth-harmonic model. All100 updates are retained without patience stopping. Original gradient-identification/feasibility gates remain; failed rates are reported, not silently damped or removed. No automatic1000-update extension or baseline promotion. Inspect convergence, generation tradeoffs and validation before extension.', '',
 'Every trial must pass a real seven-hour condition/dispatch finite-difference pilot before fitting. All live scoring states replay spline inverse and balance. Current states/weights/hourly prices stay ignored locally. Source/provenance and final coverage must pass before completion claims. Example DE-LU curves and within-trial loss plots are saved under each rate subdirectory. No public website deployment is claimed.']
 (OUT/'report.md').write_text('\n'.join(lines)+'\n')
 (OUT/'report-receipt.json').write_text(json.dumps(dict(source_sha256=digest(__file__),report_sha256=digest(OUT/'report.md'),points={str(k):len(v) for k,v in histories.items()}),indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--watch',action='store_true');args=p.parse_args()
 while True:
  report()
  if not args.watch or (OUT/'suite-finished.json').exists():break
  time.sleep(15)
