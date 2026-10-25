"""Source-verified Jan/Feb independent-hour reconstructions; no new fitting jobs."""
import json,csv,time
from pathlib import Path
import numpy as np
from scipy.spatial.distance import cdist
import run_independent_hourly_transport_2025 as source
from independent_hourly_transport_2025 import economic_nodes
from monthly_mean_forward_2025 import audit_score
from run_conditional_monotone_2025 import features
from sigmoid_month_pairs_2025 import ROOT,digest
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json
PARENT=ROOT/'data/bidding-zone-network-2025/monthly-mean-forward-100-v1'
OUT=ROOT/'data/bidding-zone-network-2025/hourly-curve-comparison-v1'

def regression(X,Y,V):
 mean=X[:,1:].mean(axis=0);std=X[:,1:].std(axis=0);keep=std>1e-8
 Z=np.c_[np.ones(len(X)),(X[:,1:][:,keep]-mean[keep])/std[keep]]
 Q=np.c_[np.ones(len(V)),(V[:,1:][:,keep]-mean[keep])/std[keep]]
 penalty=np.eye(Z.shape[1]);penalty[0,0]=0
 return Q@np.linalg.solve(Z.T@Z+penalty,Z.T@Y)

def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'summary.json').exists():raise ValueError('Completed analysis; inspect existing results')
 pinned=json.loads((PARENT/'provenance.json').read_text())
 for p,h in pinned.items():
  if digest(ROOT/p)!=h:raise ValueError('Changed original study '+p)
 base,(state,m,_,_)=source.setup();s,d,_,_,_=state;hours=[month_hours(1),month_hours(2)];raw=[];records=[];audits=[]
 for month,h in enumerate(hours,1):
  folder=PARENT/f'month-{month:02d}'
  assert json.loads((folder/'complete.json').read_text())['updates']==100
  record=json.loads((folder/'100.json').read_text());records.append(record)
  with np.load(folder/'100-parameters.npz') as z:raw.append(z['theta'])
  witness=folder/'100-within.npz'
  with np.load(witness) as z:w={k:z[k] for k in z.files}
  w.update(certificate=record['within']['solver_certificate'],seconds=0.)
  replay,generated=audit_score(state,m,raw[-1],w,month)
  np.testing.assert_allclose(generated,w['generation'],atol=1e-7,rtol=0)
  score=replay['metrics'];audit=dict(hours=len(h),certificate=replay['audit'],witness_sha256=digest(witness),generation_replay_max=float(abs(generated-w['generation']).max()))
  for k in ['price_mae','generation_mae_twh']:np.testing.assert_allclose(score[k],record['within']['metrics'][k],atol=1e-9,rtol=0)
  audits.append(audit)
 atomic_json(OUT/'audit.json',dict(status='passed',cases=audits,provenance_sha256=digest(PARENT/'provenance.json')))
 nodes=[economic_nodes(a) for a in raw]
 # Same calendar/physical candidate features for each group; no price labels.
 reference=np.maximum(m.capacity.max(axis=0),.001)
 clock=[features(s,d,h,reference) for h in hours]
 # Augment with net demand after fixed injection, source-cost anchor and zonal
 # available wind/solar; all standardization below is January-only.
 renewable=np.array([g['technology'] in ['solar','onwind','offwind-ac','offwind-dc','offwind-float','solar-hsat'] for g in s['groups']])
 windsolar=(m.capacity*renewable)@m.Z
 X=[]
 for h,c in zip(hours,clock):
  zi=m.zone;X.append(np.concatenate([c,m.load[h][:,zi,None],m.source[h,:,None],windsolar[h][:,zi,None]],axis=-1))
 rows=[];predictions={};envelopes=[]
 for g,group in enumerate(s['groups']):
  if m.zero[g]:continue
  ja=d['capacity'][hours[0],g]>0;fb=d['capacity'][hours[1],g]>0
  if ja.sum()<24 or fb.sum()<24:continue
  A=nodes[0][ja,g];B=nodes[1][fb,g];xa=X[0][ja,g];xb=X[1][fb,g]
  # All supported Jan×Feb pairs, plus within-month leave-self-out distances.
  cross=cdist(A,B)/np.sqrt(6);within=cdist(A,A)/np.sqrt(6);np.fill_diagonal(within,np.inf)
  avg=np.broadcast_to(A.mean(axis=0),B.shape);methods={'January mean':avg}
  methods['Clock']=regression(xa[:,:6],A,xb[:,:6])
  methods['Physical']=regression(np.c_[xa[:,0],xa[:,6:]],A,np.c_[xb[:,0],xb[:,6:]])
  methods['Clock + physical']=regression(xa,A,xb)
  row=dict(zone=group['zone'],technology=group['technology'],jan_hours=int(ja.sum()),feb_hours=int(fb.sum()),
           jan_temporal_mae=float(abs(A-A.mean(axis=0)).mean()),feb_temporal_mae=float(abs(B-B.mean(axis=0)).mean()),
           month_mean_shift=float(abs(A.mean(axis=0)-B.mean(axis=0)).mean()),
           cross_pair_rms_mean=float(cross.mean()),feb_nearest_jan_rms=float(cross.min(axis=0).mean()),jan_nearest_other_rms=float(within.min(axis=1).mean()))
  for name,values in methods.items():row[name]=float(abs(values-B).mean())
  rows.append(row);predictions[g]=(ja,fb,A,B,methods)
 with (OUT/'curve-comparison.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 # Distance witnesses and envelopes are compact summaries, not fabricated bids.
 wanted=[('DE-LU','gas'),('FR','nuclear'),('ES','gas'),('GB','gas'),('PL','hard_coal'),('SE3','biomass')]
 selected=[]
 for zone,tech in wanted:
  matches=[g for g in predictions if s['groups'][g]['zone']==zone and s['groups'][g]['technology']==tech]
  if matches:selected.append(matches[0])
 if len(selected)<6:
  for g in sorted(predictions,key=lambda g:m.capacity[hours[0],g].sum(),reverse=True):
   if g not in selected:selected.append(g)
   if len(selected)==6:break
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(2,3,figsize=(13,7))
 for ax,g in zip(axes.flat,selected):
  ja,fb,A,B,_=predictions[g];group=s['groups'][g]
  for arr,name,color in [(A,'January','#2563eb'),(B,'February','#ea580c')]:
   q=np.quantile(arr,[.1,.5,.9],axis=0);ax.fill_between(np.linspace(0,100,6),q[0],q[2],color=color,alpha=.2);ax.plot(np.linspace(0,100,6),q[1],label=name,color=color)
  ax.set(title=group['zone']+' '+group['technology'],xlabel='% hourly available supply',ylabel='Economic markup EUR/MWh');ax.legend(fontsize=8);ax.grid(alpha=.2)
 fig.suptitle('Independent hourly fits: median and10–90% temporal range; fuel anchors removed');fig.tight_layout();fig.savefig(OUT/'curve-envelopes.png',dpi=140);plt.close(fig)
 names=list(next(iter(predictions.values()))[-1]);scores={name:float(np.mean([r[name] for r in rows])) for name in names}
 fig,ax=plt.subplots(figsize=(9,4));ax.bar(names,list(scores.values()),color=['#64748b','#2563eb','#14b8a6','#ea580c']);ax.set(ylabel='February learned-curve MAE EUR/MWh',title='Predict February reconstructed curves from January (equal group weight)');fig.tight_layout();fig.savefig(OUT/'curve-transfer.png',dpi=140);plt.close(fig)
 # A fixed supply-fraction slice makes day/hour patterns visible; same y-axis.
 fig,axes=plt.subplots(2,3,figsize=(13,7))
 for ax,g in zip(axes.flat,selected):
  group=s['groups'][g]
  for i,name,color in [(0,'January','#2563eb'),(1,'February','#ea580c')]:
   c=clock[i][:,g];active=d['capacity'][hours[i],g]>0
   local=np.mod(np.arctan2(c[:,1],c[:,2]),2*np.pi)*24/(2*np.pi);hour=np.rint(local).astype(int)%24
   y=(nodes[i][:,g,2]+nodes[i][:,g,3])/2
   xx=[];means=[]
   for k in range(24):
    take=active&(hour==k)
    if take.any():xx.append(k);means.append(float(y[take].mean()))
   ax.plot(xx,means,label=name,color=color)
  ax.set(title=group['zone']+' '+group['technology'],xlabel='Local hour of day',ylabel='Mean 50% markup EUR/MWh');ax.legend(fontsize=8)
 fig.tight_layout();fig.savefig(OUT/'daily-patterns.png',dpi=140);plt.close(fig)
 summary=dict(status='completed_verified_existing_hourly_fits',groups=len(rows),training=[r['within']['metrics'] for r in records],curve_prediction_mae=scores,
              groups_better_clock=sum(r['Clock']<r['January mean'] for r in rows),groups_better_physical=sum(r['Physical']<r['January mean'] for r in rows),groups_better_combined=sum(r['Clock + physical']<r['January mean'] for r in rows),
              mean_temporal_january=float(np.mean([r['jan_temporal_mae'] for r in rows])),mean_temporal_february=float(np.mean([r['feb_temporal_mae'] for r in rows])),mean_month_shift=float(np.mean([r['month_mean_shift'] for r in rows])),
              cases=[str((PARENT/f'month-{i:02d}/100-parameters.npz').relative_to(ROOT)) for i in [1,2]],source_sha256=digest(__file__))
 atomic_json(OUT/'summary.json',summary);report(summary)
 print(json.dumps(summary),flush=True)

def report(r):
 lines=['# Independent hourly supply curves: January versus February', '',
 'Both months were already independently fitted to their OWN hourly price and monthly generation observations. This report reuses matched100-update checkpoints; no old search was resumed and no new dispatch fitting was run. January has744hours, February672; all48 areas remain. These are in-sample inverse reconstructions, NOT forward price predictions.', '',
 '| Within-month measure | January | February |','|---|---:|---:|']
 for key in ['price_mae','generation_mae_twh']:lines.append(f'| {key} | {r["training"][0][key]:.6f} | {r["training"][1][key]:.6f} |')
 lines+=['','![Curve distributions](curve-envelopes.png)','','![Daily patterns](daily-patterns.png)','','![Prediction of reconstructed curves](curve-transfer.png)','','[All group distances and prediction errors CSV](curve-comparison.csv)','',
 f'Analyze{r["groups"]} technology/zone groups with at least24 availability-positive hours in both months. Zero-economic renewable curves excluded. Every supported January curve is compared with every supported February curve within its SAME technology/zone, using six-node RMS economic-price distance. Compare this with January leave-self-out nearest distances; proximity does not identify actual bids.', '',
 'Curve distributions show fuel/source anchors REMOVED: they are economic markups, not complete offer prices. The horizontal axis is percent of that actual hour\'s AVAILABLE supply, as in the original16EUR/MWh experiment, not installed capacity. Equal fractions can represent different MW. Shaded10–90% ranges describe variation across fitted hours, not statistical confidence intervals.', '',
 f'Equal-group mean within-January absolute curve variation: {r["mean_temporal_january"]:.3f}EUR/MWh; within-February: {r["mean_temporal_february"]:.3f}; mean absolute month-mean shift: {r["mean_month_shift"]:.3f}. These summarize all six nodes, including weakly identified unused parts.', '',
 'January-only ridge regressions predict February\'s independently reconstructed node prices. Clock uses local first/second harmonics and weekend; physical uses available/reference fraction, zonal net demand after fixed injections, source-cost anchor and zonal available wind/solar. Combined uses both. Standardization uses January support only; ridge1, unpenalized intercept, no feature tuning on February. These regress reconstructed curves, NOT observed prices, and are not market-clearing forecasts.', '',
 '| Curve predictor | February curve MAE EUR/MWh |','|---|---:|']
 for name,value in r['curve_prediction_mae'].items():lines.append(f'| {name} | {value:.6f} |')
 lines+=['',f'Clock improves over January mean in{r["groups_better_clock"]}/{r["groups"]} groups; physical in{r["groups_better_physical"]}; combined in{r["groups_better_combined"]}. Adverse results retained. This diagnostic establishes neither randomness nor causal driver identification.', '',
 'The fits used own-month hourly price/monthly generation losses, neutral initialization, hourly shrinkage0.01 and adjacent-hour departure penalty0.01, Adam0.5. Thus some smoothness is imposed by regularization; visible daily patterns are not automatically evidence of real operator strategy. There is one optimizer trajectory per month, no repeated-initialization uncertainty estimate. Monthly generation cannot uniquely determine hourly technology bids; unused curve tails are particularly weakly identified. Similar fitted curves can also compensate for input/network errors.', '',
 'Both retained100-update quantity/flow/generation witnesses were independently replayed: inverse supply/flow responses, bounds, balance, residual work, observed metrics and source hashes. This verifies1416 actual witness hours, all48 zones and41 price targets. It does not certify original PTDF/internal constraints; the underlying model is the fast95-corridor approximation. All raw arrays/plots remain ignored; no baseline promotion or website deployment.', '',
 'Next useful diagnostic is repeat-fit stability and dispatch-local curve sensitivity, before using apparent patterns to build another forward model.']
 (OUT/'report.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':run()
