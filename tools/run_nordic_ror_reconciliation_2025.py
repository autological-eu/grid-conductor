"""Fresh source-consistent ROR control; reuse sealed water/network producer."""
import json,traceback
from pathlib import Path
import run_network_stock_retiming_2025 as producer
import run_independent_hourly_transport_2025 as parent
from nordic_ror_reconciliation_2025 import correct,NATIVE,NO_META
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json
OUT=ROOT/'data/bidding-zone-network-2025/nordic-ror-reconciliation-v1'
def configure():
 original_setup=parent.setup;original_provenance=parent.provenance
 def setup():
  base,(state,m,network,design)=original_setup();state,records=correct(state,m)
  OUT.mkdir(exist_ok=True);atomic_json(OUT/'river-inputs.json',dict(countries=records,limitations=['Existing nameplate-based reservoir/ROR split and country-only runoff shape remain assumptions.','Swedish source inflow may depend on generation accounting: retrospective reconstruction, not independent forecast.','New ROR profile is natural-flow availability; curtailment/spill is explicit, never observed generation.']))
  base.save(OUT/'river-capacity.npz',capacity=state[1]['capacity'][:1416],source_capacity=state[-1][:1416])
  return base,(state,m,network,design)
 def provenance(base):
  pins=original_provenance(base)
  for path in [Path(__file__),ROOT/'tools/nordic_ror_reconciliation_2025.py',NATIVE,NO_META,OUT/'river-inputs.json',OUT/'river-capacity.npz']:pins[str(path.relative_to(ROOT))]=digest(path)
  return pins
 parent.setup=setup;parent.provenance=provenance;producer.OUT=OUT
if __name__=='__main__':
 try:configure();producer.run()
 except Exception:
  OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
