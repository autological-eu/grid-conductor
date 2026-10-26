"""Observed zonal hydro versus saved frozen-bid controls, no new market or fit.

SE reported B12 (and B11 if reported) is labelled reported hydro, not silently
reclassified by plant. Elhub hydro is metered production. Missing is never zero.
"""
import json,hashlib,datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import run_independent_hourly_transport_2025 as parent
from run_network_stock_retiming_2025 import read,OUT as PREVIOUS
from run_nordic_ror_reconciliation_2025 import OUT as RIVER
from norway_demand_allocation_2025 import SOURCE
from audit_2025_generation_observations import summarize,month_bounds
from carbon_pilot import parse_generation
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json
OUT=ROOT/'data/bidding-zone-source-audit-2025/nordic-zonal-hydro-comparison-v1'
def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'summary.json').exists():raise ValueError('Existing observation diagnostic sealed')
 base,(state,m,_,_)=parent.setup();s,d,_,_,_=state;T=1416;zones=['NO'+str(i) for i in range(1,6)]+['SE'+str(i) for i in range(1,5)];truth=np.full((T,len(zones)),np.nan);pins={str(Path(__file__).relative_to(ROOT)):digest(__file__)};coverage=[]
 source=json.loads((SOURCE/'summary.json').read_text());audit=json.loads((SOURCE/'audit.json').read_text());assert audit['summary_sha256']==digest(SOURCE/'summary.json');assert source['hourly_sha256']==digest(SOURCE/'hourly.csv')
 for r in source['sources']:
  raw=SOURCE/'raw'/(hashlib.sha256(r['url'].encode()).hexdigest()+'.json');assert digest(raw)==r['sha256'];pins[str(raw.relative_to(ROOT))]=r['sha256']
 frame=pd.read_csv(SOURCE/'hourly.csv');pins[str((SOURCE/'hourly.csv').relative_to(ROOT))]=digest(SOURCE/'hourly.csv')
 for j,zone in enumerate(zones[:5]):
  f=frame[frame.zone.eq(zone)].sort_values('utc');dates=pd.to_datetime(f.utc,utc=True).dt.as_unit('ns');np.testing.assert_array_equal(dates.to_numpy(),pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC').as_unit('ns').to_numpy());truth[:,j]=f.hydro_mwh.to_numpy(float)[:T];coverage.append(dict(zone=zone,provider='Elhub',category='metered hydro production',known_hours=int(np.isfinite(truth[:,j]).sum())))
 for j,zone in enumerate(zones[5:],5):
  for month in [1,2]:
   start,end=month_bounds(month);path=ROOT/f'data/carbon-pilot/map-2025/{zone}/{month:02d}.json';receipt=path.with_suffix('.receipt.json');r=json.loads(receipt.read_text());raw=ROOT/f'data/carbon-pilot/entsoe/raw/{zone}-{start:%Y%m%d}-{end:%Y%m%d}.xml';assert digest(path)==r['sha256'] and digest(raw)==r['source']['sha256'];rows=json.loads(path.read_text());summarize(parse_generation(raw.read_bytes(),r['eic']),rows,zone,start,end)
   for p in [path,receipt,raw]:pins[str(p.relative_to(ROOT))]=digest(p)
   offset=0 if month==1 else 744
   for k,row in enumerate(rows):
    kinds=set(row['reported_types'])&{'B11','B12'}
    if kinds and not kinds.intersection(row['missing_types']):truth[offset+k,j]=sum(row['generation_mwh_by_type'][v] for v in kinds)
  coverage.append(dict(zone=zone,provider='ENTSO-E A75/A16',category='reported B12; B11 included only if actually reported',known_hours=int(np.isfinite(truth[:,j]).sum())))
 data=read(PREVIOUS/'inputs.npz');models={};records=[]
 for label,folder in [('stock_and_border',PREVIOUS),('consistent_ror',RIVER)]:
  a=json.loads((folder/'audit.json').read_text());assert a['summary_sha256']==digest(folder/'summary.json');pins[str((folder/'audit.json').relative_to(ROOT))]=digest(folder/'audit.json');waterpath=folder/'maxBorderFlow-water.npz';water=read(waterpath);pins[str(waterpath.relative_to(ROOT))]=digest(waterpath);fixed=np.einsum('tzc,tc->tz',data['shares'],water['power']);output=np.column_stack([fixed[:,s['zones'].index(z)] for z in zones])
  for month in [1,2]:
   path=folder/f'maxBorderFlow-{month:02d}.npz';r=read(path);pins[str(path.relative_to(ROOT))]=digest(path);q=r['quantities_gw']*1000;h=r['hours']
   for j,zone in enumerate(zones):
    ids=[g for g,row in enumerate(s['groups']) if row['zone']==zone and row['technology']=='ror'];output[h,j]+=q[:,ids].sum(axis=1)
   for j,zone in enumerate(zones):
    good=np.isfinite(truth[h,j]);x=output[h,j][good];y=truth[h,j][good]
    records.append(dict(case=label,month=month,zone=zone,known_hours=int(good.sum()),model_on_known_hours_twh=float(x.sum()/1e6),reported_on_known_hours_twh=float(y.sum()/1e6),difference_twh=float((x-y).sum()/1e6),hourly_mae_mw=float(abs(x-y).mean()) if len(x) else None,shape_correlation=float(np.corrcoef(x,y)[0,1]) if len(x) and x.std()>0 and y.std()>0 else None))
  models[label]=output
 np.savez_compressed(OUT/'hourly.npz',zones=np.array(zones),reported_hydro_mwh=truth,**models)
 fig,axes=plt.subplots(2,2,figsize=(12,7))
 for ax,zone in zip(axes.ravel(),['NO3','NO4','SE1','SE2']):
  j=zones.index(zone);ax.plot(np.arange(59),truth[:,j].reshape(59,24).mean(axis=1),color='black',label='Reported hydro')
  for label,values in models.items():ax.plot(np.arange(59),values[:,j].reshape(59,24).mean(axis=1),label=label)
  ax.set(title=zone,ylabel='Daily mean hydro MW',xlabel='Days since 1 January2025');ax.legend(fontsize=7)
 fig.tight_layout();fig.savefig(OUT/'regional-hydro.png',dpi=150);plt.close(fig)
 atomic_json(OUT/'summary.json',dict(status='raw_observation_and_saved_zonal_dispatch_comparison_not_input_substitution',coverage=coverage,rows=records,sources=pins,limitations=['ENTSO-E Swedish reporting categories differ from model ROR/reservoir split; unreported categories are not zero-filled.','Observed category coverage does not certify whole-fleet completeness; national Ember scope differs.','Reported generation remains validation only, never a new availability or inflow curve.','Country stock-based reconstruction and JAO independent envelopes are retrospective/proxy inputs.']))
 print(json.dumps(records),flush=True)
if __name__=='__main__':run()
