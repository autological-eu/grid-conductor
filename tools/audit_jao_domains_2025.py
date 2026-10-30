"""Summarize cached JAO data and compatibility with the accepted zonal LP."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from baselines.compact.evaluation import physical_lp
from baselines.compact.jao import ROOT_DATA, compatibility, read_day
from baselines.compact.source import ROOT


def run(start: date, end: date, output: Path):
    if not date(2025, 1, 1) <= start < end <= date(2026, 1, 1):
        raise ValueError('Require a 2025 UTC date range')
    zones = physical_lp()['zones']
    results = {}
    for region in ('core', 'nordic'):
        hub_counts = Counter()
        null_fields = Counter()
        source_sha = {}
        total = {'days': 0, 'rows': 0, 'distinct_time_steps': 0, 'direct_zone_rows': 0,
                 'rows_requiring_extra_hubs_or_mapping': 0, 'missing_ram_rows': 0,
                 'undefined_ptdf_rows': 0, 'invalid_ptdf_rows': 0,
                 'days_not_24_time_steps': 0, 'days_missing_top_of_hour': 0,
                 'quarter_hour_time_steps': 0}
        for offset in range((end - start).days):
            day = start + timedelta(days=offset)
            rows, receipt = read_day(region, day)
            audit = compatibility(rows, zones)
            for key in total:
                if key in audit:
                    total[key] += audit[key]
            total['days'] += 1
            total['distinct_time_steps'] += receipt['distinct_time_steps']
            total['days_not_24_time_steps'] += receipt['distinct_time_steps'] != 24
            stamps = {row['dateTimeUtc'] for row in rows}
            expected_hours = {f'{day}T{hour:02d}:00:00Z' for hour in range(24)}
            total['days_missing_top_of_hour'] += not expected_hours.issubset(stamps)
            total['quarter_hour_time_steps'] += sum(stamp[14:16] in ('15', '30', '45')
                                                     for stamp in stamps)
            hub_counts.update(audit['unmapped_nonzero_hub_row_counts'])
            for row in rows:
                null_fields.update(key[5:] for key, value in row.items()
                                   if key.startswith('ptdf_') and value is None)
            path = ROOT_DATA / region / f'{day:%Y%m%d}.json.gz'
            source_sha[str(path.relative_to(ROOT))] = receipt['sha256']
        results[region] = total | dict(
            unmapped_nonzero_hub_row_counts=dict(sorted(hub_counts.items())),
            null_ptdf_field_row_counts=dict(sorted(null_fields.items())),
            source_sha256=source_sha)
    summary = {'status': 'JAO_filtered_domain_compatibility_audit_not_applied_to_LP',
               'start_utc': str(start), 'end_utc_exclusive': str(end),
               'accepted_model_zones': zones, 'regions': results,
               'limitations': [
                   'Core presolved and Nordic nonRedundant filters are not complete market domains',
                   'Virtual hubs and nullable PTDF columns are not projected or set to zero',
                   'A JAO PTDF row is not a pairwise NTC or physical line rating',
                   'No accepted physical LP constraint or baseline result is changed']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=date.fromisoformat, required=True)
    parser.add_argument('--end', type=date.fromisoformat, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'research/data/jao-domain-audit-2025.json')
    args = parser.parse_args()
    result = run(args.start, args.end, args.output)
    print(json.dumps({region: {key: value for key, value in data.items()
                               if key not in ('source_sha256', 'unmapped_nonzero_hub_row_counts',
                                              'null_ptdf_field_row_counts')}
                      for region, data in result['regions'].items()}, indent=2))
