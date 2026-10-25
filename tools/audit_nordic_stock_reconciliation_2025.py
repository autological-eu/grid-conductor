"""Independent water, stock-date, polynomial-bid, flow and metric replay."""
import json,csv
from pathlib import Path
import numpy as np
import pandas as pd
import run_independent_hourly_transport_2025 as parent
from run_nordic_stock_reconciliation_2025 import OUT,NVE,FROZEN
from hour_table_conditioner_2025 import feature_rows
from conditional_monotone_market_2025 import ConditionalMarket
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from supply_knot_network_2025 import generation
from run_differentiable_spline_2025 import atomic_json

def primitive(u,slopes):
 k=np.clip((u*8).astype(int),0,7);x=u-k/8
 prefix=np.concatenate([np.zeros((*slopes.shape[:-1],1)),np.cumsum((slopes[...,:-1]+slopes[...,1:])/16,axis=-1)],axis=-1)
 get=lambda a:np.take_along_axis(a,k[...,None],axis=-1)[...,0]
 a=get(slopes);b=np.take_along_axis(slopes,(k+1)[...,None],axis=-1)[...,0]
 return get(prefix)+a*x+4*(b-a)*x*x

def run():
 result=json.loads((OUT/'summary.json').read_text())
 for p,sha in json.loads((OUT/'provenance.json').read_text()).items():assert digest(ROOT/p)==sha,p
 _,(state,m,_,_)=parent.setup();s,d,_,_,capacity=state;m.__class__=ConditionalMarket
 with np.load(FROZEN/'reference.npz') as z:m.reference=z['capacity_reference_gw'];centers=z['training_condition_centers']
 with np.load(FROZEN/'state-029.npz') as z:w=z['weights']
 with np.load(OUT/'hydro.npz') as z:hydro={k:z[k] for k in z.files}
 with np.load(NVE/'water.npz') as z:original={k:z[k] for k in z.files}
 eta=original['eta'];initial=float((original['initial']*eta).sum());terminal=float((original['terminal']*eta).sum());cap=float((original['capacity']*eta).sum())
 previous=np.r_[initial,hydro['stock'][:-1]];res=float(abs(hydro['stock']-previous-hydro['source_inflow']+hydro['power']+hydro['spill']).max())
 assert res<=1e-4
 assert np.maximum(original['network_lower']-hydro['power'],0).max()<=1e-4
 assert np.maximum(hydro['power']-original['network_upper'],0).max()<=1e-4
 assert hydro['stock'].min()>=-1e-4 and hydro['stock'].max()<=cap+1e-4
 assert abs(hydro['stock'][-1]-terminal)<=1e-4 and abs(hydro['power'].sum()-hydro['old_power'].sum())<=1e-4
 raw=json.loads((ROOT/'data/bidding-zone-source-audit-2025/nve-reservoir-history.json').read_text())
 obs=sorted([r for r in raw if r['omrType']=='NO' and r['omrnr']==0 and '2024-12-15'<=r['dato_Id']<='2026-01-15'],key=lambda r:r['dato_Id'])
 times=pd.DatetimeIndex([pd.Timestamp(r['dato_Id']).tz_localize('Europe/Oslo')+pd.DateOffset(days=1) for r in obs]).tz_convert('UTC');edges=pd.date_range('2025-01-01',periods=8761,freq='h',tz='UTC')
 target=np.interp(edges.asi8,times.asi8,np.array([r['fylling_TWh'] for r in obs])*1e6)
 np.testing.assert_allclose(target,hydro['observed_stock_target'],atol=1e-6,rtol=0)
 no=np.array([z.startswith('NO') for z in s['zones']]);assert abs(hydro['zonal_delta_mw'][:,~no]).max()==0
 np.testing.assert_allclose(hydro['zonal_delta_mw'].sum(axis=1),hydro['power']-hydro['old_power'],atol=1e-4,rtol=0)
 corrected=d.copy();corrected['load']=d['load']-hydro['zonal_delta_mw'];corrected['fixed_generation']=d['fixed_generation'].copy();ci=s['countries'].index('NO');ti=s['technologies'].index('reservoir');corrected['fixed_generation'][:,ci,ti]=hydro['power'];checks=[]
 m.load=corrected['load']/1000
 for c in result['cases']:
  with np.load(OUT/f"month-{c['month']:02d}.npz") as z:wr={k:z[k] for k in z.files}
  h=wr['hours'];X,_=feature_rows(s['groups'],d,h,m.reference,centers);theta=np.einsum('tgf,gfk->tgk',X,w);slopes=.05+20*np.logaddexp(0,theta[...,1:]);q=wr['quantities_gw'];p=wr['prices'];C=m.reference[None];A=m.capacity[h]
  bid=m.source[h]+theta[...,0]+primitive(q/C,slopes);b0=m.source[h]+theta[...,0];bA=b0+primitive(A/C,slopes);pp=p[:,m.zone];tau=m.thermal_tau
  wanted=b0+tau*(np.logaddexp(0,(pp-b0)/tau)-np.logaddexp(0,(pp-bA)/tau))
  inverse=float(abs((bid-wanted)[:,~m.zero]).max());assert inverse<1e-6
  expected_ror=A[:,m.zero]/.01*m.renewable_tau*(np.logaddexp(0,pp[:,m.zero]/m.renewable_tau)-np.logaddexp(0,(pp[:,m.zero]-.01)/m.renewable_tau))
  assert abs(q[:,m.zero]-expected_ror).max()*1000<1e-4
  v=p@m.M.T/m.cost;lo=m.lower[h];hi=m.upper[h];flow=lo+m.flow_tau*(np.logaddexp(0,(v-lo)/m.flow_tau)-np.logaddexp(0,(v-hi)/m.flow_tau))
  assert abs(flow-wr['flows_gw']).max()*1000<1e-4
  balance=q@m.Z+flow@m.M-m.load[h];assert abs(balance).max()*1000<1e-4 and (abs(balance*p).sum(axis=1)*1000).max()<.05
  assert max(np.maximum(-q,0).max(),np.maximum(q-A,0).max(),np.maximum(lo-flow,0).max(),np.maximum(flow-hi,0).max())*1000<1e-4
  gen=generation(s,corrected,capacity,q*1000,h);np.testing.assert_allclose(gen,wr['generation'],atol=1e-7,rtol=0);metrics,_=metric(s,corrected,p,gen,h,c['month'])
  for k in ['price_mae','generation_mae_twh']:np.testing.assert_allclose(metrics[k],c['metrics'][k],atol=1e-9,rtol=0)
  checks.append(dict(month=c['month'],hours=len(h),inverse_eur_mwh=inverse,balance_mw=float(abs(balance).max()*1000)))
 atomic_json(OUT/'audit.json',dict(status='passed_independent_water_stock_polynomial_flow_metric_replay',water_residual_mwh=res,hours=1416,cases=checks,summary_sha256=digest(OUT/'summary.json'),source_sha256=digest(__file__)))
 months=pd.date_range('2025-01-01',periods=8760,freq='h').month.values
 rows=[]
 oldstock=(original['inventory']*eta).sum(axis=1)
 for month in range(1,13):
  h=np.flatnonzero(months==month);rows.append(dict(month=month,old_reservoir_twh=float(hydro['old_power'][h].sum()/1e6),new_reservoir_twh=float(hydro['power'][h].sum()/1e6),old_end_stock_error_twh=float((oldstock[h[-1]]-target[h[-1]+1])/1e6),new_end_stock_error_twh=float((hydro['stock'][h[-1]]-target[h[-1]+1])/1e6)))
 with (OUT/'monthly-water.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(11,4));ax.plot(edges[1:],oldstock/1e6,label='Previous schedule');ax.plot(edges[1:],target[1:]/1e6,label='NVE observed-stock interpolation',color='black',ls='--');ax.plot(edges[1:],hydro['stock']/1e6,label='Stock-anchored schedule',alpha=.8);ax.set(ylabel='Electrical-equivalent stock TWh',title='Norway: annual water preserved, intermediate stock corrected');ax.legend();fig.tight_layout();fig.savefig(OUT/'reservoir-stock.png',dpi=140);plt.close(fig)
 fig,ax=plt.subplots(figsize=(11,5));case=result['cases'][1];zones=[r for r in case['zones'] if r['zone'].startswith(('NO','SE','DK')) or r['zone']=='FI'];x=np.arange(len(zones));ax.bar(x-.2,[z['before_mae'] for z in zones],.4,label='Before');ax.bar(x+.2,[z['after_mae'] for z in zones],.4,label='Stock-anchored NO');ax.set(xticks=x,xticklabels=[r['zone'] for r in zones],ylabel='February price MAE EUR/MWh',title='Frozen bids: gains and regressions retained');ax.legend();fig.tight_layout();fig.savefig(OUT/'nordic-prices.png',dpi=140);plt.close(fig)
 text=['# Nordic stock reconciliation: first controlled correction','',
 'Status: independently verified Norway schedule correction; **Nordic goal remains open**. Bids frozen at Adam1.0/update29. No retraining, capacity increase, extra water, observed-generation-as-availability or constraint widening.', '',
 'The prior source schedule matched annual inflow/endpoints but minimized departure from an inherited dispatch pattern, allowing end-Feb stock5.315TWh above the observed trajectory. A lexicographic LP first minimizes deviation from source-interpolated NVE stocks, then minimizes departure from the old hourly schedule. It preserves exact inflow, spill, turbine/network delivery bounds, stock capacity, initial/final stock and annual reservoir energy139.2145TWh.', '',
 '![Water stock correction](reservoir-stock.png)','','![Nordic gains and regressions](nordic-prices.png)','',
 '| Month | Original Europe price MAE | Corrected Europe price MAE | Corrected mix MAE TWh |','|---|---:|---:|---:|']
 baseline=json.loads((FROZEN/'history.json').read_text())[29]
 for c in result['cases']:text.append(f"| {c['month']} | {baseline['training' if c['month']==1 else 'forward']['metrics']['price_mae']:.4f} | {c['metrics']['price_mae']:.4f} | {c['metrics']['generation_mae_twh']:.6f} |")
 text += ['',f'Independent water residual{res:.3g}MWh passes unchanged1e-4 gate. Replayed1,416hours,48modeled/41target areas, inverse bids, source stock-date convention, corridor flows, bounds, generation and prices. No original coupled PTDF certificate is claimed.', '',
 'Observed future reservoir stocks make this a retrospective physical-input reconstruction, NOT an operational hydro forecast or untouched predictive validation. Weekly stock interpolation, gross-stock/net-inflow electrical-equivalent basis, national pooling and prior geographic allocation remain assumptions. Annual peak availability remains a reference-capacity proxy. Source HBV annual volume need not match observed production exactly.', '',
 'January price fit worsens and Denmark worsens in February. Northern Norway/Sweden still have substantial positive bias. These regressions are retained. Corrected Norwegian generation alone does not complete the Nordic goal. Next priorities are Swedish water-source/stock reconciliation and regional NO1–NO5/SE1–SE4 allocation, followed by same-method refitting only when justified.', '',
 '[Monthly water ledger](monthly-water.csv) · Detailed per-zone before/after errors in summary.json.']
 (OUT/'report.md').write_text('\n'.join(text)+'\n');print(json.dumps(checks),flush=True)

if __name__=='__main__':run()
