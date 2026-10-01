"""Guarded, resumable sequential monthly dispatch; NOT annual optimisation.

Carries StorageUnit inventory without monthly resets. Initial inventories are
explicitly fixed to source initial values; annual cyclic units close to those
values in December. Choosing initial inventory and future water values optimally
requires a coordinating model, which this rolling-horizon experiment does not do.
"""
import argparse,gc,hashlib,json,math,os,signal,subprocess,sys,time
from pathlib import Path

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def save(path,value):
 temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temp.replace(path)

def validate_state(state,ids):
 if set(state)!=set(ids) or any(not isinstance(v,(int,float)) or not math.isfinite(v) or v < -1e-5 for v in state.values()):
  raise ValueError('Invalid checkpoint inventory or asset identity')

def worker(args):
 import pypsa
 n=pypsa.Network(args.input)
 if len(n.stores) or n.generators.committable.any():raise ValueError('Stores and unit commitment require additional boundary state')
 for c in ['e_sum_min','e_sum_max']:
  if c in n.generators and any(math.isfinite(v) and (v>0 if c=='e_sum_min' else True) for v in n.generators[c].dropna()):raise ValueError('Generator energy budgets require coordinating state')
 if any(n.generators[c].notna().any() for c in ['ramp_limit_up','ramp_limit_down']):raise ValueError('Ramp constraints need previous-dispatch state; unsupported')
 for frame in [n.generators,n.storage_units,n.links,n.lines]:
  for col in ['p_nom_extendable','s_nom_extendable']:
   if col in frame and frame[col].any():raise ValueError('Capacity expansion is unsupported')
 if not n.global_constraints.empty:
  if not n.global_constraints.type.eq('transmission_volume_expansion_limit').all():raise ValueError('Annual budgets require coordinating state')
  n.global_constraints.drop(n.global_constraints.index,inplace=True) # no extendable transmission assets
 ids=n.storage_units.index.tolist();initial=n.storage_units.state_of_charge_initial.to_dict()
 cyclic=n.storage_units.index[n.storage_units.cyclic_state_of_charge].tolist()
 state=initial if args.month==1 else json.loads((args.output/f'{args.month-1:02d}.json').read_text())['ending_inventory_mwh']
 validate_state(state,ids)
 snapshots=n.snapshots[n.snapshots.month==args.month]
 if not len(snapshots):raise ValueError('Month absent from input')
 n.set_snapshots(snapshots)
 n.storage_units['cyclic_state_of_charge']=False
 if 'cyclic_state_of_charge_per_period' in n.storage_units:n.storage_units['cyclic_state_of_charge_per_period']=False
 n.storage_units['state_of_charge_initial']=n.storage_units.index.map(state)
 def closure(network,snapshots):
  if args.month==12 and cyclic:
   import xarray as xr
   var=network.model['StorageUnit-state_of_charge'].sel(snapshot=snapshots[-1],name=cyclic)
   values=xr.DataArray([initial[k] for k in cyclic],coords={'name':cyclic},dims=['name'])
   network.model.add_constraints(var==values,name='checkpoint-annual-inventory-closure')
 status,condition=n.optimize(solver_name='highs',solver_options={'threads':2,'solver':'ipm','run_crossover':'off'},include_objective_constant=False,extra_functionality=closure)
 if status!='ok' or condition!='optimal':raise ValueError(f'Solve failed: {status}/{condition}')
 ending=n.storage_units_t.state_of_charge.iloc[-1].to_dict();validate_state(ending,ids)
 result=args.output/f'{args.month:02d}.nc';n.export_to_netcdf(result)
 save(args.output/f'{args.month:02d}.json',dict(schema_version=1,input_sha256=digest(args.input),month=args.month,start=str(snapshots[0]),last=str(snapshots[-1]),hours=len(snapshots),initial_inventory_mwh=state,ending_inventory_mwh=ending,objective_eur=float(n.objective),result_sha256=digest(result),method='sequential_monthly_fixed_initial_inventory_not_annual_optimum',annual_boundary='cyclic units close in December to explicit source initial inventory; free cyclic initial inventory is not optimised',source_nuclear_availability='2024 proxy'))

def run(args):
 args.output.mkdir(parents=True,exist_ok=True);source=digest(args.input)
 previous=None
 for month in range(1,args.last_month+1):
  checkpoint=args.output/f'{month:02d}.json';result=args.output/f'{month:02d}.nc'
  if checkpoint.exists():
   item=json.loads(checkpoint.read_text())
   if item['input_sha256']!=source or item['month']!=month or not result.exists() or digest(result)!=item['result_sha256']:raise ValueError('Checkpoint/source integrity mismatch')
   if previous is not None and item['initial_inventory_mwh']!=previous:raise ValueError('Broken month-to-month inventory continuity')
   previous=item['ending_inventory_mwh'];continue
  command=[sys.executable,__file__,'--input',str(args.input),'--output',str(args.output),'--month',str(month)]
  peak=0;started=time.monotonic()
  with (args.output/f'{month:02d}.log').open('w') as log:
   child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   while child.poll() is None:
    try:
     rss=sum(int(s.split()[1])*1024 for s in Path(f'/proc/{child.pid}/status').read_text().splitlines() if s.startswith('VmRSS:'))
    except FileNotFoundError:rss=0
    peak=max(peak,rss)
    if rss>args.memory_gib*2**30:
     os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=30)
     save(args.output/'status.json',dict(status='stopped_memory_guard',month=month,peak_rss_bytes=peak));raise RuntimeError('Monthly solve exceeded memory guard')
    time.sleep(1)
   if child.returncode:raise RuntimeError(f'Month {month} failed; inspect its log')
  item=json.loads(checkpoint.read_text());previous=item['ending_inventory_mwh']
  save(args.output/'status.json',dict(status='month_complete',month=month,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started,method=item['method']))
 save(args.output/'status.json',dict(status='requested_months_complete',months=args.last_month,method='sequential_monthly_not_annual_optimum'))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--last-month',type=int,default=12);p.add_argument('--month',type=int);p.add_argument('--memory-gib',type=float,default=6)
 a=p.parse_args();a.input=a.input.resolve();a.output=a.output.resolve()
 if not 1<=a.last_month<=12 or not 0<a.memory_gib<=6:p.error('Invalid month or memory limit')
 if a.month:worker(a)
 else:run(a)
