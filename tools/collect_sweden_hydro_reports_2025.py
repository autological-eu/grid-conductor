"""Public dated weekly hydro reports; raw PDFs and receipts remain ignored."""
import concurrent.futures,datetime,hashlib,json,re,subprocess,time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/hydro-observations-2025/sweden-weekly-release-v2'
BASE='https://www.energiforetagen.se/globalassets/energiforetagen/statistik/kraftlaget/tidigare-kraftlagen/'

def collect(item):
 year,week=item;name=f'kraftlaget-sverige-veckorapport-vecka-{year}-{week:02d}.pdf';url=BASE+f'{year}/'+name;path=OUT/name
 receipt=path.with_suffix('.json')
 if receipt.exists():
  record=json.loads(receipt.read_text());assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'];return record
 r=requests.get(url,timeout=35)
 if r.status_code!=200 or not r.content.startswith(b'%PDF'):return dict(year=year,week=week,url=url,status=r.status_code,available=False)
 path.write_bytes(r.content);text=path.with_suffix('.txt');subprocess.run(['pdftotext','-layout',str(path),str(text)],check=True)
 s=text.read_text();first=s.split('\f')[0];digits=lambda x:float(re.sub(r'\s','',x).replace(',','.'))
 # Source prose line wrapping is removed for anchored value extraction.
 compact=' '.join(first.split())
 energy=re.search(r'energiinnehåll är beräknat till ([\d\s]+) GWh',compact)
 inflow=re.search(r'blev ([\d\s]+) GWh',compact)
 zones={}
 for z,pct,amount in re.findall(r'\b(SE[1-4])\s+([\d,]+)\s+([\d ]+?)(?=\s+SE[1-4]|\s+\d+\s|\s+Upplysningar|\s*$)',first):
  zones[z]=dict(percent=digits(pct),stock_gwh=digits(amount))
 # More reliable line-oriented numeric regional rows; no chart pixel extraction.
 zones={}
 for line in first.splitlines():
  match=re.search(r'\b(SE[1-4])\s+([\d,]+)\s+([\d ]+)\s*$',line)
  if match:zones[match[1]]=dict(percent=digits(match[2]),stock_gwh=digits(match[3]))
 record=dict(year=year,week=week,url=url,status=200,available=True,sha256=hashlib.sha256(r.content).hexdigest(),retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stock_gwh=digits(energy[1]) if energy else None,inflow_gwh=digits(inflow[1]) if inflow else None,zones=zones,text_sha256=hashlib.sha256(text.read_bytes()).hexdigest(),producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 receipt.write_text(json.dumps(record,indent=2)+'\n');return record

def run():
 OUT.mkdir(exist_ok=True)
 items=[(2024,52)]+[(2025,w) for w in range(1,53)]+[(2026,1)]
 with concurrent.futures.ThreadPoolExecutor(5) as pool:rows=list(pool.map(collect,items))
 (OUT/'manifest.json').write_text(json.dumps(dict(source='Energiföretagen Kraftläget public dated weekly PDFs',rows=rows),indent=2)+'\n')
 print(json.dumps(dict(requested=len(rows),available=sum(r.get('available',False) for r in rows),parsed_stock=sum(r.get('stock_gwh') is not None for r in rows),parsed_inflow=sum(r.get('inflow_gwh') is not None for r in rows),missing=[(r['year'],r['week']) for r in rows if not r.get('available')],parse_missing=[(r['year'],r['week']) for r in rows if r.get('available') and (r.get('stock_gwh') is None or r.get('inflow_gwh') is None)])),flush=True)

if __name__=='__main__':run()
