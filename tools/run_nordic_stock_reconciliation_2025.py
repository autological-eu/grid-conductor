"""NVE-stock correction with frozen bids; water/input/market witnesses retained."""
import json,time,traceback
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
import run_independent_hourly_transport_2025 as parent
from nve_hydro_inputs_2025 import compile_inputs
from stock_anchored_hydro_2025 import schedule
from conditional_monotone_market_2025 import ConditionalMarket
from run_conditional_monotone_2025 import audit
from hour_table_conditioner_2025 import feature_rows
from supply_knot_network_2025 import generation
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json
OUT=ROOT/'data/bidding-zone-network-2025/nordic-stock-reconciliation-v1'
NVE=ROOT/'data/hydro-observations-2025/nve-updated-model-v5'
FROZEN=ROOT/'data/bidding-zone-network-2025/higher-hour-table-learning-rates-v1/lr-1'

def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'summary.json').exists() or (OUT/'failure.json').exists():raise ValueError('Inspect existing experiment before restart')
 base,(state,m,network,_)=parent.setup();s,d,A,_,original_capacity=state
 meta=json.loads((NVE/'summary.json').read_text());assert digest(NVE/'water.npz')==meta['water_witness_sha256']
 with np.load(NVE/'water.npz') as z:water={k:z[k] for k in z.files}
 with xr.open_dataarray(ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/profile_hydro.nc') as weather:f,target,cap,hydrology=compile_inputs(weather.sel(countries='NO').values)
 old_power=water['power'].sum(axis=1);eta=water['eta'];inflow=(water['inflow']*eta).sum(axis=1);spill=(water['spill']*eta).sum(axis=1)
 initial=float((water['initial']*eta).sum());terminal=float((water['terminal']*eta).sum());capacity=float((water['capacity']*eta).sum())
 np.testing.assert_allclose(inflow,f*meta['reservoir_share'],atol=1e-6,rtol=0)
 np.testing.assert_allclose([initial,terminal,capacity],[target[0],target[-1],cap],atol=1e-6,rtol=0)
 ci=s['countries'].index('NO');ti=s['technologies'].index('reservoir');np.testing.assert_allclose(d['fixed_generation'][:,ci,ti],old_power,atol=1e-6,rtol=0)
 atomic_json(OUT/'progress.json',dict(stage='stock_projection'))
 power,stock,watercheck=schedule(inflow,initial,terminal,capacity,water['network_lower'],water['network_upper'],spill,target[1:],old_power)
 # Infer exact prepared zonal fixed injections from native gross load minus
 # compiled net load; reject rather than silently guess if lineage differs.
 native=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1/native.nc'
 with xr.open_dataset(native) as n:
  buses=list(n.buses_i.values);mapping=dict(zip(buses,n['buses_bidding_zone'].values));loadbus=n['loads_bus'].values;loads=n['loads_t_p_set'].values
  gross=np.zeros_like(d['load'])
  for j,b in enumerate(loadbus):
   zone=str(mapping[b]);zone='ES' if zone=='ES-IB-MA' else zone
   gross[:,s['zones'].index(zone)]+=loads[:,j]
 fixed=gross-d['load'];no=np.array([str(z).startswith('NO') for z in s['zones']])
 np.testing.assert_allclose(fixed[:,no].sum(axis=1),old_power,atol=1e-4,rtol=0)
 if fixed[:,no].min() < -1e-4:raise ValueError('Negative inferred fixed hydro')
 # Existing distribution only: this experiment does not introduce a new zonal allocation.
 shares=np.divide(fixed[:,no],old_power[:,None],out=np.zeros_like(fixed[:,no]),where=old_power[:,None]>0)
 if ((old_power<=0)&(power>1e-8)).any():raise ValueError('No supported zonal allocation for new positive hydro')
 delta=np.zeros_like(d['load']);delta[:,no]=(power-old_power)[:,None]*shares
 corrected=d.copy();corrected['load']=d['load']-delta;corrected['fixed_generation']=d['fixed_generation'].copy();corrected['fixed_generation'][:,ci,ti]=power
 # Gross load exactly conserved; fixed generation enters net demand exactly once.
 np.testing.assert_allclose((gross-corrected['load'])[:,no].sum(axis=1),power,atol=1e-4,rtol=0)
 base.save(OUT/'hydro.npz',power=power,stock=stock,old_power=old_power,observed_stock_target=target,source_inflow=inflow,spill=spill,zonal_delta_mw=delta)
 m.__class__=ConditionalMarket
 with np.load(FROZEN/'reference.npz') as z:m.reference=z['capacity_reference_gw'];centers=z['training_condition_centers']
 with np.load(FROZEN/'state-029.npz') as z:w=z['weights'];oldprices={1:z['training_prices'],2:z['forward_prices']}
 pinned=parent.provenance(base)
 for path in [Path(__file__),ROOT/'tools/stock_anchored_hydro_2025.py',ROOT/'tools/test_stock_anchored_hydro_2025.py',NVE/'summary.json',NVE/'water.npz',FROZEN/'state-029.npz',FROZEN/'reference.npz']:
  pinned[str(path.relative_to(ROOT))]=digest(path)
 atomic_json(OUT/'provenance.json',pinned);cases=[];complete=np.isfinite(d['observed_prices']).all(axis=0)
 # Do not alter network matrix, original available MW, source costs or bid coefficients.
 m.load=corrected['load']/1000
 for month in [1,2]:
  hours=month_hours(month);X,_=feature_rows(s['groups'],d,hours,m.reference,centers);theta=np.einsum('tgf,gfk->tgk',X,w)
  atomic_json(OUT/'progress.json',dict(stage='frozen_bid_forward',month=month))
  result=m.solve(theta,hours,p0=oldprices[month]);checks=audit(m,theta,result)
  gen=generation(s,corrected,original_capacity,result['quantities_gw']*1000,hours);metrics,monthly=metric(s,corrected,result['prices'],gen,hours,month)
  perzone=[]
  for j in np.flatnonzero(complete):
   truth=d['observed_prices'][hours,j];perzone.append(dict(zone=s['zones'][j],before_mae=float(abs(oldprices[month][:,j]-truth).mean()),after_mae=float(abs(result['prices'][:,j]-truth).mean()),before_bias=float((oldprices[month][:,j]-truth).mean()),after_bias=float((result['prices'][:,j]-truth).mean())))
  base.save(OUT/f'month-{month:02d}.npz',hours=hours,prices=result['prices'],quantities_gw=result['quantities_gw'],flows_gw=result['flows_gw'],generation=gen)
  cases.append(dict(month=month,metrics=metrics,monthly_generation_twh=monthly.tolist(),zones=perzone,audit=checks,certificate=result['certificate'],seconds=result['seconds']))
  print('CORRECTED',month,metrics,flush=True)
 if any(digest(ROOT/p)!=sha for p,sha in pinned.items()):raise ValueError('Changed sources')
 atomic_json(OUT/'summary.json',dict(status='source_stock_anchored_frozen_bid_comparison_complete',water=watercheck,cases=cases,hydrology_source=hydrology,limitations=['Observed stock trajectory makes this retrospective physical reconstruction, not operational hydro prediction.','Same existing zonal allocation, not verified NO1–NO5 reservoir routing.','Same independent-corridor fast market, not original PTDF certification.']))
 atomic_json(OUT/'progress.json',dict(stage='complete'))

if __name__=='__main__':
 try:run()
 except Exception:
  OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
