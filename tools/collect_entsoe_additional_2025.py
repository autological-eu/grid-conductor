"""Resumable source-only 2025 ENTSO-E annual input collection.

No observed generation is substituted for availability and no model is changed.
Raw responses and request receipts stay in Git-ignored data/eu-market.
"""
import hashlib
import json
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from eu_zones import ZONES, EXTERIORS
from flow_tracing import ROOT, fetch

OUT = ROOT / 'data/eu-market/additional-2025'
NETWORK = ROOT / 'data/bidding-zone-network-2025/hour-table-learning-rates-v1/lr-0.5/network.json'
PERIOD = dict(periodStart='202501010000', periodEnd='202601010000')
PRODUCTS = {
    'day_ahead_renewable_forecast': dict(documentType='A69', processType='A01', domain='in_Domain'),
    'day_ahead_load_forecast': dict(documentType='A65', processType='A01', domain='outBiddingZone_Domain'),
    'year_ahead_unit_capacity': dict(documentType='A71', processType='A33', domain='in_Domain'),
    'reservoir_filling': dict(documentType='A72', domain='in_Domain'),
}


def plan():
    zones = json.loads(NETWORK.read_text())['zones']
    codes = {z: eic for z, eic, *_ in ZONES}
    codes.update({z: eic for z, eic, *_ in EXTERIORS})
    return [(zone, product, dict(PERIOD, **{k:v for k,v in spec.items() if k!='domain'},
                                **{spec['domain']:codes[zone]}))
            for zone in zones if zone in codes for product,spec in PRODUCTS.items()]


def collect(item):
    zone, product, request = item
    raw = fetch(request, OUT / 'raw')
    root = ET.fromstring(raw)
    tag = root.tag.split('}')[-1]
    if tag == 'Acknowledgement_MarketDocument':
        reasons = [(e.tag.split('}')[-1],e.text) for e in root.iter()
                   if e.tag.split('}')[-1] in ('code','text')]
        return dict(zone=zone,product=product,status='no_data',reason=reasons[:3],
                    sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    if tag != 'GL_MarketDocument':
        raise ValueError(f'Unexpected {product} document root: {tag}')
    doc_type = next((e.text for e in root if e.tag.split('}')[-1]=='type'),None)
    if doc_type != request['documentType']:
        raise ValueError(f'Unexpected {product} document type: {doc_type}')
    series = sum(e.tag.split('}')[-1]=='TimeSeries' for e in root)
    return dict(zone=zone,product=product,status='ok',series=series,
                sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    journal = OUT / 'annual-input-coverage.jsonl'
    old = [json.loads(line) for line in journal.read_text().splitlines()] if journal.exists() else []
    done = {(row['zone'],row['product']) for row in old if row['status'] in ('ok','no_data')}
    todo = [item for item in plan() if item[:2] not in done]
    print(f'{len(todo)} remaining of {len(plan())} annual requests',flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(collect,item):item for item in todo}
        for future in as_completed(futures):
            zone,product,_ = futures[future]
            try:row = future.result()
            except Exception as error:
                row = dict(zone=zone,product=product,status='error',reason=str(error)[:180])
            with journal.open('a') as output:output.write(json.dumps(row,sort_keys=True)+'\n')
            print(zone,product,row['status'],row.get('series',''),flush=True)


if __name__=='__main__':main()
