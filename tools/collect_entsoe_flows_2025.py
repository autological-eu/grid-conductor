"""Download 2025 A11 directional series for the reviewed border registry.

Raw XML and request receipts stay under Git-ignored data/eu-market. A11 is
collected as published; its market/physical meaning is not assumed here.
"""
import hashlib
import argparse
import json
import time
from pathlib import Path

from eu_zones import ZONES, EXTERIORS, INTERNAL_BORDERS, EXTERIOR_BORDERS
from flow_tracing import ROOT, fetch, parse_quantity

OUT = ROOT / 'data/eu-market/flow-refresh-2025'
PERIOD = dict(periodStart='202501010000', periodEnd='202601010000')
NETWORK = ROOT / 'data/bidding-zone-network-2025/hour-table-learning-rates-v1/lr-0.5/network.json'


def plan():
    codes = {label: eic for label, eic, *_ in ZONES}
    codes.update({label: eic for label, eic, *_ in EXTERIORS})
    network = json.loads(NETWORK.read_text())
    if network['corridors'] != 95 or len(network['zones']) != 48:
        raise ValueError('Unexpected native network topology')
    native = {tuple(sorted((row['zone0'], row['zone1'])))
              for row in network['cross_zone_components']}
    if len(native) != 95:
        raise ValueError('Unexpected native corridor pairs')
    unresolved = sorted((a,b) for a,b in native if a not in codes or b not in codes)
    (OUT / 'unmapped-model-corridors.json').write_text(
        json.dumps(unresolved, indent=2)+'\n')
    pairs = sorted({tuple(sorted(pair)) for pair in
        INTERNAL_BORDERS + EXTERIOR_BORDERS} | native)
    pairs = [(a,b) for a,b in pairs if a in codes and b in codes]
    return [(a, b, codes[a], codes[b]) for a, b in pairs]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('physical', 'day-ahead-commercial',
                                           'day-ahead-capacity'),
                        default='physical')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    journal = OUT / {'physical':'coverage.jsonl',
                     'day-ahead-commercial':'day-ahead-commercial-coverage.jsonl',
                     'day-ahead-capacity':'day-ahead-capacity-coverage.jsonl'}[args.kind]
    done = {}
    if journal.exists():
        for line in journal.read_text().splitlines():
            item = json.loads(line)
            done[item['direction']] = item
    border_plan = plan()
    print(f'Planned {len(border_plan)} borders / {2*len(border_plan)} directions', flush=True)
    for a, b, ca, cb in border_plan:
        for source, sink, out_code, in_code in ((a, b, ca, cb), (b, a, cb, ca)):
            direction = source + '>' + sink
            if direction in done:
                continue
            params = dict(PERIOD, documentType={'physical':'A11',
                          'day-ahead-commercial':'A09','day-ahead-capacity':'A61'}[args.kind],
                          out_Domain=out_code, in_Domain=in_code)
            if args.kind != 'physical':
                params['contract_MarketAgreement.Type'] = 'A01'
            started = time.monotonic()
            try:
                raw = fetch(params, OUT / 'raw')
                samples = parse_quantity(raw, {'out_Domain.mRID':out_code,
                                               'in_Domain.mRID':in_code})
                item = dict(direction=direction, status='ok', points=len(samples),
                            first=min(samples).isoformat() if samples else None,
                            last=max(samples).isoformat() if samples else None,
                            sha256=hashlib.sha256(raw).hexdigest(),
                            seconds=round(time.monotonic()-started, 2))
            except (ValueError, OSError, TimeoutError) as exc:
                item = dict(direction=direction, status='unavailable',
                            reason=str(exc)[:180], seconds=round(time.monotonic()-started, 2))
            with journal.open('a') as output:
                output.write(json.dumps(item, sort_keys=True)+'\n')
            print(direction, item['status'], item.get('points', ''), flush=True)
            time.sleep(.2)
    print('Collection pass complete', flush=True)


if __name__ == '__main__':
    main()
