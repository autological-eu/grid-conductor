"""Resumable 2025 observed generation collection for every displayed map zone.

Bounded concurrent zones, sequential monthly API requests per zone; failures recorded without credentials, never zero-filled.
Germany's national generation is explicitly not DE-LU bidding-zone generation.
"""
import datetime as dt,json,os,hashlib,time,threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from carbon_pilot import ROOT,UTC,AREAS,download,parse_generation,calculate,iso
from eu_zones import ZONES,EXTERIORS
from monthly_dispatch import save

def registry():
 result={label:dict(eic=gen or price,scope='bidding zone' if label.startswith(('DK','SE','NO','IT-')) else 'national area') for label,price,gen,_ in ZONES}
 result.update({label:dict(eic=eic,scope='bidding zone' if label.startswith('NO') else 'national area') for label,eic,_,_ in EXTERIORS})
 result['DE-LU']['scope']='Germany national generation proxy; excludes Luxembourg, not DE-LU zonal generation'
 displayed=json.loads((ROOT/'public/research/zone-prices-2025/manifest.json').read_text())
 if set(displayed)-set(result):raise ValueError('Map zones missing generation domain candidates')
 return {z:result[z] for z in displayed}

def collect():
 output=ROOT/'data/carbon-pilot/map-2025';output.mkdir(parents=True,exist_ok=True)
 areas=registry();completed=[];failed=[]
 order=sorted(areas,key=lambda z:(z not in ('FR','DK1','DK2'),z))
 lock=threading.Lock();active={}
 for zone in areas:AREAS[{'DK1':'DK-DK1','DK2':'DK-DK2'}.get(zone,zone)]=areas[zone]['eic']
 def progress(zone,month):
  with lock:
   active[zone]=month
   save(output/'status.json',dict(status='collecting',pid=os.getpid(),workers=3,active_zone_months=dict(active),completed_zone_months=len(completed),failed_zone_months=len(failed)))
 def collect_zone(zone):
  label={'DK1':'DK-DK1','DK2':'DK-DK2'}.get(zone,zone)
  AREAS[label]=areas[zone]['eic']
  folder=output/zone;folder.mkdir(exist_ok=True)
  for month in range(1,13):
   progress(zone,month)
   start=dt.datetime(2025,month,1,tzinfo=UTC);end=dt.datetime(2026,1,1,tzinfo=UTC) if month==12 else dt.datetime(2025,month+1,1,tzinfo=UTC)
   path=folder/f'{month:02d}.json';receipt=folder/f'{month:02d}.receipt.json'
   if path.exists() and receipt.exists():
    r=json.loads(receipt.read_text())
    if r['eic']!=areas[zone]['eic'] or r['sha256']!=hashlib.sha256(path.read_bytes()).hexdigest():raise ValueError('Cached generation fingerprint mismatch')
    completed.append((zone,month));continue
   try:
    raw,provenance=download(label,start,end,ROOT/'data/carbon-pilot/entsoe/raw')
    rows=calculate(parse_generation(raw,areas[zone]['eic']),zone,start,end,1500)
    if [r['start'] for r in rows]!=[iso(start+dt.timedelta(hours=i)) for i in range(int((end-start).total_seconds()/3600))]:raise ValueError('Chronology mismatch')
    save(path,rows);save(receipt,dict(zone=zone,month=month,eic=areas[zone]['eic'],geographic_scope=areas[zone]['scope'],source=provenance,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),complete_hours=sum(r['primary_generation_mwh'] is not None for r in rows)))
    completed.append((zone,month));print(f'Collected {zone} month {month}',flush=True)
   except Exception as error:
    # Only error class is recorded: exceptions may contain a private request URL.
    failure=dict(zone=zone,month=month,error_type=type(error).__name__,status='unavailable_not_zero')
    save(folder/f'{month:02d}.failure.json',failure);failed.append(failure);print(f'Unavailable {zone} month {month}: {type(error).__name__}',flush=True)
   time.sleep(.5)
  with lock:active.pop(zone,None)
 with ThreadPoolExecutor(max_workers=3) as pool:
  list(pool.map(collect_zone,order))
 save(output/'status.json',dict(status='collection_pass_finished',completed_zone_months=len(completed),expected_zone_months=len(areas)*12,failures=failed,registry=areas))
if __name__=='__main__':collect()
