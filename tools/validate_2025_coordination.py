"""Compare two chronological blocks against the saved 48h native monolith.

This validates a conditional reference, not an annual optimum. Bounds and cuts
are reported on every iteration; an iteration limit is never a certificate.
"""
import argparse,gc,json,hashlib,time
from pathlib import Path
import numpy as np,pandas as pd,pypsa
from storage_coordinator import coordinate
from pypsa_storage_blocks import block
from run_network_benchmark import add_diagnostics

def run(folder,iterations):
 source=folder/'native-input.nc';data=json.loads((folder/'input.json').read_text());n=pypsa.Network(source)
 ids=n.storage_units.index;ns=len(ids);initial=n.storage_units.state_of_charge_initial.to_numpy();terminal=n.storage_units_t.state_of_charge_set.iloc[-1].reindex(ids).to_numpy();maximum=(n.storage_units.p_nom*n.storage_units.max_hours).to_numpy()
 n.storage_units_t.state_of_charge_set=pd.DataFrame(index=n.snapshots);add_diagnostics(n,data)
 started=time.monotonic();parts=[block(n,n.snapshots[:24],0,2),block(n,n.snapshots[24:],1,2)];bounds=[(v,v) for v in initial]+[(0,v) for v in maximum]+[(v,v) for v in terminal]
 output=folder/'coordination-reference.json'
 def report(row):
  clean={k:(None if isinstance(v,float) and not np.isfinite(v) else v) for k,v in row.items()};output.write_text(json.dumps(dict(status='running',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),hours=48,blocks=2,elapsed_seconds=time.monotonic()-started,**clean),indent=2)+'\n')
 reference=pypsa.Network(folder.parent/'monthly-dispatch-sequential/01.nc')
 warm=np.r_[initial,reference.storage_units_t.state_of_charge.iloc[23].reindex(ids).to_numpy(),terminal];del reference;gc.collect()
 result=coordinate(parts,bounds,initial_state=warm,max_iterations=iterations,absolute_gap=.01,relative_gap=1e-10,on_iteration=report)
 native=json.loads((folder/'native-cases.json').read_text())[0]['cost_eur'];state=result.pop('state');result['state_mwh']=None if state is None else state.tolist();result['native_monolithic_cost_eur']=native;result['difference_eur']=None if not np.isfinite(result['objective']) else result['objective']-native;result['scope']='48h conditional reference, not annual optimum';result['elapsed_seconds']=time.monotonic()-started
 for k in ['objective','gap']:result[k]=None if not np.isfinite(result[k]) else result[k]
 for row in result['history']:
  for k,v in row.items():
   if isinstance(v,float) and not np.isfinite(v):row[k]=None
 if result['status']=='converged' and abs(result['difference_eur'])>.02:raise RuntimeError('Monolithic parity failed')
 output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(result['status'],result['difference_eur'])
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);p.add_argument('--iterations',type=int,default=100);a=p.parse_args();run(a.folder,a.iterations)
