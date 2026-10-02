"""Cache public Energy-Charts pilot observations; no API credential required."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def fetch():
 folder=ROOT/'data/pypsa-eur/supply-stack-pilot';folder.mkdir(parents=True,exist_ok=True)
 sources=[('PL-observed.json','public_power?country=pl'),('SE-observed.json','public_power?country=se'),('PL-price.json','price?bzn=PL')]
 def retrieve(item):
  name,query=item;url='https://api.energy-charts.info/'+query+'&start=2025-01-01&end=2025-01-02';path=folder/name
  if not path.exists():
   raw=urllib.request.urlopen(url,timeout=30).read();json.loads(raw);temp=path.with_suffix('.tmp');temp.write_bytes(raw);temp.replace(path)
  return dict(file=name,url=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
 with concurrent.futures.ThreadPoolExecutor(3) as pool:rows=list(pool.map(retrieve,sources))
 (folder/'source-manifest.json').write_text(json.dumps(dict(attribution='Fraunhofer ISE Energy-Charts; see API source/license descriptions',sources=rows),indent=2)+'\n')
 print('Cached three public observation sources')
if __name__=='__main__':fetch()
