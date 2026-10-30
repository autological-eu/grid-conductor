"""Map source-hashed JAO CNEC endpoints to model border pairs, without NTC claims."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date, timedelta

from baselines.compact.jao import read_day
from baselines.compact.network import transport_corridors
from baselines.compact.source import ROOT, digest, grouped_fit_inputs

OUT = ROOT / 'research/data/jao-edge-cnec-evidence-2025.csv'
SUMMARY = ROOT / 'research/data/jao-edge-cnec-evidence-2025.json'


def audit():
    schema, data, _ = grouped_fit_inputs()
    zones = schema['zones']
    edges, _, _ = transport_corridors(zones, data)
    pairs = {frozenset((zones[i], zones[j])): (zones[i], zones[j]) for i, j in edges}
    evidence = defaultdict(lambda: dict(rows=0, stamps=set(), names=set(),
                                         types=Counter(), fmax_by_type=defaultdict(list)))
    receipt_sha = {}
    for region in ('core', 'nordic'):
        for offset in range(365):
            day = date(2025, 1, 1) + timedelta(days=offset)
            rows, receipt = read_day(region, day)
            receipt_sha[f'{region}/{day}'] = receipt['sha256']
            for row in rows:
                a = row.get('hubFrom') if region == 'core' else row.get('biddingZoneFrom')
                b = row.get('hubTo') if region == 'core' else row.get('biddingZoneTo')
                key = frozenset((a, b))
                if a == b or key not in pairs:
                    continue
                item = evidence[region, pairs[key]]
                item['rows'] += 1
                item['stamps'].add(row['dateTimeUtc'])
                item['names'].add(str(row.get('cneEic') or row.get('cneName') or
                                      row.get('cnecName')))
                kind = str(row.get('elementType') or row.get('cneType'))
                item['types'][kind] += 1
                fmax = row.get('fmax')
                if isinstance(fmax, (int, float)) and fmax > 0:
                    item['fmax_by_type'][kind].append(float(fmax))
    output = []
    for pair in pairs.values():
        for region in ('core', 'nordic'):
            item = evidence[region, pair]
            cne_fmax = (item['fmax_by_type'].get('CNE', []) +
                        item['fmax_by_type'].get('TieLine', []))
            ptc_fmax = item['fmax_by_type'].get('PTC', [])
            output.append(dict(from_zone=pair[0], to_zone=pair[1], region=region,
                matching_cnec_rows=item['rows'], published_time_steps=len(item['stamps']),
                distinct_cnec_ids=len(item['names']),
                element_types='|'.join(f'{k}:{v}' for k, v in sorted(item['types'].items())),
                minimum_cne_fmax_mw=(min(cne_fmax) if cne_fmax else ''),
                maximum_cne_fmax_mw=(max(cne_fmax) if cne_fmax else ''),
                minimum_ptc_fmax_mw=(min(ptc_fmax) if ptc_fmax else ''),
                maximum_ptc_fmax_mw=(max(ptc_fmax) if ptc_fmax else ''),
                interpretation='JAO endpoint-matched constrained elements, not border transfer capacity'))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(output[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(output)
    summary = dict(status='JAO_CNEC_endpoint_crosswalk_not_pairwise_capacity',
                   model_edges=len(pairs), regions=['core', 'nordic'],
                   edges_with_endpoint_matched_cnecs={region: sum(
                       evidence[region, pair]['rows'] > 0 for pair in pairs.values())
                       for region in ('core', 'nordic')},
                   source_daily_sha256=receipt_sha, csv_sha256=digest(OUT),
                   limitations=['Filtered presolved/nonredundant rows do not form a complete market domain',
                                'CNEC endpoint pair and fmax are not a pairwise market transfer rating',
                                'Virtual hubs, null PTDF fields and allocation constraints remain unmapped',
                                'Nordic quarter-hour steps are retained as published',
                                'No LP or transport corridor bound was changed from JAO CNEC fmax'])
    SUMMARY.write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    result = audit()
    print(json.dumps({k: result[k] for k in ('model_edges',
        'edges_with_endpoint_matched_cnecs')}, indent=2))
