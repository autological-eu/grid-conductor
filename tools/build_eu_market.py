"""EU-27 day-ahead market data bank (E1/E2).

Collects the ENTSO-E series the EU model needs into `data/eu-market/`:
clearing prices (A44), generation by type (A75), load (A65), physical flows
(A11) and net transfer capacity (A61) for every modelled border. No
Electricity Maps inputs: A44 prices are the validation reference only.

`collect(month)` is cache-first and reproducible: raw responses land in
`data/eu-market/raw/` (reused via fetch sha256), parsed quarter-hour
samples are merged into `data/eu-market/bank-YYYY-MM.json` positionally
aligned to the month (each entry is a quarter-hour value, None where
missing). Prices, demand and borders use exact bidding-zone domains.
Generation domain exceptions are explicit in zone_domains, never silent aliases.
"""
import argparse
import datetime as dt
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from carbon_pilot import ROOT, timestamp, iso, STORAGE, parse_generation
from flow_tracing import fetch, parse_quantity, parse_day_ahead_prices, charging

DUMP=ROOT/'data/eu-market'

def read_registry():
    eic=json.loads((DUMP/'eic.json').read_text(encoding='utf-8'))
    topo=json.loads((DUMP/'topology.json').read_text(encoding='utf-8'))
    zones=eic['zones']
    externals=eic['exteriors']
    interior=[(e['a'],e['b']) for e in topo['interiors'].values()]
    exterior=[(e['zone'],e['neighbor']) for e in topo['exteriors_exchange']]
    return zones,externals,interior,exterior,topo.get('se_area',{}),topo.get('ie_area',{})

def prefix_candidates(zones,externals,se_area,ie_area,label,mode='price'):
    """Bidding-zone EIC(s) for a label; order matters (first non-empty parse wins).
    mode='gen' prefers the country generation domain (DE 83F) for A75."""
    if label in zones:
        z=zones[label]
        # Different geographic domains are not interchangeable aliases.
        return [z.get('gen') or z['price']] if mode=='gen' else [z['price']]
    if label in externals:
        return [externals[label]['eic']]
    return []

def border_pairs(zones,externals,se_area,ie_area,a,b):
    out=prefix_candidates(zones,externals,se_area,ie_area,a) or [a]
    inn=prefix_candidates(zones,externals,se_area,ie_area,b) or [b]
    pairs=[];seen=set()
    for o in out:
        for i in inn:
            if (o,i) not in seen:
                seen.add((o,i));pairs.append((o,i))
    return pairs

def quarter_index(start,quarters,instant):
    q=int((instant-start).total_seconds()//900)
    if q<0 or q>=quarters:
        return None
    return q

class Bank:
    def __init__(self,start,quarters):
        self.start=start;self.quarters=quarters
        self._rows={}
    def put(self,key,instant,value):
        if instant.tzinfo is None:raise ValueError('Timezone required')
        if (instant-self.start).total_seconds()%900:raise ValueError('Unaligned quarter hour')
        instant=instant.astimezone(dt.timezone.utc)
        q=quarter_index(self.start,self.quarters,instant)
        if q is None:
            return
        row=self._rows.setdefault(key,[None]*self.quarters)
        if value is not None and row[q] is not None and row[q]!=value:
            raise ValueError(f'Conflicting samples for {key} at {iso(instant)}')
        if value is not None:row[q]=value
    def load(self,key):
        return self._rows.get(key)

def collect(month='2026-08',output=DUMP/'bank-2026-08.json'):
    zones,externals,interior,exterior,se_area,ie_area=read_registry()
    year,mnth=[int(x) for x in month.split('-')]
    start=dt.datetime(year,mnth,1,tzinfo=dt.timezone.utc)
    end=(dt.datetime(year+1,1,1,tzinfo=dt.timezone.utc) if mnth==12
         else dt.datetime(year,mnth+1,1,tzinfo=dt.timezone.utc))
    quarters=int((end-start).total_seconds()//900)
    cache=DUMP/'raw';cache.mkdir(parents=True,exist_ok=True)
    period=dict(periodStart=start.strftime('%Y%m%d%H%M'),periodEnd=end.strftime('%Y%m%d%H%M'))
    provenance=[]
    def get(extra):
        import time
        request=dict(period,**extra)
        cache_key=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()[:24]
        if not (cache/(cache_key+'.xml')).exists():time.sleep(0.25)
        raw=fetch(request,cache)
        root=ET.fromstring(raw)
        for node in root.iter():node.tag=node.tag.split('}')[-1]
        if root.findtext('type') != request['documentType']:
            raise ValueError('Unexpected ENTSO-E document type or acknowledgement')
        provenance.append(dict(request={k:v for k,v in request.items() if k not in ('periodStart','periodEnd')},
            period=request['periodStart']+'>'+request['periodEnd'],sha256=hashlib.sha256(raw).hexdigest()))
        return raw
    bank=Bank(start,quarters);errors={}
    zone_labels=sorted(zones)
    # Prices (A44) for every bidding zone and priced exterior.
    for label in zone_labels+[x for x in sorted(externals)]:
        ok=False
        err='no candidate eic'
        for eic in prefix_candidates(zones,externals,se_area,ie_area,label):
            try:
                raw=get(dict(documentType='A44',processType='A01',in_Domain=eic,out_Domain=eic))
                for instant,value in parse_day_ahead_prices(raw).items():
                    if value is not None:bank.put(('price',label),instant,value)
                ok=True
                break
            except ValueError as error:
                err=str(error)
        if not ok:
            errors['price_'+label]=err
    # Query generation and demand independently with their explicit domains.
    for label in zone_labels:
        eic=zones[label].get('gen') or zones[label]['price']
        try:
            raw=get(dict(documentType='A75',processType='A16',in_Domain=eic))
            for kind,samples in parse_generation(raw,eic).items():
                for instant,value in samples.items():bank.put(('gen',label,kind),instant,value)
            for kind,samples in charging(raw,eic).items():
                for instant,value in samples.items():bank.put(('charge',label,kind),instant,value)
        except ValueError as error:errors['gen_'+label]=str(error)
        eic=zones[label]['price']
        try:
            raw=get(dict(documentType='A65',processType='A16',outBiddingZone_Domain=eic))
            for instant,value in parse_quantity(raw,{'outBiddingZone_Domain.mRID':eic}).items():
                bank.put(('load',label),instant,value)
        except ValueError as error:errors['load_'+label]=str(error)
    # Flows (A11) and caps (A61) in BOTH directions for every border, probed separately.
    borders=sorted({tuple(sorted(p)) for p in interior+exterior})
    for a,b in borders:
        if not (a in zones or a in externals) or not (b in zones or b in externals):
            continue
        for direction in [(a,b),(b,a)]:
            for probe,kind,extra in [('flow',('flow',direction),dict(documentType='A11')),
                                     ('cap',('cap',direction),dict(documentType='A61',**{'contract_MarketAgreement.Type':'A01'}))]:
                ok=False;failure='No returned observations'
                for o,i in border_pairs(zones,externals,se_area,ie_area,*direction):
                    try:
                        raw=get(dict(extra,out_Domain=o,in_Domain=i))
                        for instant,value in parse_quantity(raw,{'out_Domain.mRID':o,'in_Domain.mRID':i}).items():
                            if value is not None:bank.put(kind,instant,value)
                        ok=True
                        break
                    except ValueError as error:
                        failure=str(error)
                        continue
                if not ok:
                    errors['border_'+probe+'_'+direction[0]+'>'+direction[1]]=failure
    directions=sorted({direction for a,b in borders for direction in [(a,b),(b,a)]})
    flows_mw={f'{a}>{b}':bank.load(('flow',(a,b))) for a,b in directions if bank.load(('flow',(a,b))) is not None}
    caps_mw={f'{a}>{b}':bank.load(('cap',(a,b))) for a,b in directions if bank.load(('cap',(a,b))) is not None}
    caps_synthetic=[]
    bank_json=dict(schema_version=2,zone_domains=zones,month=month,period=period,zones=zone_labels,
        exteriors=sorted(externals),
        interior_borders=[sorted(p) for p in sorted(interior)],
        exterior_borders=[sorted(p) for p in sorted(exterior)],
        prices={label:bank.load(('price',label)) for label in zone_labels+[x for x in sorted(externals)] if bank.load(('price',label))},
        load_mw={label:bank.load(('load',label)) for label in zone_labels if bank.load(('load',label))},
        generation_mw={label:{kind:bank.load(('gen',label,kind)) for kind in sorted({k[2] for k in bank._rows if k[0]=='gen' and k[1]==label})} for label in zone_labels},
        storage_charge_mw={label:{kind:bank.load(('charge',label,kind)) for kind in sorted({k[2] for k in bank._rows if k[0]=='charge' and k[1]==label})} for label in zone_labels},
        flows_mw=flows_mw,
        caps_mw=caps_mw,
        caps_synthetic=sorted(caps_synthetic),
        errors=errors,
        provenance=dict(request_count=len(provenance),requests=provenance,
            note='ENTSO-E API only. Directed A11 physical flows and A61 day-ahead estimated NTC. '
                 'Missing is unknown; no mirrored capacities or flow-derived limits. '
                 'A61 is not a complete flow-based market coupling constraint set.'))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(bank_json,allow_nan=False),encoding='utf-8')
    def uncovered(prefix):
        return [f'{a}>{b}' for (a,b) in directions if not bank.load((prefix,(a,b)))]
    missing=uncovered('flow')+sorted({f'{a}>{b}' for (a,b) in borders if bank.load(('flow',(a,b))) and f'{a}>{b}' not in caps_mw})
    caps_total=len(caps_mw)
    flows=len(flows_mw)
    gen_zones=[]
    for label in zone_labels:
        kinds={kk[2] for kk in bank._rows if kk[0]=='gen' and kk[1]==label}
        if any(any(v is not None for v in (bank.load(('gen',label,k)) or [])) for k in kinds):
            gen_zones.append(label)
    print(json.dumps(dict(output=str(output),
        prices=sum(bool(bank.load(('price',l))) for l in zone_labels+list(externals)),
        generation_zones=gen_zones,
        flows=flows,caps=caps_total,
        caps_real=len([k for k in caps_mw if k not in set(caps_synthetic)]),
        caps_synthetic_count=len(caps_synthetic),
        missing_flow_cap=missing[:20],errors=len(errors)),indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--month',default='2026-08')
    p.add_argument('--months',nargs='+',help='collect several YYYY-MM months (overrides --month)')
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    months=args.months if args.months else [args.month]
    for m in months:
        out=args.output
        if not out:
            out=DUMP/f'bank-{m}.json'
        collect(m,out)

if __name__=='__main__':main()
