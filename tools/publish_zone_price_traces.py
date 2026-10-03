"""Cache public historical zone prices and publish complete hourly means."""
import json,time,urllib.request,urllib.error,hashlib,datetime
from pathlib import Path
root=Path(__file__).resolve().parents[1];cache=root/'data/price-trace';cache.mkdir(exist_ok=True)
out=root/'public/research/zone-prices-2025';out.mkdir(exist_ok=True)
targets=json.loads((root/'public/research/entsoe-fast-targets.json').read_text())['targets']
zones=sorted({z for r in targets if (r.get('deadweight_loss_meur_year') or 0)>0 for z in r['border'].split('>')})
# Public provider uses exchange-area aliases for Italian zones.
aliases={'IT-CNOR':'IT-Centre-North','IT-CSUD':'IT-Centre-South','IT-SARD':'IT-Sardinia','IT-SUD':'IT-South'}
start=int(datetime.datetime(2025,1,1,tzinfo=datetime.timezone.utc).timestamp());manifest={}
allowed={'AT','BE','CH','CZ','DE-LU','DK1','DK2','FR','HU','IT-North','NL','NO2','PL','SE4','SI'}
for zone in zones:
 if zone not in allowed:
  manifest[zone]=dict(status='unavailable',error='No openly licensed trace from this provider; direct ENTSO-E collection required')
  (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
  continue
 path=cache/(zone+'.json');url=f'https://api.energy-charts.info/price?bzn={aliases.get(zone,zone)}&start=2025-01-01&end=2025-12-31'
 try:
  if not path.exists():
   time.sleep(2)
   for attempt in range(3):
    try:raw=urllib.request.urlopen(url,timeout=40).read();break
    except urllib.error.HTTPError as e:
     if e.code!=429 or attempt==2:raise
     time.sleep(20)
   d=json.loads(raw)
   if 'unix_seconds' not in d or 'price' not in d:raise ValueError('No price series')
   path.write_bytes(raw)
  raw=path.read_bytes();d=json.loads(raw)
  if 'CC BY 4.0' not in d.get('license_info',''):raise ValueError('Public republication is not permitted by this source')
  quarters={};t=d['unix_seconds'];prices=d['price']
  if d['unit']!='EUR / MWh' or len(t)!=len(prices):raise ValueError('Invalid units or alignment')
  for i,(stamp,value) in enumerate(zip(t,prices)):
   duration=t[i+1]-stamp if i+1<len(t) else 900
   if duration not in (900,3600):raise ValueError('Unsupported interval duration')
   if value is None:continue
   for instant in range(stamp,stamp+duration,900):quarters[instant]=float(value)
  hourly=[]
  for hour in range(8760):
   samples=[quarters.get(start+hour*3600+q*900) for q in range(4)]
   hourly.append(None if any(v is None for v in samples) else sum(samples)/4)
  if not any(v is not None for v in hourly):raise ValueError('No observed 2025 hours')
  (out/(zone+'.json')).write_text(json.dumps(hourly,separators=(',',':'))+'\n')
  manifest[zone]=dict(status='published',known_hours=sum(v is not None for v in hourly),url=url,sha256=hashlib.sha256(raw).hexdigest(),license=d.get('license_info'))
 except Exception as e:manifest[zone]=dict(status='unavailable',error=str(e),url=url)
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(zone,manifest[zone]['status'],flush=True)
