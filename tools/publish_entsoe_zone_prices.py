"""Offline A44 price collector; publish hourly means, never credentials."""
import os,json,hashlib,datetime as dt
from concurrent.futures import ThreadPoolExecutor,as_completed
import xml.etree.ElementTree as ET
from pathlib import Path
from eu_zones import ZONES,EXTERIORS
from flow_tracing import fetch,parse_day_ahead_prices,hourly
root=Path(__file__).resolve().parents[1];cache=root/'data/price-trace/entsoe';out=root/'public/research/zone-prices-2025';out.mkdir(exist_ok=True)
secret=root/'data/price-trace/.entsoe-key'
if not os.environ.get('ENTSOE_API_KEY') and secret.exists():os.environ['ENTSOE_API_KEY']=secret.read_text().strip()
manifest=json.loads((out/'manifest.json').read_text())
registry={z[0]:z[1] for z in ZONES+EXTERIORS}
start=dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)
def collect(zone):
 eic=registry[zone];samples={};receipts=[];failures=[]
 for month in range(1,13):
  begin=dt.datetime(2025,month,1,tzinfo=dt.timezone.utc);end=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc) if month==12 else dt.datetime(2025,month+1,1,tzinfo=dt.timezone.utc)
  params=dict(documentType='A44',processType='A01',in_Domain=eic,out_Domain=eic,periodStart=begin.strftime('%Y%m%d%H%M'),periodEnd=end.strftime('%Y%m%d%H%M'))
  try:
   raw=fetch(params,cache/zone)
   document=ET.fromstring(raw)
   for element in document.iter():element.tag=element.tag.split('}')[-1]
   for series in document.findall('TimeSeries'):
    for field in ('in_Domain.mRID','out_Domain.mRID'):
     domain=series.findtext(field)
     if domain is not None and domain!=eic:raise ValueError('Response domain mismatch')
   parsed=parse_day_ahead_prices(raw)
   for stamp,value in parsed.items():
    if not begin<=stamp<end:continue
    if stamp in samples and samples[stamp]!=value:raise ValueError('Conflicting price intervals')
    samples[stamp]=value
   receipts.append(dict(month=month,request=params,sha256=hashlib.sha256(raw).hexdigest()))
  except Exception as e:failures.append(dict(month=month,error=str(e)))
 values=[hourly(samples,start+dt.timedelta(hours=i)) for i in range(8760)]
 known=sum(v is not None for v in values)
 if known:
  (out/(zone+'.json')).write_text(json.dumps(values,separators=(',',':'))+'\n')
  result=dict(status='published',source='ENTSO-E A44 day-ahead prices',known_hours=known,receipts=receipts,failed_months=failures)
 else:result=dict(status='unavailable',source='ENTSO-E A44',failed_months=failures)
 return zone,result

pending=[zone for zone,item in manifest.items() if item['status']!='published' or item.get('failed_months')]
with ThreadPoolExecutor(max_workers=3) as pool:
 futures=[pool.submit(collect,zone) for zone in pending]
 for future in as_completed(futures):
  zone,result=future.result();manifest[zone]=result
  temp=out/'manifest.tmp';temp.write_text(json.dumps(manifest,indent=2)+'\n');temp.replace(out/'manifest.json')
  print(zone,result.get('known_hours',0),'hours',len(result.get('failed_months',[])),'failed months',flush=True)
