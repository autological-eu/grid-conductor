"""Compare two chronological blocks against the saved 48h native monolith.

This validates a conditional reference, not an annual optimum. Bounds and cuts
are reported on every iteration; an iteration limit is never a certificate.
"""
import argparse,gc,json,hashlib,time,os
from datetime import datetime,timezone
from pathlib import Path
import numpy as np,pandas as pd,pypsa
from storage_coordinator import coordinate
from inventory_reachability import envelope
from disk_storage_blocks import save_block,DiskBlocks
from pypsa_storage_blocks import block
from run_network_benchmark import add_diagnostics

def run(folder,iterations,disk_blocks=False):
 output=folder/'coordination-reference.json'
 previous=json.loads(output.read_text()) if output.exists() else {}
 source=folder/'native-input.nc'
 output.write_text(json.dumps(dict(status='preparing',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),previous_status=previous.get('status'),previous_iteration=previous.get('iteration',previous.get('iterations')),scope='48h conditional reference, not annual optimum'),indent=2)+'\n')
 data=json.loads((folder/'input.json').read_text());n=pypsa.Network(source)
 ids=n.storage_units.index;ns=len(ids);initial=n.storage_units.state_of_charge_initial.to_numpy();terminal=n.storage_units_t.state_of_charge_set.iloc[-1].reindex(ids).to_numpy();maximum=(n.storage_units.p_nom*n.storage_units.max_hours).to_numpy()
 n.storage_units_t.state_of_charge_set=pd.DataFrame(index=n.snapshots);add_diagnostics(n,data)
 started=time.monotonic()
 if disk_blocks:
  paths=[folder/f'coordination-block-{period}.npz' for period in range(2)]
  manifest=folder/'coordination-blocks-manifest.json'
  dependencies=[source,folder/'input.json',Path(__file__),Path(__file__).with_name('pypsa_storage_blocks.py'),Path(__file__).with_name('run_network_benchmark.py'),Path(__file__).with_name('disk_storage_blocks.py')]
  fingerprint={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies}
  saved=json.loads(manifest.read_text()) if manifest.exists() else None
  if saved is not None and saved['dependencies']==fingerprint:
   parts=DiskBlocks(paths,saved['blocks'])
   # Verify all archives now, before expensive independent relaxations.
   for prepared in parts:del prepared
  else:
   for period,times in enumerate([n.snapshots[:24],n.snapshots[24:]]):
    prepared=block(n,times,period,2)
    save_block(paths[period],prepared);del prepared;gc.collect()
   parts=DiskBlocks(paths)
   temp=manifest.with_suffix('.tmp')
   temp.write_text(json.dumps(dict(dependencies=fingerprint,blocks=parts.hashes))+'\n');temp.replace(manifest)

 else:parts=[block(n,n.snapshots[:24],0,2),block(n,n.snapshots[24:],1,2)]
 bounds=[(v,v) for v in initial]+[(0,v) for v in maximum]+[(v,v) for v in terminal]
 if not np.all(n.snapshot_weightings.to_numpy()==1):raise ValueError('Reference reachability requires hourly weights')
 for key in ['p_min_pu','p_max_pu','efficiency_store','efficiency_dispatch','standing_loss']:
  if len(n.storage_units_t[key].columns):raise ValueError('Dynamic storage parameters need hourly envelope inputs')
 constraints=[];limits=[]
 for period,times in enumerate([n.snapshots[:24],n.snapshots[24:]]):
  for j,key in enumerate(ids):
   unit=n.storage_units.loc[key]
   inflow=n.storage_units_t.inflow.loc[times,key].to_numpy() if key in n.storage_units_t.inflow else np.zeros(len(times))
   retention=np.full(len(times),1-unit.standing_loss)
   if period==0 and not unit.cyclic_state_of_charge:retention[0]=1.
   a,gain,drain,cap=envelope(maximum[j],retention,np.full(len(times),-unit.p_min_pu*unit.p_nom*unit.efficiency_store),np.full(len(times),unit.p_max_pu*unit.p_nom/unit.efficiency_dispatch),inflow)
   row=np.zeros(3*ns);row[period*ns+j]=-a;row[(period+1)*ns+j]=1.;constraints.append(row);limits.append(gain)
   constraints.append(-row);limits.append(drain)
   row=np.zeros(3*ns);row[(period+1)*ns+j]=1.;constraints.append(row);limits.append(cap)
 output=folder/'coordination-reference.json'
 checkpoint=folder/'coordination-cuts.json';source_hash=hashlib.sha256(source.read_bytes()).hexdigest();resume=None
 if checkpoint.exists():
  resume=json.loads(checkpoint.read_text())
  if resume['source_sha256']!=source_hash:raise ValueError('Coordinator checkpoint source mismatch')
 def save_cuts(value):
  value['source_sha256']=source_hash
  # JSON history uses null for unbounded initial upper bounds.
  for item in value['history']:
   for k,v in item.items():
    if isinstance(v,float) and not np.isfinite(v):item[k]=None
  temp=checkpoint.with_suffix('.tmp');temp.write_text(json.dumps(value,allow_nan=False)+'\n');temp.replace(checkpoint)
 def report(row):
  clean={k:(None if isinstance(v,float) and not np.isfinite(v) else v) for k,v in row.items()};output.write_text(json.dumps(dict(status='running',pid=os.getpid(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),hours=48,blocks=2,elapsed_seconds=time.monotonic()-started,**clean),indent=2)+'\n')
 reference=pypsa.Network(folder.parent/'monthly-dispatch-sequential/01.nc')
 warm=np.r_[initial,reference.storage_units_t.state_of_charge.iloc[23].reindex(ids).to_numpy(),terminal];del reference;gc.collect()
 try:
  result=coordinate(parts,bounds,initial_state=warm,max_iterations=iterations,absolute_gap=.001,relative_gap=0.,on_iteration=report,resume=resume,on_checkpoint=save_cuts,inequality=constraints,limit=limits)
 except Exception as error:
  progress=json.loads(output.read_text()) if output.exists() else {}
  progress.update(status='failed_not_certified',error=str(error));output.write_text(json.dumps(progress,indent=2)+'\n');raise
 native=json.loads((folder/'native-cases.json').read_text())[0]['cost_eur'];state=result.pop('state');result['state_mwh']=None if state is None else state.tolist();result['native_monolithic_cost_eur']=native;result['difference_eur']=None if not np.isfinite(result['objective']) else result['objective']-native;result['scope']='48h conditional reference, not annual optimum';result['elapsed_seconds']=time.monotonic()-started
 for k in ['objective','gap']:result[k]=None if not np.isfinite(result[k]) else result[k]
 for row in result['history']:
  for k,v in row.items():
   if isinstance(v,float) and not np.isfinite(v):row[k]=None
 if result['status']=='converged' and (abs(result['difference_eur'])>.02 or result['lower_bound']>native+.02):
  result['status']='failed_not_certified'
  result['error']='Monolithic objective/bound parity failed'
  output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
  raise RuntimeError(result['error'])
 output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(result['status'],result['difference_eur'])
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);p.add_argument('--iterations',type=int,default=100);p.add_argument('--disk-blocks',action='store_true',help='Load one prepared LP block at a time');a=p.parse_args();run(a.folder,a.iterations,a.disk_blocks)
