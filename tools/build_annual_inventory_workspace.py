"""Build annual boundary/reachability constraints and hash-verified sequential warm state."""
import argparse,json
from pathlib import Path
import numpy as np
import pypsa
from scipy import sparse
from annual_inventory_workspace import boundaries,validate_warm
from inventory_reachability import envelope
from monthly_dispatch import digest,save
from prepare_annual_coordination import validate_calendar,fingerprint
def build(args):
 expected=fingerprint(args);receipts=[]
 for month in range(1,13):
  item=json.loads((args.output/f'{month:02d}.json').read_text())
  if any(item.get(k)!=v for k,v in expected.items()) or digest(args.output/f'{month:02d}.npz')!=item['block_sha256']:
   raise ValueError('Prepared block fingerprint mismatch')
  receipts.append(item)
 ids=receipts[0]['storage_ids']
 if any(r['storage_ids']!=ids for r in receipts):raise ValueError('Storage identities changed')
 n=pypsa.Network(args.input);validate_calendar(n,args.year)
 if n.storage_units.index.tolist()!=ids:raise ValueError('Source storage order changed')
 units=n.storage_units;ns=len(ids);initial=units.state_of_charge_initial.to_numpy();capacity=(units.p_nom*units.max_hours).to_numpy()
 bounds,E,rhs=boundaries(capacity,initial,units.cyclic_state_of_charge.to_numpy())
 warm=[initial];previous=None;warm_receipts=[]
 for month in range(1,13):
  receipt_path=args.sequential/f'{month:02d}.json';item=json.loads(receipt_path.read_text())
  if item['input_sha256']!=expected['input_sha256'] or item['month']!=month or digest(args.sequential/f'{month:02d}.nc')!=item['result_sha256']:
   raise ValueError('Sequential warm source/result fingerprint mismatch')
  if set(item['initial_inventory_mwh'])!=set(ids) or set(item['ending_inventory_mwh'])!=set(ids):
   raise ValueError('Warm storage identities changed')
  start=np.array([item['initial_inventory_mwh'][key] for key in ids])
  if not np.array_equal(start,initial if previous is None else previous):raise ValueError('Broken warm chronology')
  previous=np.array([item['ending_inventory_mwh'][key] for key in ids]);warm.append(previous)
  warm_receipts.append(digest(receipt_path))
 state=validate_warm(np.concatenate(warm),bounds,E,rhs)
 data=[];rows=[];cols=[];limits=[]
 def constraint(entries,limit):
  row=len(limits);limits.append(float(limit))
  for col,value in entries:rows.append(row);cols.append(col);data.append(float(value))
 for period in range(12):
  times=n.snapshots[n.snapshots.month==period+1]
  for j,key in enumerate(ids):
   unit=units.loc[key];water=n.storage_units_t.inflow.loc[times,key].to_numpy() if key in n.storage_units_t.inflow else np.zeros(len(times))
   retention=np.full(len(times),1-unit.standing_loss)
   if period==0 and not unit.cyclic_state_of_charge:retention[0]=1.
   a,gain,drain,cap=envelope(capacity[j],retention,np.full(len(times),-unit.p_min_pu*unit.p_nom*unit.efficiency_store),np.full(len(times),unit.p_max_pu*unit.p_nom/unit.efficiency_dispatch),water)
   constraint([(period*ns+j,-a),((period+1)*ns+j,1.)],gain)
   constraint([(period*ns+j,a),((period+1)*ns+j,-1.)],drain)
   constraint([((period+1)*ns+j,1.)],cap)
 U=sparse.csr_matrix((data,(rows,cols)),shape=(len(limits),len(bounds)));limits=np.array(limits)
 violation=max(0.,float(np.max(U@state-limits)))
 if violation>1e-7:raise ValueError('Warm inventories fail monthly reachability')
 sparse.save_npz(args.output/'master-equality.npz',E);sparse.save_npz(args.output/'master-inequality.npz',U)
 np.savez_compressed(args.output/'master-state.npz',bounds=np.array(bounds),rhs=rhs,limit=limits,warm_state_mwh=state)
 result=dict(status='inventory_workspace_prepared',**expected,storage_units=ns,shared_variables=len(bounds),
  cyclic_closure_equalities=E.shape[0],reachability_constraints=U.shape[0],warm_reachability_violation=violation,
  sequential_receipt_sha256=warm_receipts,workspace_sha256={name:digest(args.output/name) for name in ['master-equality.npz','master-inequality.npz','master-state.npz']},
  scope='boundary/reachability validation only; warm dispatch must be independently re-solved before accepting an upper bound',
  annual_boundary='cyclic units optimise free initial inventory with final=initial; noncyclic initial inventory fixed to source')
 save(args.output/'master-workspace.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['sequential_receipt_sha256','workspace_sha256']},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--sequential',type=Path,required=True);p.add_argument('--year',type=int,default=2025)
 args=p.parse_args();args.input=args.input.resolve();args.output=args.output.resolve();args.sequential=args.sequential.resolve();build(args)
