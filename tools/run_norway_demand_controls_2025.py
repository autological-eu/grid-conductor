"""Frozen-bid Norwegian demand geography controls, same all-European market.

Two predeclared allocations; no demand-total or price-target adjustment. Each
water schedule is recomputed with unchanged budgets under maxBorderFlow only.
"""
import json,traceback
from pathlib import Path
import numpy as np
import run_independent_hourly_transport_2025 as parent
from run_network_stock_retiming_2025 import read,BORDERS,FROZEN,OUT as PREVIOUS
from network_stock_projection_2025 import project
from norway_demand_allocation_2025 import observed,allocate,SOURCE
from run_nordic_border_envelopes_v2_2025 import feasible
from conditional_monotone_market_2025 import ConditionalMarket
from hour_table_conditioner_2025 import feature_rows
from run_conditional_monotone_2025 import audit
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from supply_knot_network_2025 import generation
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json
OUT=ROOT/'data/bidding-zone-network-2025/norway-demand-controls-v1'
KINDS=['metered_plus_original_residual','metered_proportional_scope_control']
def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'summary.json').exists() or (OUT/'failure.json').exists():raise ValueError('Existing study sealed')
 base,(state,m,_,_)=parent.setup();s,d,_,_,sourcecap=state;T=1416;input=read(PREVIOUS/'inputs.npz');bounds=read(BORDERS/'maxBorderFlow-bounds.npz');no=np.array([z.startswith('NO') for z in s['zones']]);metered=observed(np.array(s['zones'])[no]);gross=input['load_without_hydro'][:,no]
 pins=parent.provenance(base)
 for p in [Path(__file__),ROOT/'tools/norway_demand_allocation_2025.py',ROOT/'tools/network_stock_projection_2025.py',PREVIOUS/'inputs.npz',PREVIOUS/'summary.json',PREVIOUS/'audit.json',SOURCE/'hourly.csv',SOURCE/'summary.json',SOURCE/'audit.json',BORDERS/'maxBorderFlow-bounds.npz',FROZEN/'reference.npz',FROZEN/'state-029.npz']:pins[str(p.relative_to(ROOT))]=digest(p)
 atomic_json(OUT/'provenance.json',pins);base.save(OUT/'demand-sources.npz',zones=np.array(s['zones'])[no],metered_mwh=metered,original_gross_mw=gross)
 residual=gross.sum(axis=1)-metered.sum(axis=1);atomic_json(OUT/'scope.json',dict(country_demand_unchanged=True,min_residual_mw=float(residual.min()),negative_residual_hours=int((residual<0).sum()),limitations=['Metered consumption is not certified ENTSO-E total load; residual is not assumed to be losses alone.','Additive preserves residual original geographic shares; proportional is only a scope sensitivity control.']))
 m.__class__=ConditionalMarket;ref=read(FROZEN/'reference.npz');m.reference=ref['capacity_reference_gw'];centers=ref['training_condition_centers'];weights=read(FROZEN/'state-029.npz')['weights'];cases=[]
 m.lower[:T]=bounds['lower_gw'];m.upper[:T]=bounds['upper_gw']
 for kind in KINDS:
  case=dict(kind=kind,months=[])
  try:allocated,scope=allocate(gross,metered,kind)
  except ValueError as e:case.update(status='source_scope_rejected',error=str(e));cases.append(case);atomic_json(OUT/(kind+'.json'),case);continue
  load_other=input['load_without_hydro'].copy();load_other[:,no]=allocated;case['scope']=scope;base.save(OUT/(kind+'-demand.npz'),gross_no_mw=allocated,load_without_hydro=load_other)
  atomic_json(OUT/'progress.json',dict(stage='water_projection',kind=kind))
  args={k:input[k] for k in ['M','available','shares','inflow','spill','initial','terminal','stock_capacity','power_lower','power_upper','target_stock','reference_power']}
  try:water,check=project(**args,load_without_hydro=load_other,flow_lower=bounds['lower_gw']*1000,flow_upper=bounds['upper_gw']*1000,anchors={743:input['month_boundary']},margin_mw=0)
  except ValueError as e:case.update(status='projection_rejected_no_relaxation',error=str(e));cases.append(case);atomic_json(OUT/(kind+'.json'),case);continue
  base.save(OUT/(kind+'-water.npz'),**water);case['water']=check
  corrected=d.copy();corrected['load']=d['load'].copy();corrected['load'][:T]=load_other-np.einsum('tzc,tc->tz',input['shares'],water['power']);corrected['fixed_generation']=d['fixed_generation'].copy()
  for c,country in enumerate(['NO','SE']):corrected['fixed_generation'][:T,s['countries'].index(country),s['technologies'].index('reservoir')]=water['power'][:,c]
  m.load=corrected['load']/1000;case['feasibility']=feasible(m,np.arange(T));assert not case['feasibility']['infeasible']
  for month in [1,2]:
   h=month_hours(month);X,_=feature_rows(s['groups'],d,h,m.reference,centers);theta=np.einsum('tgf,gfk->tgk',X,weights);old=read(PREVIOUS/f'maxBorderFlow-{month:02d}.npz');p0=old['prices'];atomic_json(OUT/'progress.json',dict(stage='frozen_market',kind=kind,month=month))
   try:r=m.solve(theta,h,p0=p0);checks=audit(m,theta,r)
   except Exception as e:case['months'].append(dict(month=month,status='market_failed_original_gates',error=repr(e)));continue
   gen=generation(s,corrected,sourcecap,r['quantities_gw']*1000,h);metrics,monthly=metric(s,corrected,r['prices'],gen,h,month);zones=[]
   for j in np.flatnonzero(np.isfinite(d['observed_prices']).all(axis=0)):
    truth=d['observed_prices'][h,j];zones.append(dict(zone=s['zones'][j],before_mae=float(abs(p0[:,j]-truth).mean()),after_mae=float(abs(r['prices'][:,j]-truth).mean()),after_bias=float((r['prices'][:,j]-truth).mean())))
   base.save(OUT/f'{kind}-{month:02d}.npz',hours=h,prices=r['prices'],quantities_gw=r['quantities_gw'],flows_gw=r['flows_gw'],generation=gen)
   case['months'].append(dict(month=month,metrics=metrics,monthly_generation_twh=monthly.tolist(),zones=zones,audit=checks,seconds=r['seconds']));print(kind,month,metrics,flush=True);atomic_json(OUT/(kind+'.json'),case)
  cases.append(case);atomic_json(OUT/(kind+'.json'),case)
 assert all(digest(ROOT/p)==sha for p,sha in pins.items());atomic_json(OUT/'summary.json',dict(status='predeclared_geography_controls_complete_not_adoption',cases=cases));atomic_json(OUT/'progress.json',dict(stage='complete'))
if __name__=='__main__':
 try:run()
 except Exception:
  OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
