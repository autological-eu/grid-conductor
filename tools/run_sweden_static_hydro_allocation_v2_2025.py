"""Fresh frozen-bid geography control; consistent ROR, same network/water gates."""
import traceback
from pathlib import Path
import run_independent_hourly_transport_2025 as parent
import run_network_stock_retiming_2025 as producer
from nordic_ror_reconciliation_2025 import correct as river,NATIVE,NO_META
from sweden_static_hydro_allocation_v2_2025 import correct as geography
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json
OUT=ROOT/'data/bidding-zone-network-2025/sweden-static-hydro-allocation-v2'
def configure():
 before=parent.setup;before_pins=parent.provenance
 def setup():
  base,(state,m,network,design)=before();state,river_meta=river(state,m);state,geo=geography(state,m);OUT.mkdir(exist_ok=True);atomic_json(OUT/'input-control.json',dict(river=river_meta,geography=geo));base.save(OUT/'capacity.npz',capacity=state[1]['capacity'][:1416],source_capacity=state[-1][:1416]);return base,(state,m,network,design)
 def provenance(base):
  pins=before_pins(base)
  for p in [Path(__file__),ROOT/'tools/nordic_ror_reconciliation_2025.py',ROOT/'tools/sweden_static_hydro_allocation_v2_2025.py',NATIVE,NO_META,OUT/'input-control.json',OUT/'capacity.npz']:pins[str(p.relative_to(ROOT))]=digest(p)
  return pins
 parent.setup=setup;parent.provenance=provenance;producer.OUT=OUT
if __name__=='__main__':
 try:configure();producer.run()
 except Exception:
  OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
