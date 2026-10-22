"""Cache public German source evidence for the January scarcity investigation.

No credentials, market fitting or model modifications. Retain upstream bytes,
URLs, retrieval times and digests; forecast archives do not establish auction vintages.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/bidding-zone-network-2025/january-supply-balance-v1'
BASE='https://www.smard.de/app'
START=int(dt.datetime(2025,1,13,tzinfo=dt.timezone.utc).timestamp()*1000)
STOP=int(dt.datetime(2025,1,23,tzinfo=dt.timezone.utc).timestamp()*1000)
SERIES={
    'forecast_solar':125,'forecast_onshore':123,'forecast_offshore':3791,
    'forecast_wind_solar':5097,'forecast_load':411,'forecast_generation':122,
    'actual_solar':4068,'actual_onshore':4067,'actual_offshore':1225,
    'actual_load':410,'actual_gas':4071,'actual_hard_coal':4069,'actual_lignite':1223,
}
CAPACITY={'installed_lignite':4072,'installed_hard_coal':4075,'installed_gas':198,'installed_solar':188,'installed_onshore':186,'installed_offshore':4076}

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def fetch(url):
    folder=OUT/'raw';folder.mkdir(parents=True,exist_ok=True)
    key=hashlib.sha256(url.encode()).hexdigest()[:24];path=folder/(key+'.json');receipt=folder/(key+'.receipt.json')
    if path.exists():
        r=json.loads(receipt.read_text());assert r['url']==url and r['sha256']==digest(path)
        return json.loads(path.read_bytes()),r
    req=urllib.request.Request(url,headers={'User-Agent':'Grid-Conductor-research/alpha'})
    with urllib.request.urlopen(req,timeout=45) as response:
        raw=response.read(8*1024*1024+1);assert len(raw)<=8*1024*1024
        assert response.status==200
    parsed=json.loads(raw);path.write_bytes(raw)
    r=dict(url=url,file=str(path.relative_to(OUT)),sha256=digest(path),retrieved_at=dt.datetime.now(dt.timezone.utc).isoformat(),bytes=len(raw))
    write(receipt,r);return parsed,r

def series(name,code,resolution='hour',capacity=False):
    index,receipt=fetch(f'{BASE}/chart_data/{code}/DE/index_{resolution}.json');times=index['timestamps'];assert times==sorted(set(times))
    # Capacity files cover year blocks. Use the surrounding 2024/25 endpoints;
    # these are annual snapshots, never hourly outage-adjusted availability.
    a=int(dt.datetime(2024,1,1,tzinfo=dt.timezone.utc).timestamp()*1000) if capacity else START
    b=int(dt.datetime(2026,1,1,tzinfo=dt.timezone.utc).timestamp()*1000) if capacity else STOP
    selected=[v for i,v in enumerate(times) if v<b and (i+1==len(times) or times[i+1]>a)]
    receipts=[receipt];samples={};metadata=[]
    for stamp in selected:
        data,r=fetch(f'{BASE}/chart_data/{code}/DE/{code}_DE_{resolution}_{stamp}.json');receipts.append(r);metadata.append(data.get('meta_data'))
        for t,value in data['series']:
            if a<=t<b:
                assert t not in samples or samples[t]==value
                samples[t]=value
    write(OUT/(name+('-quarter' if resolution=='quarterhour' else '')+'.json'),dict(name=name,filter=code,region='DE',resolution=resolution,metadata=metadata,samples=sorted(samples.items()),receipts=receipts))
    print(name,resolution,len(samples),flush=True)
    return name,receipts

def collect():
    OUT.mkdir(parents=True,exist_ok=True);config,rc=fetch(BASE+'/chart_configuration/market_data_configuration.json');write(OUT/'configuration.json',config)
    jobs=[(name,code,'hour',False) for name,code in SERIES.items()]+[(name,code,'year',True) for name,code in CAPACITY.items()]+[('forecast_solar',125,'quarterhour',False),('actual_load',410,'quarterhour',False)]
    completed={};failures={}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(series,*job):job[0]+('-quarter' if job[2]=='quarterhour' else '') for job in jobs}
        for f,name in futures.items():
            try:completed[name]=f.result()[1]
            except Exception as error:failures[name]=type(error).__name__;print(name,'failed',type(error).__name__,flush=True)
    write(OUT/'collection.json',dict(status='public_source_collection_complete',producer_sha256=digest(Path(__file__)),window=['2025-01-13T00:00Z','2025-01-23T00:00Z'],sources=completed,failures=failures,configuration_receipt=rc,limitations=['Public forecast archives may be revised; original pre-auction vintages are not established.','Forecast generation is not installed or verified physically available capacity.','SMARD Germany and model DE-LU/source-country scopes differ.']))
    print('Collection complete; failures:',failures)

if __name__=='__main__':collect()
