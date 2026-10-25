"""Independent replay: water, source borders, supply bids, generation and scores."""
import json
import numpy as np
import run_independent_hourly_transport_2025 as parent
from run_network_stock_retiming_2025 import OUT,BORDERS,FROZEN,read
from audit_nordic_stock_reconciliation_2025 import primitive
from conditional_monotone_market_2025 import ConditionalMarket
from hour_table_conditioner_2025 import feature_rows
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from supply_knot_network_2025 import generation
from run_differentiable_spline_2025 import atomic_json

def run():
 summary=json.loads((OUT/'summary.json').read_text())
 for path,sha in json.loads((OUT/'provenance.json').read_text()).items():assert digest(ROOT/path)==sha,path
 data=read(OUT/'inputs.npz');_,(state,m,_,_)=parent.setup();s,d,_,_,cap=state;m.__class__=ConditionalMarket
 reference=read(FROZEN/'reference.npz');m.reference=reference['capacity_reference_gw'];centers=reference['training_condition_centers'];w=read(FROZEN/'state-029.npz')['weights'];checks=[]
 for case in summary['cases']:
  endpoint=case['endpoint']
  if case.get('status')=='projection_failed_no_relaxation':checks.append(dict(endpoint=endpoint,status=case['status']));continue
  water=read(OUT/(endpoint+'-water.npz'));bounds=read(BORDERS/(endpoint+'-bounds.npz'));p=water['power'];stock=water['stock'];previous=np.vstack([data['initial'],stock[:-1]])
  residual=float(abs(stock-previous-data['inflow']+p+data['spill']).max());assert residual<=1e-4
  for x,lo,hi in [(p,data['power_lower'],data['power_upper']),(stock,0,data['stock_capacity']),(water['flows_mw'],bounds['lower_gw']*1000,bounds['upper_gw']*1000)]:assert max(np.maximum(lo-x,0).max(),np.maximum(x-hi,0).max())<=1e-4
  np.testing.assert_allclose(stock[-1],data['terminal'],atol=1e-4,rtol=0);np.testing.assert_allclose(stock[743],data['month_boundary'],atol=1e-4,rtol=0)
  newload=data['load_without_hydro']-np.einsum('tzc,tc->tz',data['shares'],p)
  g=newload-water['flows_mw']@data['M'];assert max(np.maximum(-g,0).max(),np.maximum(g-data['available'],0).max())<=1e-4
  np.testing.assert_allclose(g,water['feasible_generation_mw'],atol=1e-7,rtol=0)
  for h in [slice(0,744),slice(744,1416)]:np.testing.assert_allclose(p[h].sum(axis=0),data['reference_power'][h].sum(axis=0),atol=1e-4,rtol=0)
  corrected=d.copy();corrected['load']=d['load'].copy();corrected['load'][:1416]=newload;corrected['fixed_generation']=d['fixed_generation'].copy()
  for c,country in enumerate(['NO','SE']):corrected['fixed_generation'][:1416,s['countries'].index(country),s['technologies'].index('reservoir')]=p[:,c]
  m.load=corrected['load']/1000;m.lower[:1416]=bounds['lower_gw'];m.upper[:1416]=bounds['upper_gw'];monthchecks=[]
  for record in case['months']:
   month=record['month']
   if 'metrics' not in record:monthchecks.append(dict(month=month,status=record['status']));continue
   result=read(OUT/f'{endpoint}-{month:02d}.npz');h=result['hours'];price=result['prices'];q=result['quantities_gw'];X,_=feature_rows(s['groups'],d,h,m.reference,centers);theta=np.einsum('tgf,gfk->tgk',X,w);slopes=.05+20*np.logaddexp(0,theta[...,1:]);A=m.capacity[h];C=m.reference[None];b0=m.source[h]+theta[...,0];bid=b0+primitive(q/C,slopes);bA=b0+primitive(A/C,slopes);pp=price[:,m.zone];tau=m.thermal_tau
   wanted=b0+tau*(np.logaddexp(0,(pp-b0)/tau)-np.logaddexp(0,(pp-bA)/tau));err=float(abs((bid-wanted)[:,~m.zero]).max());assert err<1e-6
   rq=A[:,m.zero]/.01*m.renewable_tau*(np.logaddexp(0,pp[:,m.zero]/m.renewable_tau)-np.logaddexp(0,(pp[:,m.zero]-.01)/m.renewable_tau));assert abs(rq-q[:,m.zero]).max()*1000<1e-4
   lo=m.lower[h];hi=m.upper[h];v=price@m.M.T/m.cost;flow=lo+m.flow_tau*(np.logaddexp(0,(v-lo)/m.flow_tau)-np.logaddexp(0,(v-hi)/m.flow_tau));assert abs(flow-result['flows_gw']).max()*1000<1e-4
   balance=q@m.Z+flow@m.M-m.load[h];assert abs(balance).max()*1000<1e-4 and (abs(balance*price).sum(axis=1)*1000).max()<.05
   assert max(np.maximum(-q,0).max(),np.maximum(q-A,0).max(),np.maximum(lo-flow,0).max(),np.maximum(flow-hi,0).max())*1000<1e-4
   gen=generation(s,corrected,cap,q*1000,h);np.testing.assert_allclose(gen,result['generation'],atol=1e-7,rtol=0);metrics,_=metric(s,corrected,price,gen,h,month)
   for k in ['price_mae','generation_mae_twh']:np.testing.assert_allclose(metrics[k],record['metrics'][k],atol=1e-9,rtol=0)
   monthchecks.append(dict(month=month,hours=len(h),inverse_eur_mwh=err,balance_mw=float(abs(balance).max()*1000)))
  checks.append(dict(endpoint=endpoint,water_residual_mwh=residual,months=monthchecks))
 atomic_json(OUT/'audit.json',dict(status='completed_independent_replay_including_failed_cases',cases=checks,source_sha256=digest(__file__),summary_sha256=digest(OUT/'summary.json')));print(json.dumps(checks),flush=True)
if __name__=='__main__':run()
