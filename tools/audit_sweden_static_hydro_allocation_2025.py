"""Independent market/water replay plus static geographic allocation checks."""
import numpy as np
import run_independent_hourly_transport_2025 as parent
import audit_network_stock_retiming_2025 as auditor
from nordic_ror_reconciliation_2025 import correct as river
from sweden_static_hydro_allocation_v2_2025 import correct as geography
from run_sweden_static_hydro_allocation_v2_2025 import OUT
from run_network_stock_retiming_2025 import read,WATER

def run():
 before=parent.setup
 def setup():
  base,(state,m,network,design)=before();state,_=river(state,m);state,_=geography(state,m)
  s=state[0];se=np.array([z.startswith('SE') for z in s['zones']]);inputs=read(OUT/'inputs.npz');shares=read(WATER/'water.npz')['static_allocation']
  np.testing.assert_allclose(inputs['shares'][:,se,1],np.broadcast_to(shares,(1416,len(shares))),atol=1e-7,rtol=0)
  return base,(state,m,network,design)
 parent.setup=setup;auditor.OUT=OUT;auditor.run()
if __name__=='__main__':run()
