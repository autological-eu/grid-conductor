"""Prepare fingerprinted monthly native LP blocks with resource guards; does not solve."""
import argparse,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
from monthly_dispatch import digest,save

def validate_calendar(network,year):
 import pandas as pd
 expected=pd.date_range(f'{year}-01-01',f'{year+1}-01-01',freq='h',inclusive='left')
 if not network.snapshots.equals(expected):raise ValueError('Complete chronological hourly calendar required')
 if not (network.snapshot_weightings.to_numpy()==1).all():raise ValueError('Hourly unit weights required')
 if len(network.stores) or network.generators.committable.any():raise ValueError('Unsupported Stores or commitment')
 for key in ['ramp_limit_up','ramp_limit_down']:
  if network.generators[key].notna().any():raise ValueError('Unsupported cross-month ramps')
 for key in ['e_sum_min','e_sum_max']:
  values=network.generators[key].dropna()
  if any(float(v)>0 if key=='e_sum_min' else float(v)<float('inf') for v in values):
   raise ValueError('Annual generation budgets need master constraints')
 for frame in [network.generators,network.lines,network.links,network.storage_units]:
  for key in ['p_nom_extendable','s_nom_extendable']:
   if key in frame and frame[key].any():raise ValueError('Expansion unsupported')
 if len(network.storage_units_t.state_of_charge_set.columns):raise ValueError('Hourly SOC targets unsupported')
 for key in ['p_min_pu','p_max_pu','efficiency_store','efficiency_dispatch','standing_loss']:
  if len(network.storage_units_t[key].columns):raise ValueError('Dynamic storage parameters need explicit envelopes')
 if not network.global_constraints.empty and not network.global_constraints.type.eq('transmission_volume_expansion_limit').all():
  raise ValueError('Global annual budgets unsupported')

def fingerprint(args):
 return dict(input_sha256=digest(args.input),year=args.year,
  preparation_sha256=digest(Path(__file__)),exporter_sha256=digest(Path(__file__).with_name('pypsa_storage_blocks.py')))

def worker(args):
 import pypsa
 from pypsa_storage_blocks import block
 from disk_storage_blocks import save_block
 n=pypsa.Network(args.input);validate_calendar(n,args.year)
 ignored=n.global_constraints.index.tolist()
 n.global_constraints.drop(n.global_constraints.index,inplace=True) # checked fixed capacities only
 snapshots=n.snapshots[n.snapshots.month==args.month]
 prepared=block(n,snapshots,args.month-1,12)
 path=args.output/f'{args.month:02d}.npz';save_block(path,prepared)
 save(args.output/f'{args.month:02d}.json',dict(**fingerprint(args),month=args.month,
  start=str(snapshots[0]),last=str(snapshots[-1]),hours=len(snapshots),
  block_sha256=digest(path),shared_variables=prepared.coupling.shape[1],
  storage_ids=n.storage_units.index.tolist(),
  source_initial_inventory_mwh=n.storage_units.state_of_charge_initial.tolist(),
  storage_capacity_mwh=(n.storage_units.p_nom*n.storage_units.max_hours).tolist(),
  source_cyclic=n.storage_units.cyclic_state_of_charge.tolist(),
  ignored_fixed_transmission_volume_constraints=ignored,
  method='prepared native chronological LP coefficients; no dispatch solve or annual optimality claim'))

def run(args):
 args.output.mkdir(parents=True,exist_ok=True);expected=fingerprint(args)
 for month in range(1,args.last_month+1):
  receipt=args.output/f'{month:02d}.json';artifact=args.output/f'{month:02d}.npz'
  if receipt.exists():
   item=json.loads(receipt.read_text())
   if any(item.get(k)!=v for k,v in expected.items()) or item['month']!=month or not artifact.exists() or digest(artifact)!=item['block_sha256']:
    raise ValueError('Prepared block integrity/source mismatch')
   continue
  if __import__('shutil').disk_usage(args.output).free<2*2**30:raise RuntimeError('Insufficient free disk for monthly preparation')
  command=[sys.executable,__file__,'--input',str(args.input),'--output',str(args.output),'--year',str(args.year),'--month',str(month)]
  with (args.output/f'{month:02d}.log').open('w') as log:
   child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save(args.output/'status.json',dict(status='preparing',month=month,pid=child.pid,**expected))
   peak=0
   while child.poll() is None:
    try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
    except FileNotFoundError:rss=0
    peak=max(peak,rss)
    if rss>args.memory_gib*2**30:
     os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=30)
     save(args.output/'status.json',dict(status='stopped_memory_guard',month=month,peak_rss_bytes=peak))
     raise RuntimeError('Monthly LP preparation exceeded memory guard')
    time.sleep(1)
   if child.returncode:
    save(args.output/'status.json',dict(status='failed',month=month,returncode=child.returncode,peak_rss_bytes=peak))
    raise RuntimeError('Monthly LP preparation failed; inspect its log')
   save(args.output/'status.json',dict(status='month_prepared',month=month,peak_rss_bytes=peak,**expected))
 save(args.output/'status.json',dict(status='requested_months_prepared',months=args.last_month,**expected,
  scope='prepared coefficients only; no annual solve'))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--year',type=int,default=2025);p.add_argument('--month',type=int);p.add_argument('--last-month',type=int,default=12);p.add_argument('--memory-gib',type=float,default=6.)
 args=p.parse_args()
 if not 1<=args.last_month<=12 or (args.month is not None and not 1<=args.month<=12) or not 0<args.memory_gib<=6:p.error('Invalid resource/month limit')
 args.input=args.input.resolve();args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=True)
 worker(args) if args.month is not None else run(args)
