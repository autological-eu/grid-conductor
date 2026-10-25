"""Public JAO Nordic max-flow and max-exchange daily series; hashed raw cache."""
import concurrent.futures,datetime as dt,json,hashlib,time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/bidding-zone-source-audit-2025/nordic-border-envelopes-v1'

def collect(item):
 endpoint,date=item;day=date.strftime('%Y-%m-%d');folder=OUT/endpoint;folder.mkdir(exist_ok=True);path=folder/(day+'.json');receipt=path.with_suffix('.receipt.json')
 if path.exists() and receipt.exists():
  r=json.loads(receipt.read_text());assert hashlib.sha256(path.read_bytes()).hexdigest()==r['sha256'];return r
 a=date.isoformat().replace('+00:00','Z');b=(date+dt.timedelta(days=1)).isoformat().replace('+00:00','Z')
 url='https://publicationtool.jao.eu/nordic/api/data/'+endpoint;params=dict(FromUtc=a,ToUtc=b,Skip=0,Take=5000)
 for attempt in range(3):
  r=requests.get(url,params=params,timeout=45)
  if r.status_code==200:break
  if attempt==2:r.raise_for_status()
  time.sleep(2**attempt)
 payload=r.json();assert not payload.get('rejected') and len(payload['data'])==24,(day,endpoint,len(payload.get('data',[])))
 stamps=[x['dateTimeUtc'] for x in payload['data']];assert len(set(stamps))==24
 expected={(date+dt.timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ') for h in range(24)};assert set(stamps)==expected
 path.write_bytes(r.content);meta=dict(endpoint=endpoint,day=day,url=r.url,sha256=hashlib.sha256(r.content).hexdigest(),retrieved_utc=dt.datetime.now(dt.timezone.utc).isoformat(),rows=24,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest());receipt.write_text(json.dumps(meta,indent=2)+'\n');return meta

def run():
 OUT.mkdir(exist_ok=True);start=dt.datetime(2025,1,1,tzinfo=dt.timezone.utc);days=[start+dt.timedelta(days=d) for d in range(59)]
 with concurrent.futures.ThreadPoolExecutor(4) as pool:rows=list(pool.map(collect,[(e,d) for e in ['maxBorderFlow','maxExchanges'] for d in days]))
 (OUT/'manifest.json').write_text(json.dumps(dict(scope='Jan/Feb2025 published directional envelopes, not full FB domains',receipts=rows,hours_per_endpoint=1416),indent=2)+'\n');print('Verified118daily responses,1416hours per endpoint',flush=True)
if __name__=='__main__':run()
