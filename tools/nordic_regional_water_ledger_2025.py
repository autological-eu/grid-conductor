"""Regional NVE stock/HBV ledger; observations only, never a dispatch input.

Shows whether national pooling hides geography. No generation-derived inflow.
Electrical-equivalent gross-stock/net-inflow basis remains an explicit caveat.
"""
import json,datetime as dt
import pandas as pd
import numpy as np
from nve_hydro_inputs_2025 import RELEASE,STOCK,HBV,utc_week
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json
OUT=ROOT/'data/bidding-zone-source-audit-2025/nordic-regional-water-ledger-v1'
def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'summary.json').exists():raise ValueError('Existing ledger sealed')
 receipt=json.loads((RELEASE/'receipt.json').read_text());assert digest(RELEASE/'table.xlsx')==receipt['sha256'];meta=json.loads(STOCK.with_name('nve-reservoir-history.meta.json').read_text());assert digest(STOCK)==meta['sha256']
 frame=pd.read_excel(RELEASE/'table.xlsx');raw=json.loads(STOCK.read_text());hours=pd.date_range('2025-01-01',periods=1416,freq='h',tz='UTC').as_unit('ns');edges=pd.date_range('2025-01-01',periods=1417,freq='h',tz='UTC').as_unit('ns');rows=[];inflows=[];stocks=[]
 for zone in ['NO','NO1','NO2','NO3','NO4','NO5']:
  kind,num=('NO',0) if zone=='NO' else ('EL',int(zone[-1]));records=sorted([r for r in raw if r['omrType']==kind and r['omrnr']==num and '2024-12-15'<=r['dato_Id']<='2025-03-15'],key=lambda r:r['dato_Id'])
  times=pd.DatetimeIndex([pd.Timestamp(r['dato_Id']).tz_localize('Europe/Oslo')+pd.DateOffset(days=1) for r in records]).tz_convert('UTC').as_unit('ns');assert times[0]<=edges[0] and times[-1]>=edges[-1];assert not times.has_duplicates
  stock=np.interp(edges.asi8,times.asi8,[r['fylling_TWh']*1e6 for r in records]);flow=np.full(1416,np.nan)
  for _,r in frame[(frame['Område']==zone)&(frame['År']==2025)].iterrows():
   start,end=utc_week(2025,int(r.Uke));mask=(hours>=start)&(hours<end);flow[mask]=float(r[HBV])*1000/((end-start).total_seconds()/3600)
  assert np.isfinite(flow).all() and (flow>=0).all();inflows.append(flow);stocks.append(stock)
  for month,start,end in [(1,0,744),(2,744,1416)]:rows.append(dict(zone=zone,month=month,hbv_inflow_twh=float(flow[start:end].sum()/1e6),stock_drawdown_twh=float((stock[start]-stock[end])/1e6),inflow_plus_drawdown_twh=float((flow[start:end].sum()+stock[start]-stock[end])/1e6)))
 # This ledger uses uniform within-week rates solely to calculate boundary-volume
 # diagnostics; it is not the weather-shaped dispatch inflow release.
 errors=dict(inflow_regional_minus_national_mwh=float(abs(np.sum(inflows[1:],axis=0)-inflows[0]).max()),stock_regional_minus_national_mwh=float(abs(np.sum(stocks[1:],axis=0)-stocks[0]).max()))
 atomic_json(OUT/'summary.json',dict(status='regional_source_ledger_not_dispatch_input',rows=rows,source_additivity=errors,sources={str(p.relative_to(ROOT)):digest(p) for p in [RELEASE/'table.xlsx',STOCK,ROOT/'tools/nve_hydro_inputs_2025.py',__import__('pathlib').Path(__file__)]},limitations=['HBV includes all usable hydro; reservoir/ROR split unresolved.','Stock drawdown plus HBV is not measured generation; spill/pumping/basis differences remain.','Uniform weekly rate used only for monthly boundary-volume ledger; no hourly generation inferred.']))
 print(json.dumps(dict(rows=rows,additivity=errors)),flush=True)
if __name__=='__main__':run()
