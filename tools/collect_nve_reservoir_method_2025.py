"""Public NVE method and reservoir/plant energy-equivalent source tables."""
import concurrent.futures,datetime,hashlib,json,subprocess
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/bidding-zone-source-audit-2025/nve-reservoir-method-v1'
SOURCES={'method.pdf':'https://webfileservice.nve.no/API/PublishedFiles/Download/64edbe40-b965-4c90-a114-88162ffff454/201903383/3435075','reservoir.xlsx':'https://www.nve.no/media/18839/nmag_magasin.xlsx','plant.xlsx':'https://www.nve.no/media/18838/nmag_kraftverk.xlsx','reservoir-plant.xlsx':'https://www.nve.no/media/18840/nmag_magasin_kraftverk.xlsx'}
def collect(item):
 name,url=item;path=OUT/name;receipt=path.with_suffix('.receipt.json')
 if path.exists() and receipt.exists():
  row=json.loads(receipt.read_text());assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'];return row
 r=requests.get(url,timeout=45);r.raise_for_status()
 if name.endswith('.pdf') and not r.content.startswith(b'%PDF'):raise ValueError('Not a PDF')
 if name.endswith('.xlsx') and not r.content.startswith(b'PK'):raise ValueError('Not XLSX')
 path.write_bytes(r.content);row=dict(url=r.url,file=name,sha256=hashlib.sha256(r.content).hexdigest(),retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());receipt.write_text(json.dumps(row,indent=2)+'\n')
 if name.endswith('.pdf'):subprocess.run(['pdftotext','-layout',str(path),str(path.with_suffix('.txt'))],check=True)
 return row
if __name__=='__main__':
 OUT.mkdir(exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(4) as pool:rows=list(pool.map(collect,SOURCES.items()))
 (OUT/'manifest.json').write_text(json.dumps(dict(source='NVE method page current release; date/2025 coverage must be verified before model use',rows=rows,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n');print('Verified four public source files',flush=True)
