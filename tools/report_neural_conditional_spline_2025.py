"""Read-only progress/final report for the nonlinear conditioner comparison."""
import json,time,csv,argparse
from sigmoid_month_pairs_2025 import ROOT,digest
OUT=ROOT/'data/bidding-zone-network-2025/neural-conditional-spline-v1'
REF=ROOT/'data/bidding-zone-network-2025/conditional-monotone-v1'

def report():
 rows=json.loads((OUT/'history.json').read_text());last=rows[-1];old=json.loads((REF/'history.json').read_text())[-1]
 status='COMPLETE' if (OUT/'complete.json').exists() else 'FAILED' if (OUT/'failure.json').exists() else 'RUNNING'
 with (OUT/'learning-curves.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['iteration','january_price_mae','february_price_mae','january_mix_twh','february_mix_twh','january_data_loss','february_data_loss','january_regularizer','recorded_seconds'])
  for r in rows:w.writerow([r['iteration'],r['training']['metrics']['price_mae'],r['forward']['metrics']['price_mae'],r['training']['metrics']['generation_mae_twh'],r['forward']['metrics']['generation_mae_twh'],r['price_loss']+r['generation_loss'],r['forward_data_loss'],r['regularizer'],r['seconds']])
 lines=['# Neural-conditioned monotone supply bids', '',f'Status: **{status}**, last scored update **{last["iteration"]}/100**. Initial state plus100 updates required; incomplete results are not a final comparison.','',
 '| Metric | Linear conditioner, update100 | Neural conditioner, latest |','|---|---:|---:|']
 for kind,label in [('training','January'),('forward','February')]:
  for key,unit in [('price_mae','EUR/MWh'),('generation_mae_twh','TWh')]:lines.append(f'| {label} {key} ({unit}) | {old[kind]["metrics"][key]:.6f} | {last[kind]["metrics"][key]:.6f} |')
 lines+=['','![Learning curves](losses.png)','','![DE-LU example supply curves](example-curves.png)','','[All computed losses CSV](learning-curves.csv) · [Per-zone, hour and extreme-price errors CSV](february-errors.csv)','',
 'The candidate uses a two-hidden-layer32-unit tanh network, shared across resources, with8-dimensional zone and4-dimensional technology embeddings. Inputs otherwise match the linear conditioner: two local-hour sine/cosine harmonics, weekend and available/reference capacity fraction. The network produces the intercept and9 raw positive-slope spline parameters. Integrated linear B-spline slopes give monotone quadratic bids with analytic inverse; the same function is used for training and forward prediction, without averaging.', '',
 'Initial economic bids match the linear control exactly (zero last layer,60EUR/MWh utilization slope,-30EUR/MWh intercept adjustment). Fuel/carbon anchors, actual hourly demand and availability, fixed hydro, near-zero renewable bids,95-corridor transport model and all48 areas are unchanged. The reference scale remains the prior annual-peak-availability proxy, NOT verified installed capacity. This is retrospective perfect-input evaluation. No new demand or observed-price feature enters the conditioner.', '',
 'Changes include nonlinear interactions, parameter sharing through zone/technology embeddings and Adam learning rate0.003 rather than the linear control0.05; this is a candidate comparison, not an isolated causal architecture estimate. Penalty is0.001 mean squared parameter departure from initialization. NumPy analytic neural backprop is checked by finite differences; no large framework installation is required.', '',
 'All744January hours and monthly country/family generation targets train the network. All672February hours are separately scored after prediction; no February label enters gradients or normalization. Ordinary price MAE covers the same41 complete ENTSO-E zones; generation MAE uses243 monthly Ember cells. February was already development data: no untouched forecasting or unique actual-bid recovery claim follows.', '',
 'Error CSV includes each eligible zone, all hours, UTC hour-of-day and observed-price cohorts above January p95/below January p05. Thresholds are fixed from January; February prices are used only to classify scored errors, never as model inputs. This distinguishes persistent bias, daily timing and extremes but does not prove their causes. The linear comparator is frozen at update100.', '',
 'Solid DE-LU curves are available at1January15:00UTC; faint parts cannot dispatch that hour. Renewable near-zero curves are not learned and omitted. Every fit/prediction state replays inverse spline equations and balance; unidentified-price gradients must pass the original guard. These checks do NOT certify original PTDF/intrazonal constraints. No baseline, annual, investment or public-site adoption is implied. All raw weights/hourly prices remain ignored locally.']
 if status=='COMPLETE':
  best=min(rows,key=lambda r:r['forward']['metrics']['price_mae']);lines+=['',f'Lowest observed February MAE: {best["forward"]["metrics"]["price_mae"]:.6f} at update{best["iteration"]}. Descriptive validation selection only; retain final100 and all adverse scores.']
 (OUT/'report.md').write_text('\n'.join(lines)+'\n')
 (OUT/'report-receipt.json').write_text(json.dumps(dict(status=status,points=len(rows),history_sha256=digest(OUT/'history.json'),source_sha256=digest(__file__),report_sha256=digest(OUT/'report.md')),indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--watch',action='store_true');args=p.parse_args()
 while True:
  if (OUT/'history.json').exists():report()
  if not args.watch or (OUT/'complete.json').exists() or (OUT/'failure.json').exists():break
  time.sleep(10)
