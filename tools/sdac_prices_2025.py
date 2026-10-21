"""Fresh auction-aware A44 targets. Frozen research parsers/targets stay intact."""
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/price-trace/sdac-hourly-2025-v1'
START=dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)
END=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)
POLICY={'DE-LU':1,'AT':1}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stamp(v):return dt.datetime.fromisoformat(v.replace('Z','+00:00'))
def clean(raw):
    root=ET.fromstring(raw)
    for e in root.iter():e.tag=e.tag.split('}')[-1]
    if root.tag!='Publication_MarketDocument' or root.findtext('type')!='A44':raise ValueError('Expected A44 price document')
    return root

def selected(ts,zone):
    if ts.findtext('contract_MarketAgreement.type')!='A01':return False
    seq=ts.findtext('classificationSequence_AttributeInstanceComponent.position')
    if zone in POLICY:return seq==str(POLICY[zone])
    if seq is not None:raise ValueError('Unverified classified day-ahead auction: '+zone)
    return True

def parse(raw,zone,eic):
    root=clean(raw);samples={}
    for ts in root.findall('TimeSeries'):
        if not selected(ts,zone):continue
        if ts.findtext('currency_Unit.name')!='EUR' or ts.findtext('price_Measure_Unit.name')!='MWH':raise ValueError('Expected EUR/MWh')
        if any(ts.findtext(k)!=eic for k in ['in_Domain.mRID','out_Domain.mRID']):raise ValueError('Wrong bidding zone')
        curve=ts.findtext('curveType')
        if curve not in ['A01','A03']:raise ValueError('Unknown curve')
        for period in ts.findall('Period'):
            a=stamp(period.findtext('timeInterval/start'));b=stamp(period.findtext('timeInterval/end'))
            minutes={'PT15M':15,'PT30M':30,'PT60M':60}.get(period.findtext('resolution'))
            if not minutes or b<=a or a.minute%15 or a.second or a.microsecond:raise ValueError('Misaligned period')
            slots=(b-a).total_seconds()/(minutes*60)
            if not slots.is_integer():raise ValueError('Misaligned end')
            points={}
            for p in period.findall('Point'):
                pos=int(p.findtext('position'));v=p.findtext('price.amount');v=None if v is None else float(v)
                if pos in points or not 1<=pos<=slots or v is not None and not math.isfinite(v):raise ValueError('Invalid point')
                points[pos]=v
            last=None
            for pos in range(1,int(slots)+1):
                if pos in points:last=points[pos]
                v=last if curve=='A03' else points.get(pos)
                for q in range(minutes//15):
                    t=a+dt.timedelta(minutes=(pos-1)*minutes+q*15)
                    if t in samples and samples[t]!=v:raise ValueError('Conflicting selected auction observations')
                    samples[t]=v
    return samples

def run():
    OUT.mkdir(parents=True,exist_ok=False)
    legacy=ROOT/'data/price-trace/dispatch-validation-2025-v2/manifest.json';manifest=json.loads(legacy.read_text())
    model=json.loads((ROOT/'data/bidding-zone-network-2025/oil-chp-bids-v2/summary.json').read_text());zones=model['zones']
    matrix=np.full((8760,len(zones)),np.nan);sources={str(legacy.relative_to(ROOT)):sha(legacy)};records=[]
    for zone,meta in manifest['zones'].items():
        name='IE-SEM' if zone=='IE' else zone
        if name not in zones:continue
        quarters={};receipts=[]
        for receipt in meta.get('receipts',[]):
            req=receipt['request'];key=hashlib.sha256(json.dumps(req,sort_keys=True).encode()).hexdigest()[:24]
            path=ROOT/f'data/price-trace/entsoe/{zone}/{key}.xml'
            assert sha(path)==receipt['sha256']
            sources[str(path.relative_to(ROOT))]=sha(path)
            parsed=parse(path.read_bytes(),zone,req['in_Domain'])
            a=dt.datetime.strptime(req['periodStart'],'%Y%m%d%H%M').replace(tzinfo=dt.timezone.utc);b=dt.datetime.strptime(req['periodEnd'],'%Y%m%d%H%M').replace(tzinfo=dt.timezone.utc)
            for t,v in parsed.items():
                if max(START,a)<=t<min(END,b):
                    if t in quarters and quarters[t]!=v:raise ValueError('Request-boundary conflict')
                    quarters[t]=v
            receipts.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path),request=req))
        for h in range(8760):
            values=[quarters.get(START+dt.timedelta(minutes=h*60+q*15)) for q in range(4)]
            if all(v is not None for v in values):matrix[h,zones.index(name)]=sum(values)/4
        records.append(dict(zone=name,source_zone=zone,auction='sequence 1 (SDAC)' if zone in POLICY else 'sole unclassified A01 day-ahead',known_hours=int(np.isfinite(matrix[:,zones.index(name)]).sum()),receipts=receipts))
    np.savez_compressed(OUT/'prices.npz',prices=matrix)
    result=dict(schema_version=1,status='auction_aware_hourly_targets',zones=zones,hours=8760,start_utc=START.isoformat(),producer_file=Path(__file__).name,producer_sha256=sha(__file__),policy=POLICY,source_hashes=sources,areas=records,prices_sha256=sha(OUT/'prices.npz'),limitations=['Main ENTSO-E day-ahead A01 series; SDAC where applicable. Non-coupled areas are not claimed as SDAC.', 'DE-LU/AT sequence 1 only; no fallback to sequence 2. Other markets require an unclassified A01 series. A07 intraday excluded.', 'All four published quarter-hour samples required per UTC hour; A03 published blocks expanded, A01 missing points remain missing.'])
    (OUT/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Corrected targets',np.isfinite(matrix).sum(axis=0).tolist(),flush=True)

if __name__=='__main__':run()
