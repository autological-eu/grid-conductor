"""Independent two-month water/market replay of the combined NO+SE diagnostic."""
import json,csv
from pathlib import Path
import numpy as np
import pandas as pd
import run_independent_hourly_transport_2025 as parent
from run_sweden_stock_window_v2_2025 import OUT,NORWAY,FROZEN
from audit_nordic_stock_reconciliation_2025 import primitive
from sweden_hydro_calendar_2025 import observations
from conditional_monotone_market_2025 import ConditionalMarket
from hour_table_conditioner_2025 import feature_rows
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from supply_knot_network_2025 import generation
from run_differentiable_spline_2025 import atomic_json

def run():
 result=json.loads((OUT/'summary.json').read_text())
 for p,h in json.loads((OUT/'provenance.json').read_text()).items():assert digest(ROOT/p)==h,p
 with np.load(OUT/'water.npz') as z:water={k:z[k] for k in z.files}
 previous=np.r_[water['initial'],water['stock'][:-1]];water_res=float(abs(water['stock']-previous-water['natural_inflow']+water['power']).max());assert water_res<=1e-4
 assert water['power'].min()>=-1e-4 and water['power'].max()<=water['turbine']+1e-4
 assert water['stock'].min()>=-1e-4 and water['stock'].max()<=water['stockcap']+1e-4
 assert abs(water['stock'][-1]-water['terminal'])<=1e-4
 np.testing.assert_allclose(water['power'].sum(),water['natural_inflow'].sum()+water['initial']-water['terminal'],atol=1e-4,rtol=0)
 # Rebuild stock dates from each report's declared ISO week, independently of compiler.
 source_rows,_=observations();when=[];stock=[]
 import datetime as dt
 for (year,week),r in sorted(source_rows.items()):
  when.append(pd.Timestamp(dt.date.fromisocalendar(year,week,7)).tz_localize('Europe/Stockholm')+pd.DateOffset(days=1));stock.append(sum(v['stock_gwh'] for v in r['zones'].values())*1000)
 when=pd.DatetimeIndex(when).tz_convert('UTC').as_unit('ns');edges=pd.date_range('2025-01-01',periods=1417,freq='h',tz='UTC').as_unit('ns');target=np.interp(edges.asi8,when.asi8,stock)
 # Regional GWh rows round independently; national-vs-regional sums differ by <=2GWh.
 discrepancy=float(abs(target-water['stocktarget']).max());assert discrepancy<=2001
 _,(state,m,_,_)=parent.setup();s,d,_,_,capacity=state;m.__class__=ConditionalMarket
 with np.load(FROZEN/'reference.npz') as z:m.reference=z['capacity_reference_gw'];centers=z['training_condition_centers']
 with np.load(FROZEN/'state-029.npz') as z:w=z['weights']
 with np.load(NORWAY/'hydro.npz') as z:no_power=z['power']
 corrected=d.copy();corrected['load']=d['load'].copy();corrected['load'][:1416]-=water['zonal_delta_mw'];corrected['fixed_generation']=d['fixed_generation'].copy();ti=s['technologies'].index('reservoir')
 corrected['fixed_generation'][:1416,s['countries'].index('NO'),ti]=no_power[:1416];corrected['fixed_generation'][:1416,s['countries'].index('SE'),ti]=water['power'];m.load=corrected['load']/1000
 zonesNO=np.array([z.startswith('NO') for z in s['zones']]);zonesSE=np.array([z.startswith('SE') for z in s['zones']]);others=~(zonesNO|zonesSE)
 assert abs(water['zonal_delta_mw'][:,others]).max()==0
 np.testing.assert_allclose(water['zonal_delta_mw'][:,zonesSE].sum(axis=1),water['power']-water['old_power'],atol=1e-4,rtol=0)
 checks=[];table=[]
 for c in result['cases']:
  with np.load(OUT/f"month-{c['month']:02d}.npz") as z:wr={k:z[k] for k in z.files}
  h=wr['hours'];X,_=feature_rows(s['groups'],d,h,m.reference,centers);theta=np.einsum('tgf,gfk->tgk',X,w);slopes=.05+20*np.logaddexp(0,theta[...,1:]);q=wr['quantities_gw'];p=wr['prices'];C=m.reference[None];A=m.capacity[h]
  b0=m.source[h]+theta[...,0];bid=b0+primitive(q/C,slopes);bA=b0+primitive(A/C,slopes);pp=p[:,m.zone];tau=m.thermal_tau
  wanted=b0+tau*(np.logaddexp(0,(pp-b0)/tau)-np.logaddexp(0,(pp-bA)/tau));err=float(abs((bid-wanted)[:,~m.zero]).max());assert err<1e-6
  rq=A[:,m.zero]/.01*m.renewable_tau*(np.logaddexp(0,pp[:,m.zero]/m.renewable_tau)-np.logaddexp(0,(pp[:,m.zero]-.01)/m.renewable_tau));assert abs(rq-q[:,m.zero]).max()*1000<1e-4
  lo=m.lower[h];hi=m.upper[h];v=p@m.M.T/m.cost;flow=lo+m.flow_tau*(np.logaddexp(0,(v-lo)/m.flow_tau)-np.logaddexp(0,(v-hi)/m.flow_tau));assert abs(flow-wr['flows_gw']).max()*1000<1e-4
  balance=q@m.Z+flow@m.M-m.load[h];assert abs(balance).max()*1000<1e-4 and (abs(balance*p).sum(axis=1)*1000).max()<.05
  assert max(np.maximum(-q,0).max(),np.maximum(q-A,0).max(),np.maximum(lo-flow,0).max(),np.maximum(flow-hi,0).max())*1000<1e-4
  gen=generation(s,corrected,capacity,q*1000,h);np.testing.assert_allclose(gen,wr['generation'],atol=1e-7,rtol=0);metrics,_=metric(s,corrected,p,gen,h,c['month'])
  for k in ['price_mae','generation_mae_twh']:np.testing.assert_allclose(metrics[k],c['metrics'][k],atol=1e-9,rtol=0)
  checks.append(dict(month=c['month'],hours=len(h),water_residual_mwh=water_res,inverse_eur_mwh=err,balance_mw=float(abs(balance).max()*1000)))
  for z in c['zones']:table.append(dict(month=c['month'],**z))
 with (OUT/'zone-comparison.csv').open('w',newline='') as f:
  out=csv.DictWriter(f,fieldnames=list(table[0]));out.writeheader();out.writerows(table)
 atomic_json(OUT/'audit.json',dict(status='passed_water_regional_rounding_polynomial_flow_generation_metrics',water_residual_mwh=water_res,stock_national_regional_rounding_max_mwh=discrepancy,cases=checks,source_sha256=digest(__file__),summary_sha256=digest(OUT/'summary.json')))
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(1,2,figsize=(13,4.5))
 for ax,c in zip(axes,result['cases']):
  rows=[r for r in c['zones'] if r['zone'].startswith(('NO','SE','DK')) or r['zone']=='FI'];x=np.arange(len(rows));ax.bar(x-.2,[r['before_mae'] for r in rows],.4,label='Original');ax.bar(x+.2,[r['after_mae'] for r in rows],.4,label='NO+SE water reconstruction');ax.set(xticks=x,xticklabels=[r['zone'] for r in rows],ylabel='Price MAE EUR/MWh',title='January' if c['month']==1 else 'February');ax.tick_params(axis='x',rotation=45);ax.legend(fontsize=7)
 fig.tight_layout();fig.savefig(OUT/'nordic-prices.png',dpi=140);plt.close(fig)
 lines=['# Nordic water-input reconstruction: Norway and Sweden','',
 '**Status: independently verified two-month diagnostic; autonomous Nordic goal remains OPEN.** No bid refit or new price target. Adam1.0/update29 coefficients remain frozen.', '',
 '| Case | January Europe MAE | February Europe MAE |','|---|---:|---:|',
 '| Original |21.9535|31.6688|','| Norway stock-anchored |22.6023|26.4329|',f"| Norway + Swedish source-covered reservoir |{result['cases'][0]['metrics']['price_mae']:.4f}|{result['cases'][1]['metrics']['price_mae']:.4f}|", '',
 '![Per-zone gains and regressions](nordic-prices.png)','','[All41-zone errors CSV](zone-comparison.csv)','',
 'Norway keeps the same independent HBV inflow, spill, turbine/network bounds, initial/final stock, annual reservoir energy139.2145TWh and existing geographic pattern. It now tracks NVE observed stock rather than an inherited annual-dispatch pattern. Sweden uses public Energiföretagen weekly inflow-energy and reservoir-stock reports, with existing reservoir-capacity share to split total inflow; source ERA5 provides only within-week shape. Stock observations are linearly bracketed at reported week-end dates;33.7TWh capacity is the published national header value. No generation curve is substituted for availability.', '',
 'Sweden compiles ONLY January/February, with complete required weekly source coverage. Two later reports (2025weeks14/27) remain missing after public retrieval attempts. No full-year Swedish release, water seam into March, annual-price result or input promotion is claimed. The legacy generic water diagnostic key annual_generation_difference_mwh refers to the1416-hour WINDOW here, not annual energy. Boundary stock change and natural inflow explain added reservoir generation; it is not created freely.', '',
 'The source publication labels inflow as calculated; its independence from generation/stock accounting is not established. Thus this is retrospective physical reconstruction, not a weather-only hydro forecast. Generation agreement is not an independent test if the source inflow was derived from production. Unchanged run-of-river hydrology remains on its old source, so full national water-source reconciliation is not complete. These limitations matter for scenario/forecast use.', '',
 'The first Swedish attempt stopped because old reservoir output was zero in some hours. Its failure receipt remains in sweden-stock-window-v1. Version2 recovers original plant-capacity geographic shares for those hours, keeps existing supported-hour shares and verifies country/turbine totals. It does not infer a geographic share from zero generation or use observed generation to place supply.', '',
 f'Independent water residual{water_res:.3g}MWh passes original1e-4MWh gate. Source dates are independently rebuilt; regional/national published stocks agree within2GWh rounding. Full1416-hour polynomial bids, renewable responses, corridor flows, balance/bounds/residual work, generation and price metrics replay. Still the fast95-corridor model, not original PTDF or commercial capacity certification.', '',
 'Northern price bias remains positive; Denmark and some southern zones worsen. Next priority: validate actual north–south commercial constraints and Norwegian/Swedish zonal allocation/demand scope. No further optimizer expansion. No public deployment or accepted-baseline replacement.']
 (OUT/'report.md').write_text('\n'.join(lines)+'\n');print(json.dumps(checks),flush=True)

if __name__=='__main__':run()
