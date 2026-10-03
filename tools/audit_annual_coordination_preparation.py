"""Verify all prepared month hashes, chronology and inventory coupling; no solve."""
import argparse,datetime,json
from pathlib import Path
from monthly_dispatch import digest,save
from disk_storage_blocks import load_block
from prepare_annual_coordination import fingerprint

def audit(args):
 folder=args.output;expected=fingerprint(args);previous=None;hours=0;size=0;ids=None
 for month in range(1,13):
  item=json.loads((folder/f'{month:02d}.json').read_text());path=folder/f'{month:02d}.npz'
  if any(item.get(k)!=v for k,v in expected.items()) or item['month']!=month or digest(path)!=item['block_sha256']:
   raise ValueError('Month source/code/block fingerprint mismatch')
  if ids is None:ids=item['storage_ids']
  if item['storage_ids']!=ids:raise ValueError('Storage identity mismatch')
  start=datetime.datetime.fromisoformat(item['start']);last=datetime.datetime.fromisoformat(item['last'])
  wanted=datetime.datetime(args.year,1,1) if previous is None else previous+datetime.timedelta(hours=1)
  if start!=wanted or start.month!=month or last.month!=month or (last-start).total_seconds()/3600+1!=item['hours']:
   raise ValueError('Broken monthly chronology')
  block=load_block(path);ns=len(ids)
  if block.coupling.shape[1]!=13*ns or any(int(col)//ns not in (month-1,month) for col in block.coupling.nonzero()[1]):
   raise ValueError('Unexpected inventory boundary coupling')
  hours+=item['hours'];size+=path.stat().st_size;previous=last;del block
 end=datetime.datetime(args.year+1,1,1)
 if previous+datetime.timedelta(hours=1)!=end or hours!=(end-datetime.datetime(args.year,1,1)).total_seconds()/3600:
  raise ValueError('Incomplete annual coverage')
 result=dict(status='prepared_blocks_verified',months=12,hours=hours,storage_units=len(ids),
  shared_variables=13*len(ids),bytes=size,**expected,scope='native monthly coefficients only; no annual solve')
 save(folder/'audit.json',result);return result
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
 parser.add_argument('--output',type=Path,required=True);parser.add_argument('--year',type=int,default=2025)
 args=parser.parse_args();args.input=args.input.resolve();args.output=args.output.resolve()
 print(json.dumps(audit(args),indent=2))
