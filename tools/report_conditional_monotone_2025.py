"""Export actual scores; optionally watch the single existing fit to completion."""
import csv,json,time,argparse,os
from pathlib import Path
from sigmoid_month_pairs_2025 import ROOT,digest
OUT=ROOT/'data/bidding-zone-network-2025/conditional-monotone-v1'

def report():
 rows=json.loads((OUT/'history.json').read_text());a=rows[0];b=rows[-1]
 complete=(OUT/'complete.json').exists();failed=(OUT/'failure.json').exists()
 with (OUT/'learning-curves.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['iteration','january_price_mae','february_price_mae','january_mix_mae_twh','february_mix_mae_twh','january_joint_loss','january_data_loss','february_data_loss','seconds'])
  for r in rows:w.writerow([r['iteration'],r['training']['metrics']['price_mae'],r['forward']['metrics']['price_mae'],r['training']['metrics']['generation_mae_twh'],r['forward']['metrics']['generation_mae_twh'],r['training_loss'],r['price_loss']+r['generation_loss'],r['forward_data_loss'],r['seconds']])
 text=['# Conditional monotone spline supply bids: January → February 2025','',
 'Status: '+('COMPLETE: 100 updates and 101 scored states.' if complete else 'FAILED; inspect failure.json.' if failed else f'RUNNING: last scored update {b["iteration"]} of100.'),'',
 '| Metric | Initial | Latest |','|---|---:|---:|']
 for kind,label in [('training','January fit'),('forward','February forward')]:
  for key,unit in [('price_mae','EUR/MWh'),('generation_mae_twh','TWh')]:text.append(f'| {label} {key} ({unit}) | {a[kind]["metrics"][key]:.6f} | {b[kind]["metrics"][key]:.6f} |')
 text+=['','![Price and generation-data losses](losses.png)','','![Learned thermal supply curves](example-curves.png)','','[All computed scores CSV](learning-curves.csv)','',
 '## Model and interpretation','',
 'For each technology–zone group, a conditional linear head generates a starting markup and nine positive spline-slope coefficients. Integrating linear B-spline slopes produces smooth monotone quadratic marginal bids. Supply inversion is analytic within each spline interval, with explicit price-space boundary smoothing. Gradients include the inverse, network root and condition mapping. No six-price-node export or averaging is used.', '',
 'Seven shared features are intercept; sin/cos of local hour at first and second harmonics; weekend; and available/reference output. Each group learns its own coefficients across all actual hours. This pilot has no learned cross-zone/technology pooling, demand feature or annual-season feature. Initial slopes60EUR/MWh per utilization and markup-30EUR/MWh are declared modeling choices. Adam learning rate0.05, raw-weight shrinkage0.001; all100 updates run without patience stopping.', '',
 'The fixed quantity reference is each group\'s peak available output over the prepared2025 inputs, floored at1MW. It is an annual availability-envelope proxy, NOT independently verified installed nameplate capacity. It uses retrospective physical input information; no future price/generation targets enter fitting. This prototype does not yet validate capacity expansion extrapolation. Every actual hourly availability bound is retained.', '',
 'Actual source fuel/carbon anchors, demand and fixed hydro remain. Wind/solar/run-of-river zero-economic offers retain the earlier near-zero bid treatment; their curves are not learned and are omitted from the thermal example plot. All48 zones,744 January and672 February hours remain. ENTSO-E hourly price MAE uses41 complete zones; Ember generation loss uses243 country/family cells per month, not invented hourly generation labels.', '',
 'The shared conditional function is trained against January alone; February is separately scored at every update without updating parameters from February labels. Loss curves compare normalized smooth price-plus-generation data loss; January regularization is separately included in the CSV joint objective. Price MAE is unnormalizedEUR/MWh. January/February were already development data: this is retrospective forward validation, not an untouched forecasting test.', '',
 'The fixed example is DE-LU,1January2025 at15:00UTC. Solid curve portions are available; faint portions extend to the reference envelope and cannot dispatch in that hour. Curves include source fuel anchors. Nonlinear shape is learned through positive spline slopes, not assumed from a plotted interpolation.', '',
 'Three tests independently check integrals by quadrature, monotonicity and inverse/parameter finite differences. A7-hour European full condition-chain pilot passes (scaled derivative error7.42e-6). Every state independently replays polynomial marginal bids at dispatched quantities against smoothed target prices and checks network balance/residual work. The fast network uses95 independent corridor bounds and quadratic transport cost; original PTDF/internal-line coupling is NOT certified. No native physical, investment, annual-acceptance or baseline adoption claim follows.', '',
 'All weights and hourly price arrays for all101 states remain ignored locally. Old failed studies remain unchanged. No website deployment is claimed.']
 if complete:
  best=min(rows,key=lambda r:r['forward']['metrics']['price_mae'])
  text+=['',f'Descriptive minimum forward MAE occurs at update{best["iteration"]}: {best["forward"]["metrics"]["price_mae"]:.6f}EUR/MWh. This uses inspected validation scores and is not an untouched selection test. Final update100 is retained regardless.']
 (OUT/'report.md').write_text('\n'.join(text)+'\n')
 (OUT/'report-receipt.json').write_text(json.dumps(dict(points=len(rows),history_sha256=digest(OUT/'history.json'),report_sha256=digest(OUT/'report.md'),source_sha256=digest(__file__)),indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--watch',action='store_true');args=p.parse_args()
 while True:
  if (OUT/'history.json').exists():report()
  if not args.watch or (OUT/'complete.json').exists() or (OUT/'failure.json').exists():break
  time.sleep(10)
