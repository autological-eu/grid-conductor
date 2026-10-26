"""Rebuild hydro availability, then reuse independent water/market replay."""
import json
import numpy as np
import run_independent_hourly_transport_2025 as parent
import audit_network_stock_retiming_2025 as auditor
from nordic_ror_reconciliation_2025 import correct,NORWAY,WATER,NO_META
from run_nordic_ror_reconciliation_2025 import OUT
from run_network_stock_retiming_2025 import read
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json

def run():
 original=parent.setup;records=json.loads((OUT/'river-inputs.json').read_text());saved=read(OUT/'river-capacity.npz');source_no=read(NORWAY/'hydro.npz');source_se=read(WATER/'water.npz');no_share=json.loads(NO_META.read_text())['reservoir_share'];checks=[]
 def setup():
  base,(state,m,network,design)=original();changed,rows=correct(state,m);s,d,_,_,_=state
  np.testing.assert_array_equal(changed[1]['capacity'][:1416],saved['capacity']);np.testing.assert_array_equal(changed[-1][:1416],saved['source_capacity'])
  for row in records['countries']:
   ids=[i for i,g in enumerate(s['groups']) if g['technology']=='ror' and g['country']==row['country']];nom=np.array(row['turbines_mw']);share=row['reservoir_share'];total=source_no['source_inflow'][:1416]/no_share if row['country']=='NO' else source_se['source_total_inflow'];potential=np.outer(total*(1-share),nom/nom.sum());expected=np.minimum(potential,nom)
   np.testing.assert_allclose(saved['capacity'][:,ids],expected,atol=1e-8,rtol=0);spill=potential-expected;np.testing.assert_allclose(expected.sum(axis=1)+spill.sum(axis=1)+total*share,total,atol=1e-7,rtol=0)
   checks.append(dict(country=row['country'],river_and_reservoir_partition_residual_mwh=float(abs(expected.sum(axis=1)+spill.sum(axis=1)+total*share-total).max()),maximum_turbine_excess_mw=float(np.maximum(expected-nom,0).max())))
  untouched=[i for i,g in enumerate(s['groups']) if not(g['technology']=='ror' and g['country'] in ['NO','SE'])];np.testing.assert_array_equal(saved['capacity'][:,untouched],d['capacity'][:1416,untouched])
  return base,(changed,m,network,design)
 parent.setup=setup;auditor.OUT=OUT;auditor.run()
 atomic_json(OUT/'river-audit.json',dict(status='same_source_partition_turbine_and_unchanged_other_technology_replay_passed',cases=checks,full_market_audit_sha256=digest(OUT/'audit.json'),summary_sha256=digest(OUT/'summary.json'),producer_sha256=digest(__file__)))
if __name__=='__main__':run()
