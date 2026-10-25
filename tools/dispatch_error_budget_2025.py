"""Frozen completed-candidate error budget; no new market fit or solve."""
import json,csv
from pathlib import Path
import numpy as np
import run_independent_hourly_transport_2025 as parent
from sigmoid_month_pairs_2025 import ROOT,digest,FAMILIES
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json
OUT=ROOT/'data/bidding-zone-network-2025/dispatch-error-budget-v1'


def budget(predicted,observed,training_observed):
 error=predicted-observed;lo,hi=np.quantile(training_observed,[.05,.95],axis=0)
 masks={'Low observed price (<Jan p05)':observed<lo,'Middle observed price':(observed>=lo)&(observed<=hi),'High observed price (>Jan p95)':observed>hi}
 total=error.size;absolute=abs(error).sum();rows=[]
 for name,mask in masks.items():
  n=int(mask.sum());summed=float(abs(error[mask]).sum())
  rows.append(dict(cohort=name,hours=n,hour_share=n/total,mae=float(abs(error[mask]).mean()) if n else None,bias=float(error[mask].mean()) if n else None,error_share=summed/absolute,contribution=summed/total))
 np.testing.assert_allclose(sum(r['contribution'] for r in rows),abs(error).mean(),atol=1e-12)
 return rows


def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'summary.json').exists():raise ValueError('Already analyzed; use frozen existing report')
 candidates=[]
 for root,rates in [('hour-table-learning-rates-v1',[.05,.15,.5]),('higher-hour-table-learning-rates-v1',[1.,2.])]:
  for rate in rates:
   p=ROOT/'data/bidding-zone-network-2025'/root/f'lr-{rate:g}'
   if not (p/'complete.json').exists():continue
   rows=json.loads((p/'history.json').read_text());assert len(rows)==101
   for r in rows:candidates.append((r['forward']['metrics']['price_mae'],rate,r['iteration'],p,r))
 best=min(candidates,key=lambda x:x[0]);_,rate,step,folder,row=best
 for name,h in json.loads((folder/'provenance.json').read_text()).items():
  if digest(ROOT/name)!=h:raise ValueError('Changed fit source '+name)
 base,(state,market,_,_)=parent.setup();s,d,_,_,_=state;jan=month_hours(1);feb=month_hours(2);ok=np.isfinite(d['observed_prices']).all(axis=0);zones=np.array(s['zones'])[ok]
 path=folder/f'state-{step:03d}.npz'
 with np.load(path) as z:training=z['training_prices'][:,ok];pred=z['forward_prices'][:,ok]
 truth=d['observed_prices'][feb][:,ok];jtruth=d['observed_prices'][jan][:,ok];error=pred-truth
 np.testing.assert_allclose(abs(error).mean(),row['forward']['metrics']['price_mae'],atol=1e-10)
 cohorts=budget(pred,truth,jtruth);zrows=[];hour_bias=np.zeros((len(zones),24));jan_bias=(training-jtruth).mean(axis=0);feb_bias=error.mean(axis=0)
 for j,z in enumerate(zones):
  for h in range(24):hour_bias[j,h]=error[feb%24==h,j].mean()
  zrows.append(dict(zone=z,mae=float(abs(error[:,j]).mean()),bias=float(feb_bias[j]),jan_bias=float(jan_bias[j]),error_share=float(abs(error[:,j]).sum()/abs(error).sum()),contribution=float(abs(error[:,j]).sum()/error.size)))
 zrows.sort(key=lambda x:x['mae'],reverse=True)
 # Diagnostic February-centering uses future labels and is NOT a prediction.
 jan_corrected=float(abs(error-jan_bias).mean());feb_centered=float(abs(error-feb_bias).mean())
 # Monthly mix errors are retained independently of price/error categories.
 generated=np.array(row['forward']['monthly_generation_twh']);observed=d['ember'][1];mix=[]
 for c,country in enumerate(s['countries']):
  for t,family in enumerate(FAMILIES):
   if np.isfinite(observed[c,t]):mix.append(dict(country=country,family=family,model_twh=float(generated[c,t]),observed_twh=float(observed[c,t]),difference_twh=float(generated[c,t]-observed[c,t])))
 mix.sort(key=lambda x:abs(x['difference_twh']),reverse=True)
 np.testing.assert_allclose(np.mean([abs(r['difference_twh']) for r in mix]),row['forward']['metrics']['generation_mae_twh'],atol=1e-10)
 for name,rows in [('cohorts',cohorts),('zones',zrows),('generation-mix',mix)]:
  with (OUT/f'{name}.csv').open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 # Validate attribution totals independently from individual zone errors.
 np.testing.assert_allclose(sum(r['contribution'] for r in zrows),abs(error).mean(),atol=1e-12)
 reference=np.maximum(market.capacity.max(axis=0),.001);inputrows=[]
 for j,g in enumerate(s['groups']):
  if g['zone'] not in [r['zone'] for r in zrows[:10]]:continue
  a=d['capacity'][feb,j]
  if not a.max()>0:continue
  inputrows.append(dict(zone=g['zone'],technology=g['technology'],available_min_mw=float(a.min()),available_max_mw=float(a.max()),flat=bool(np.ptp(a)<1e-6)))
 atomic_json(OUT/'input-flags.json',dict(scope='Constant availability is a review flag, not proof of an input error.',groups=inputrows))
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(1,2,figsize=(12,5));top=zrows[:12];axes[0].barh([r['zone'] for r in top][::-1],[100*r['error_share'] for r in top][::-1]);axes[0].set(xlabel='% of all February absolute price error',title='Largest zone contributions')
 axes[1].bar([r['cohort'].split(' (')[0] for r in cohorts],[100*r['error_share'] for r in cohorts]);axes[1].set(ylabel='% of absolute price error',title='Disjoint observed-price cohorts');axes[1].tick_params(axis='x',rotation=15);fig.tight_layout();fig.savefig(OUT/'error-budget.png',dpi=140);plt.close(fig)
 fig,ax=plt.subplots(figsize=(12,11));order=[list(zones).index(r['zone']) for r in zrows];lim=max(1,float(np.quantile(abs(hour_bias),.95)));im=ax.imshow(hour_bias[order],aspect='auto',cmap='RdBu_r',vmin=-lim,vmax=lim);ax.set(yticks=np.arange(len(zones)),yticklabels=[r['zone'] for r in zrows],xticks=np.arange(0,24,2),xlabel='UTC hour',title='Mean model−observed price EUR/MWh; color clipped at95% absolute bias');fig.colorbar(im,ax=ax);fig.tight_layout();fig.savefig(OUT/'hourly-bias.png',dpi=140);plt.close(fig)
 summary=dict(status='completed_frozen_candidate_error_budget',rate=rate,iteration=step,selection='Lowest February MAE among completed hourly-table trials at analysis start; explicitly validation-selected',path=str(path.relative_to(ROOT)),price_mae=float(abs(error).mean()),bias=float(error.mean()),jan_bias_corrected_mae=jan_corrected,feb_oracle_centered_mae=feb_centered,cohorts=cohorts,top_zones=zrows[:10],top_mix=mix[:10],generation_mae_twh=row['forward']['metrics']['generation_mae_twh'],top5_error_share=sum(r['error_share'] for r in zrows[:5]),source_sha256=digest(__file__),checkpoint_sha256=digest(path))
 atomic_json(OUT/'summary.json',summary);report(summary)
 files=list(OUT.glob('*.csv'))+list(OUT.glob('*.png'))+[OUT/'report.md',OUT/'summary.json',OUT/'input-flags.json',path,folder/'history.json',folder/'provenance.json',Path(__file__)]
 atomic_json(OUT/'receipt.json',{str(p.relative_to(ROOT)):digest(p) for p in files});print(json.dumps(summary),flush=True)


def report(r):
 lines=['# Dispatch price-error budget: frozen January→February candidate','',f'Frozen candidate: Adam{r["rate"]}, update{r["iteration"]}, February price MAE **{r["price_mae"]:.3f}EUR/MWh**. Selected using February among COMPLETED hourly-table trials; not an untouched test or baseline promotion. Rate2 may still be running and cannot change this frozen analysis.', '',
 'No new training or dispatch solve. Saved January/February prices are compared against their original complete hourly ENTSO-E targets; monthly generation is compared with the same Ember cells. Source and checkpoint hashes, recorded MAE and generation totals replay. All672February hours/41 target zones retained, including extremes;48 modeled zones remain in original fits.', '',
 '![Error budget](error-budget.png)','','![Daily zonal bias](hourly-bias.png)','',
 f'Top5 zones contribute **{100*r["top5_error_share"]:.1f}%** of absolute February price error. Overall signed model−observation bias **{r["bias"]:.3f}EUR/MWh**. Absolute errors, rather than visually striking spikes alone, determine priority.', '',
 '| Cohort | Share of zone-hours | MAE | Share of absolute error |','|---|---:|---:|---:|']
 for c in r['cohorts']:lines.append(f'| {c["cohort"]} | {100*c["hour_share"]:.1f}% | {c["mae"]:.3f} | {100*c["error_share"]:.1f}% |')
 lines+=['', 'Low/high thresholds are each zone\'s January observed-price p05/p95; middle includes ties. Cohorts are disjoint and their MAE contributions add exactly to overall MAE. Labels use February observations only for retrospective diagnosis, never as prediction inputs. Cohorts identify WHEN errors occur, not their cause.', '',
 f'Subtracting each zone\'s January mean fitting error from February predictions gives MAE **{r["jan_bias_corrected_mae"]:.3f}**. Subtracting each zone\'s own February mean error gives **{r["feb_oracle_centered_mae"]:.3f}**; the latter is an oracle diagnostic using future labels, NOT a usable forecast. These are counterfactual score sensitivities, not additive causal error shares or guaranteed attainable improvements.', '',
 '| Zone | MAE | Signed bias | Share of error |','|---|---:|---:|---:|']
 for z in r['top_zones']:lines.append(f'| {z["zone"]} | {z["mae"]:.3f} | {z["bias"]:.3f} | {100*z["error_share"]:.2f}% |')
 lines+=['',f'February monthly generation MAE: **{r["generation_mae_twh"]:.6f}TWh**. Largest absolute country/family gaps:', '', '| Country/family | Model TWh | Ember TWh | Difference TWh |','|---|---:|---:|---:|']
 for x in r['top_mix']:lines.append(f'| {x["country"]}/{x["family"]} | {x["model_twh"]:.3f} | {x["observed_twh"]:.3f} | {x["difference_twh"]:+.3f} |')
 lines+=['','[All zones](zones.csv) · [All cohorts](cohorts.csv) · [All monthly generation gaps](generation-mix.csv)','',
 '## Implication for modelling','',
 'Keep fast constrained clearing and flexible monotone marginal bids. Use this ranking to select a source-backed diagnostic, rather than further increasing curve flexibility indiscriminately. Availability, demand, fuel anchors and deliverability can all alter prices even with stable bids; inverse calibration can compensate for wrong physical inputs. Monthly country generation cannot uniquely identify hourly technology bids.', '',
 'input-flags.json inventories constant availability in the worst10price zones; constancy is not itself an error. Country generation gaps also reflect source scope/taxonomy and within-group illustrative allocation. None proves a missing capacity quantity or incorrect bid price. Observed hourly generation/exchanges/outages have NOT been newly reconciled in this report; that is a next investigation, not completed evidence.', '',
 'The fast market uses95 model-derived independent corridor bounds with quadratic transport costs, annual peak availability as reference-capacity proxy and fixed hydro. It omits original PTDF/intrazonal coupling and does not certify actual commercial capacity, operator bids, forecast resilience or asset valuations. Hourly bias plot uses UTC; saturated colors do not truncate numeric CSV values. No public deployment or automatic model adoption.']
 (OUT/'report.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':run()
