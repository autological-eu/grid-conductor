"""Two predeclared source-envelope controls after frozen NO+SE water correction.

Published max-border-flow and max-bilateral-exchange are directional envelopes,
not interchangeable with exact Nordic flow-based domains or verified NTC.
"""
import json,traceback,time
from pathlib import Path
import numpy as np
from scipy.sparse import hstack,csc_matrix
import highspy
import run_independent_hourly_transport_2025 as parent
from conditional_monotone_market_2025 import ConditionalMarket
from run_conditional_monotone_2025 import audit
from hour_table_conditioner_2025 import feature_rows
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from supply_knot_network_2025 import generation
from forward_hourly_splines_2025 import month_hours
from run_differentiable_spline_2025 import atomic_json
SOURCE=ROOT/'data/bidding-zone-source-audit-2025/nordic-border-envelopes-v1'
WATER=ROOT/'data/bidding-zone-network-2025/sweden-stock-window-v2'
NORWAY=ROOT/'data/bidding-zone-network-2025/nordic-stock-reconciliation-v1'
FROZEN=ROOT/'data/bidding-zone-network-2025/higher-hour-table-learning-rates-v1/lr-1'
OUT=ROOT/'data/bidding-zone-network-2025/nordic-border-envelopes-v1'

def envelopes(m,endpoint):
 files=sorted((SOURCE/endpoint).glob('2025-*.json'));rows={};pinned={}
 for path in files:
  r=json.loads(path.with_suffix('.receipt.json').read_text());assert digest(path)==r['sha256'];pinned[str(path.relative_to(ROOT))]=r['sha256']
  for row in json.loads(path.read_text())['data']:
   stamp=np.datetime64(row['dateTimeUtc'].removesuffix('Z'),'h');h=int((stamp-np.datetime64('2025-01-01T00'))/np.timedelta64(1,'h'));assert h not in rows;rows[h]=row
 assert set(rows)==set(range(1416));lower=m.lower.copy();upper=m.upper.copy();changes=[];missing=[]
 for k,(a,b) in enumerate(m.edges):
  za,zb=m.zones[a],m.zones[b]
  if not any(z.startswith(('NO','SE','DK')) or z=='FI' for z in [za,zb]):continue
  alias=lambda z:'DE' if z=='DE-LU' else z
  forward='border_'+alias(za)+'_'+alias(zb);reverse='border_'+alias(zb)+'_'+alias(za)
  if not all(forward in rows[h] and reverse in rows[h] for h in rows):missing.append([za,zb]);continue
  f=np.array([rows[h][forward] for h in range(1416)],float)/1000;r=np.array([rows[h][reverse] for h in range(1416)],float)/1000
  if not np.isfinite(f).all() or not np.isfinite(r).all():raise ValueError('Missing numeric envelope')
  upper[:1416,k]=np.minimum(upper[:1416,k],f);lower[:1416,k]=np.maximum(lower[:1416,k],-r)
  if (lower[:1416,k]>upper[:1416,k]+1e-10).any():raise ValueError('Incompatible signed directional envelopes')
  changes.append(dict(zone0=za,zone1=zb,source_forward=forward,source_reverse=reverse,new_forward_min_mw=float(upper[:1416,k].min()*1000),new_forward_max_mw=float(upper[:1416,k].max()*1000)))
 return lower,upper,changes,missing,pinned

def feasible(m,hours):
 matrix=hstack([csc_matrix(m.Z.T),csc_matrix(m.M.T)],format='csc');cols=np.arange(matrix.shape[1],dtype=np.int32);rows=np.arange(m.nz,dtype=np.int32)
 solver=highspy.Highs();solver.setOptionValue('threads',1);solver.setOptionValue('output_flag',False);solver.setOptionValue('primal_feasibility_tolerance',1e-9)
 lp=highspy.HighsLp();lp.num_col_=matrix.shape[1];lp.num_row_=matrix.shape[0];lp.col_cost_=np.zeros(len(cols));lp.col_lower_=np.r_[np.zeros(m.ng),m.lower[hours[0]]];lp.col_upper_=np.r_[m.capacity[hours[0]],m.upper[hours[0]]];lp.row_lower_=lp.row_upper_=m.load[hours[0]];lp.a_matrix_.format_=highspy.MatrixFormat.kColwise;lp.a_matrix_.start_=matrix.indptr;lp.a_matrix_.index_=matrix.indices;lp.a_matrix_.value_=matrix.data;solver.passModel(lp)
 failed=[];residual=0.
 for h in hours:
  lo=np.r_[np.zeros(m.ng),m.lower[h]];hi=np.r_[m.capacity[h],m.upper[h]]
  solver.changeColsBounds(len(cols),cols,lo,hi);solver.changeRowsBounds(m.nz,rows,m.load[h],m.load[h]);solver.run()
  if solver.getModelStatus()!=highspy.HighsModelStatus.kOptimal:failed.append(dict(hour=int(h),status=solver.modelStatusToString(solver.getModelStatus())));continue
  x=np.array(solver.getSolution().col_value);e=max(float(abs(matrix@x-m.load[h]).max()),float(np.maximum(lo-x,0).max()),float(np.maximum(x-hi,0).max()))*1000;residual=max(residual,e)
 if residual>1e-4:raise ValueError('Feasibility replay gate failed')
 return dict(hours=len(hours),infeasible=failed,max_primal_mw=residual)

def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'summary.json').exists() or (OUT/'failure.json').exists():raise ValueError('Inspect existing study')
 assert (WATER/'audit.json').exists()
 base,(state,m,_,_)=parent.setup();s,d,_,_,sourcecap=state;m.__class__=ConditionalMarket
 with np.load(WATER/'water.npz') as z:delta=z['zonal_delta_mw'];sepower=z['power']
 with np.load(NORWAY/'hydro.npz') as z:nopower=z['power']
 corrected=d.copy();corrected['load']=d['load'].copy();corrected['load'][:1416]-=delta;corrected['fixed_generation']=d['fixed_generation'].copy();ti=s['technologies'].index('reservoir');corrected['fixed_generation'][:1416,s['countries'].index('NO'),ti]=nopower[:1416];corrected['fixed_generation'][:1416,s['countries'].index('SE'),ti]=sepower;m.load=corrected['load']/1000
 with np.load(FROZEN/'reference.npz') as z:m.reference=z['capacity_reference_gw'];centers=z['training_condition_centers']
 with np.load(FROZEN/'state-029.npz') as z:weights=z['weights']
 oldlo=m.lower.copy();oldhi=m.upper.copy();cases=[];sources=parent.provenance(base)
 for path in [Path(__file__),WATER/'summary.json',WATER/'audit.json',WATER/'water.npz',NORWAY/'hydro.npz',FROZEN/'state-029.npz']:sources[str(path.relative_to(ROOT))]=digest(path)
 for endpoint in ['maxBorderFlow','maxExchanges']:
  m.lower,m.upper=oldlo,oldhi;lo,hi,changes,missing,pinned=envelopes(m,endpoint);sources.update(pinned);m.lower,m.upper=lo,hi
  atomic_json(OUT/'progress.json',dict(stage='feasibility_check',endpoint=endpoint));check=feasible(m,np.arange(1416))
  case=dict(endpoint=endpoint,mapped_corridors=changes,unmapped_corridors=missing,feasibility=check,months=[])
  base.save(OUT/(endpoint+'-bounds.npz'),lower_gw=lo[:1416],upper_gw=hi[:1416])
  if check['infeasible']:
   case['status']='infeasible_inputs_no_price_score_no_relaxation';cases.append(case);atomic_json(OUT/(endpoint+'.json'),case);print(endpoint,'INFEASIBLE',len(check['infeasible']),flush=True);continue
  for month in [1,2]:
   h=month_hours(month);X,_=feature_rows(s['groups'],d,h,m.reference,centers);raw=np.einsum('tgf,gfk->tgk',X,weights)
   with np.load(WATER/f'month-{month:02d}.npz') as z:oldprices=z['prices']
   atomic_json(OUT/'progress.json',dict(stage='market_forward',endpoint=endpoint,month=month))
   r=m.solve(raw,h,p0=oldprices);checks=audit(m,raw,r);gen=generation(s,corrected,sourcecap,r['quantities_gw']*1000,h);metrics,monthly=metric(s,corrected,r['prices'],gen,h,month);zones=[];ok=np.isfinite(d['observed_prices']).all(axis=0)
   for j in np.flatnonzero(ok):
    truth=d['observed_prices'][h,j];zones.append(dict(zone=s['zones'][j],water_only_mae=float(abs(oldprices[:,j]-truth).mean()),after_mae=float(abs(r['prices'][:,j]-truth).mean()),after_bias=float((r['prices'][:,j]-truth).mean())))
   base.save(OUT/f'{endpoint}-{month:02d}.npz',hours=h,prices=r['prices'],quantities_gw=r['quantities_gw'],flows_gw=r['flows_gw'],generation=gen)
   case['months'].append(dict(month=month,metrics=metrics,monthly_generation_twh=monthly.tolist(),zones=zones,audit=checks,seconds=r['seconds']));print(endpoint,month,metrics,flush=True)
  case['status']='full_two_month_envelope_diagnostic';cases.append(case);atomic_json(OUT/(endpoint+'.json'),case)
 atomic_json(OUT/'provenance.json',sources);assert all(digest(ROOT/p)==sha for p,sha in sources.items())
 atomic_json(OUT/'summary.json',dict(status='predeclared_envelope_controls_completed',cases=cases,limitations=['Independent directional proxies, not exact NordicFB domain or verified NTC.','Source-covered JanFeb water reconstruction, not operational forecast or annual release.','Unmapped corridors retained with original physical limits; no fictitious added links.']))
 atomic_json(OUT/'progress.json',dict(stage='complete'))

if __name__=='__main__':
 try:run()
 except Exception:
  OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
