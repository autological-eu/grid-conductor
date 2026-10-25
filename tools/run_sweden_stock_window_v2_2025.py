"""Source-covered Jan/Feb Swedish reservoir reconstruction, frozen European bids.

This is a finite-window physical-input diagnostic. No full-year input release is
claimed while two later Swedish weekly inflow reports remain unavailable.
"""
import json,traceback
from pathlib import Path
import numpy as np
import xarray as xr
import run_independent_hourly_transport_2025 as parent
from stock_anchored_hydro_2025 import schedule
from sweden_hydro_calendar_2025 import compile_window
from conditional_monotone_market_2025 import ConditionalMarket
from hour_table_conditioner_2025 import feature_rows
from run_conditional_monotone_2025 import audit
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from supply_knot_network_2025 import generation
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json
OUT=ROOT/'data/bidding-zone-network-2025/sweden-stock-window-v2'
NORWAY=ROOT/'data/bidding-zone-network-2025/nordic-stock-reconciliation-v1'
FROZEN=ROOT/'data/bidding-zone-network-2025/higher-hour-table-learning-rates-v1/lr-1'

def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'summary.json').exists() or (OUT/'failure.json').exists():raise ValueError('Inspect prior diagnostic before restart')
 base,(state,m,_,_)=parent.setup();s,d,_,_,original_capacity=state
 no_audit=json.loads((NORWAY/'audit.json').read_text());assert no_audit['summary_sha256']==digest(NORWAY/'summary.json')
 with np.load(NORWAY/'hydro.npz') as z:no_power=z['power'];no_delta=z['zonal_delta_mw']
 with xr.open_dataarray(ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/profile_hydro.nc') as weather:flow,stocktarget,stockcap,source=compile_window(weather.sel(countries='SE').values)
 original=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/networks/base_s_128_elec_.nc'
 with xr.open_dataset(original) as n:
  country=dict(zip(n.buses_i.values,n.buses_country.values));carrier=n.storage_units_carrier.values
  ids=n.storage_units_i.values[(carrier=='hydro')&np.array([country[b]=='SE' for b in n.storage_units_bus.values])]
  unit_nom={str(i):float(n.storage_units_p_nom.sel(storage_units_i=i)) for i in ids};turbine=sum(unit_nom.values())
  rorids=n.generators_i.values[(n.generators_carrier.values=='ror')&np.array([country[b]=='SE' for b in n.generators_bus.values])]
  ror=float(n.generators_p_nom.sel(generators_i=rorids).sum());share=turbine/(turbine+ror)
 ci=s['countries'].index('SE');ti=s['technologies'].index('reservoir');old=d['fixed_generation'][:1416,ci,ti]
 power,stock,watercheck=schedule(flow*share,stocktarget[0],stocktarget[-1],stockcap,np.zeros(1416),np.full(1416,turbine),np.zeros(1416),stocktarget[1:],old)
 # Reconcile the EXISTING fixed geographic allocation exactly against native gross load.
 native=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1/native.nc'
 with xr.open_dataset(native) as n:
  mapping=dict(zip(n.buses_i.values,n.buses_bidding_zone.values));gross=np.zeros_like(d['load'])
  for j,b in enumerate(n.loads_bus.values):
   zone=str(mapping[b]);zone='ES' if zone=='ES-IB-MA' else zone
   gross[:,s['zones'].index(zone)]+=n.loads_t_p_set.values[:,j]
 se=np.array([z.startswith('SE') for z in s['zones']]);fixed=(gross-d['load'])[:1416,se]
 np.testing.assert_allclose(fixed.sum(axis=1),old,atol=1e-4,rtol=0)
 # Zero old production contains no geographic identity. Recover the original
 # source allocation from plant-capacity shares, never from observed generation.
 mapping_path=ROOT/'data/bidding-zone-network-2025/annual-v7/mapping.json'
 mapping_meta=json.loads(mapping_path.read_text());static=np.zeros(len(s['zones']))
 for entry in mapping_meta['allocation']:
  if entry['component']!='FixedReservoir' or entry['name'] not in unit_nom:continue
  for bus,fraction in entry['shares'].items():
   zone=mapping_meta['zone_by_bus'][bus];static[s['zones'].index(zone)]+=unit_nom[entry['name']]*fraction
 np.testing.assert_allclose(static[se].sum(),turbine,atol=1e-7,rtol=0)
 static=static[se]/turbine
 allocation=np.divide(fixed,old[:,None],out=np.broadcast_to(static,fixed.shape).copy(),where=old[:,None]>1e-6)
 np.testing.assert_allclose(allocation.sum(axis=1),1,atol=1e-7,rtol=0)
 delta=no_delta.copy();delta[:1416,se]+=(power-old)[:,None]*allocation
 corrected=d.copy();corrected['load']=d['load']-delta;corrected['fixed_generation']=d['fixed_generation'].copy()
 corrected['fixed_generation'][:,s['countries'].index('NO'),ti]=no_power;corrected['fixed_generation'][:1416,ci,ti]=power
 base.save(OUT/'water.npz',power=power,stock=stock,stocktarget=stocktarget,natural_inflow=flow*share,source_total_inflow=flow,zero_hour_allocation_fallback=np.array(old<=1e-6),static_allocation=static,initial=stocktarget[0],terminal=stocktarget[-1],stockcap=stockcap,turbine=turbine,reservoir_share=share,old_power=old,zonal_delta_mw=delta[:1416])
 m.__class__=ConditionalMarket
 with np.load(FROZEN/'reference.npz') as z:m.reference=z['capacity_reference_gw'];centers=z['training_condition_centers']
 with np.load(FROZEN/'state-029.npz') as z:w=z['weights'];oldprices={1:z['training_prices'],2:z['forward_prices']}
 pinned=parent.provenance(base)
 for path in [Path(__file__),ROOT/'tools/sweden_hydro_calendar_2025.py',ROOT/'tools/stock_anchored_hydro_2025.py',NORWAY/'summary.json',NORWAY/'audit.json',NORWAY/'hydro.npz',FROZEN/'state-029.npz',original,mapping_path]:pinned[str(path.relative_to(ROOT))]=digest(path)
 for p,r in source['sources'].items():pinned[p]=r['sha256']
 atomic_json(OUT/'provenance.json',pinned);m.load=corrected['load']/1000;cases=[];complete=np.isfinite(d['observed_prices']).all(axis=0)
 for month in [1,2]:
  h=month_hours(month);X,_=feature_rows(s['groups'],d,h,m.reference,centers);raw=np.einsum('tgf,gfk->tgk',X,w)
  atomic_json(OUT/'progress.json',dict(stage='frozen_bids',month=month))
  result=m.solve(raw,h,p0=oldprices[month]);checks=audit(m,raw,result);gen=generation(s,corrected,original_capacity,result['quantities_gw']*1000,h);metrics,monthly=metric(s,corrected,result['prices'],gen,h,month);zones=[]
  for j in np.flatnonzero(complete):
   truth=d['observed_prices'][h,j];zones.append(dict(zone=s['zones'][j],before_mae=float(abs(oldprices[month][:,j]-truth).mean()),after_mae=float(abs(result['prices'][:,j]-truth).mean()),before_bias=float((oldprices[month][:,j]-truth).mean()),after_bias=float((result['prices'][:,j]-truth).mean())))
  base.save(OUT/f'month-{month:02d}.npz',hours=h,prices=result['prices'],quantities_gw=result['quantities_gw'],flows_gw=result['flows_gw'],generation=gen)
  cases.append(dict(month=month,metrics=metrics,monthly_generation_twh=monthly.tolist(),zones=zones,audit=checks,seconds=result['seconds']));print('NO+SE',month,metrics,flush=True)
 if any(digest(ROOT/p)!=sha for p,sha in pinned.items()):raise ValueError('Changed source')
 atomic_json(OUT/'summary.json',dict(status='two_month_frozen_bid_diagnostic_complete_not_annual_release',water=watercheck,source=source,cases=cases,limitations=['January/February fully covered, two later2025weekly inflow reports missing: annual reconstruction blocked.','Published Swedish inflow estimation may use generation/stock data; not weather-only forecast.','Reservoir fraction uses existing capacity allocation; unchanged ROR availability retains old hydrology source, not full national flow reconciliation.','Existing positive-hour allocation retained; zero original-generation hours use original plant-capacity geographic allocation. No commercial-domain or original PTDF certification.']))

if __name__=='__main__':
 try:run()
 except Exception:
  OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
