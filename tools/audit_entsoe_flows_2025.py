"""Independently replay downloaded 2025 ENTSO-E flow coverage and receipts."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from collect_entsoe_flows_2025 import OUT, PERIOD, plan
from flow_tracing import parse_quantity

START = datetime(2025, 1, 1, tzinfo=timezone.utc)
COUNT = 365 * 24 * 4


def audit(kind):
    journal = OUT / {'physical':'coverage.jsonl',
                     'day-ahead-commercial':'day-ahead-commercial-coverage.jsonl',
                     'day-ahead-capacity':'day-ahead-capacity-coverage.jsonl'}[kind]
    rows = [json.loads(line) for line in journal.read_text().splitlines()]
    border_plan = plan()
    expected = {f'{a}>{b}' for a, b, _, _ in border_plan} | {f'{b}>{a}' for a, b, _, _ in border_plan}
    code = {label: eic for a,b,ca,cb in border_plan
            for label,eic in ((a,ca),(b,cb))}
    assert len(rows) == len(expected) and {r['direction'] for r in rows} == expected
    records = []
    for row in rows:
        source, sink = row['direction'].split('>')
        request = dict(PERIOD, documentType={'physical':'A11',
                       'day-ahead-commercial':'A09','day-ahead-capacity':'A61'}[kind],
                       out_Domain=code[source], in_Domain=code[sink])
        if kind != 'physical':
            request['contract_MarketAgreement.Type'] = 'A01'
        key = hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()[:24]
        path = OUT / 'raw' / (key+'.xml')
        meta = json.loads(path.with_suffix('.json').read_text())
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        assert meta['request'] == request and meta['sha256'] == sha
        if row['status'] == 'ok':
            assert row['sha256'] == sha
            root = ET.fromstring(raw)
            for node in root.iter():node.tag=node.tag.split('}')[-1]
            assert root.findtext('type') == request['documentType']
            series = root.findall('TimeSeries')
            assert all(ts.findtext('businessType') == {'physical':'A66',
                           'day-ahead-commercial':'A06','day-ahead-capacity':'A27'}[kind]
                       for ts in series)
            # A61's contract type is a request filter; the returned capacity
            # TimeSeries often omits that field entirely.
            if kind == 'day-ahead-commercial':
                assert all(ts.findtext('contract_MarketAgreement.type') == 'A01' for ts in series)
            samples = parse_quantity(raw, {'out_Domain.mRID':request['out_Domain'],
                                           'in_Domain.mRID':request['in_Domain']})
            indices = {(stamp-START)//timedelta(minutes=15) for stamp in samples}
            assert len(indices) == len(samples) == row['points']
            assert all(0 <= index < COUNT for index in indices)
            records.append(dict(direction=row['direction'], status='ok', points=len(indices),
                                missing=COUNT-len(indices), sha256=sha))
        else:
            root = ET.fromstring(raw)
            assert root.tag.split('}')[-1] == 'Acknowledgement_MarketDocument'
            records.append(dict(direction=row['direction'], status='unavailable',
                                missing=COUNT, reason=row['reason'], sha256=sha))
    counts=Counter('full' if r['missing']==0 else r['status'] if r['status']!='ok' else 'partial'
                   for r in records)
    result=dict(kind=kind, expected_directions=len(expected), counts=dict(counts),
                model_zone_domain_gaps=['FR-COR','IE-SEM','IT-CALA','XK'],
                coverage=records)
    (OUT / (kind+'-audit.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(kind,dict(counts),flush=True)


if __name__=='__main__':
    import sys
    audit(sys.argv[1])
