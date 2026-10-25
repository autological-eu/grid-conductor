"""Predeclared offline NO/SE water retiming under two public envelope proxies.

No observed prices enter retiming; monthly energy and stock endpoints are fixed.
This diagnoses the conflict of fixed hydro with independently bounded borders.
"""
import json,traceback
from pathlib import Path
import numpy as np
import xarray as xr
import run_independent_hourly_transport_2025 as parent
from network_stock_projection_2025 import project
from run_nordic_border_envelopes_v2_2025 import WATER,NORWAY,FROZEN,feasible
from conditional_monotone_market_2025 import ConditionalMarket
from hour_table_conditioner_2025 import feature_rows
from run_conditional_monotone_2025 import audit
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from supply_knot_network_2025 import generation
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json
OUT=ROOT/'data/bidding-zone-network-2025/nordic-network-stock-retiming-v1'
BORDERS=ROOT/'data/bidding-zone-network-2025/nordic-border-envelopes-v2'
NVE=ROOT/'data/hydro-observations-2025/nve-updated-model-v5/water.npz'
def read(path):
 with np.load(path) as z:return {k:z[k] for k in z.files}
def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'summary.json').exists() or (OUT/'failure.json').exists():raise ValueError('Existing study is sealed')
 base,(state,m,_,_)=parent.setup();s,d,_,_,sourcecap=state;T=1416
 no=read(NORWAY/'hydro.npz');se=read(WATER/'water.npz');nw=read(NVE)
 native=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1/native.nc'
 with xr.open_dataset(native) as n:
  mapping=dict(zip(n.buses_i.values,n.buses_bidding_zone.values));gross=np.zeros_like(d['load'][:T])
  for j,b in enumerate(n.loads_bus.values):
   zone=str(mapping[b]);zone='ES' if zone=='ES-IB-MA' else zone
   gross[:,s['zones'].index(zone)]+=n.loads_t_p_set.values[:T,j]
 fixed=gross-d['load'][:T];shares=np.zeros((T,m.nz,2));oldfixed=np.zeros_like(gross)
 for c,country in enumerate(['NO','SE']):
  mask=np.array([z.startswith(country) for z in s['zones']]);old=d['fixed_generation'][:T,s['countries'].index(country),s['technologies'].index('reservoir')]
  np.testing.assert_allclose(fixed[:,mask].sum(axis=1),old,atol=1e-4,rtol=0)
  f=np.divide(fixed[:,mask],old[:,None],out=np.zeros_like(fixed[:,mask]),where=old[:,None]>1e-6)
  if country=='SE':f[old<=1e-6]=se['static_allocation']
  if not np.allclose(f.sum(axis=1),1,atol=1e-8):raise ValueError('Unsupported allocation')
  shares[:,mask,c]=f;oldfixed[:,mask]=fixed[:,mask]
 available=m.capacity[:T]@m.Z*1000;load_other=d['load'][:T]+oldfixed
 inflow=np.c_[no['source_inflow'][:T],se['natural_inflow']];spill=np.c_[no['spill'][:T],np.zeros(T)]
 initial=np.array([(nw['initial']*nw['eta']).sum(),float(se['initial'])]);terminal=np.array([no['stock'][T-1],float(se['terminal'])]);cap=np.array([(nw['capacity']*nw['eta']).sum(),float(se['stockcap'])])
 target=np.c_[no['observed_stock_target'][1:T+1],se['stocktarget'][1:]];reference=np.c_[no['power'][:T],se['power']]
 plo=np.c_[nw['network_lower'][:T],np.zeros(T)];phi=np.c_[nw['network_upper'][:T],np.full(T,float(se['turbine']))]
 anchors={743:np.array([no['stock'][743],se['stock'][743]])}
 sources=parent.provenance(base)
 for p in [Path(__file__),ROOT/'tools/network_stock_projection_2025.py',NORWAY/'hydro.npz',WATER/'water.npz',NVE,native,FROZEN/'state-029.npz',FROZEN/'reference.npz',BORDERS/'summary.json']:sources[str(p.relative_to(ROOT))]=digest(p)
 base.save(OUT/'inputs.npz',M=m.M,available=available,load_without_hydro=load_other,shares=shares,inflow=inflow,spill=spill,initial=initial,terminal=terminal,stock_capacity=cap,power_lower=plo,power_upper=phi,target_stock=target,reference_power=reference,month_boundary=anchors[743])
 atomic_json(OUT/'provenance.json',sources)
 m.__class__=ConditionalMarket
 ref=read(FROZEN/'reference.npz');m.reference=ref['capacity_reference_gw'];centers=ref['training_condition_centers'];weights=read(FROZEN/'state-029.npz')['weights']
 oldlo=m.lower.copy();oldhi=m.upper.copy();cases=[]
 for endpoint in ['maxBorderFlow','maxExchanges']:
  boundpath=BORDERS/(endpoint+'-bounds.npz');bounds=read(boundpath);sources[str(boundpath.relative_to(ROOT))]=digest(boundpath)
  atomic_json(OUT/'progress.json',dict(stage='network_water_projection',endpoint=endpoint))
  try:
   witness,check=project(m.M,available,load_other,shares,bounds['lower_gw']*1000,bounds['upper_gw']*1000,inflow,spill,initial,terminal,cap,plo,phi,target,reference,anchors=anchors,margin_mw=0)
  except ValueError as error:
   cases.append(dict(endpoint=endpoint,status='projection_failed_no_relaxation',error=str(error)));atomic_json(OUT/(endpoint+'.json'),cases[-1]);print(endpoint,str(error),flush=True);continue
  base.save(OUT/(endpoint+'-water.npz'),**witness)
  corrected=d.copy();corrected['load']=d['load'].copy();corrected['load'][:T]=load_other-np.einsum('tzc,tc->tz',shares,witness['power']);corrected['fixed_generation']=d['fixed_generation'].copy()
  for c,country in enumerate(['NO','SE']):corrected['fixed_generation'][:T,s['countries'].index(country),s['technologies'].index('reservoir')]=witness['power'][:,c]
  for h in [slice(0,744),slice(744,T)]:np.testing.assert_allclose(witness['power'][h].sum(axis=0),reference[h].sum(axis=0),atol=1e-4,rtol=0)
  m.load=corrected['load']/1000;m.lower=oldlo.copy();m.upper=oldhi.copy();m.lower[:T]=bounds['lower_gw'];m.upper[:T]=bounds['upper_gw']
  check['hourly_generation_feasibility']=feasible(m,np.arange(T));assert not check['hourly_generation_feasibility']['infeasible']
  case=dict(endpoint=endpoint,water=check,months=[]);atomic_json(OUT/(endpoint+'.json'),case)
  for month in [1,2]:
   h=month_hours(month);X,_=feature_rows(s['groups'],d,h,m.reference,centers);theta=np.einsum('tgf,gfk->tgk',X,weights);p0=read(WATER/f'month-{month:02d}.npz')['prices']
   atomic_json(OUT/'progress.json',dict(stage='frozen_bid_market',endpoint=endpoint,month=month))
   try:r=m.solve(theta,h,p0=p0);checks=audit(m,theta,r)
   except Exception as error:
    case['months'].append(dict(month=month,status='market_failed_unchanged_gates',error=repr(error)));atomic_json(OUT/(endpoint+'.json'),case);continue
   gen=generation(s,corrected,sourcecap,r['quantities_gw']*1000,h);metrics,monthly=metric(s,corrected,r['prices'],gen,h,month)
   zones=[]
   for j in np.flatnonzero(np.isfinite(d['observed_prices']).all(axis=0)):
    truth=d['observed_prices'][h,j];zones.append(dict(zone=s['zones'][j],water_only_mae=float(abs(p0[:,j]-truth).mean()),after_mae=float(abs(r['prices'][:,j]-truth).mean()),after_bias=float((r['prices'][:,j]-truth).mean())))
   base.save(OUT/f'{endpoint}-{month:02d}.npz',hours=h,prices=r['prices'],quantities_gw=r['quantities_gw'],flows_gw=r['flows_gw'],generation=gen)
   case['months'].append(dict(month=month,metrics=metrics,monthly_generation_twh=monthly.tolist(),zones=zones,audit=checks,seconds=r['seconds']));print(endpoint,month,metrics,flush=True);atomic_json(OUT/(endpoint+'.json'),case)
  cases.append(case)
 atomic_json(OUT/'provenance.json',sources);assert all(digest(ROOT/p)==sha for p,sha in sources.items())
 atomic_json(OUT/'summary.json',dict(status='network_water_diagnostic_completed',cases=cases,limitations=['Independent JAO directional envelopes, not full Nordic FB domain.','Retrospective stock reconstruction; unchanged country geographic shares and ROR source.','All hours retained, no added generation, no softened physical/numerical gate.','Zero interior margin: boundary-only market prices may be unidentified.']))
 atomic_json(OUT/'progress.json',dict(stage='complete'))
if __name__=='__main__':
 try:run()
 except Exception:
  OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
