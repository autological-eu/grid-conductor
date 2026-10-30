"""Read source-verified JAO domains without dropping virtual hubs.

The current physical LP has bidding-zone net-position variables but no explicit
JAO virtual-hub variables or certified mapping. JAO rows are therefore exposed
for compatibility auditing, not silently inserted as pairwise border caps.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from datetime import date

import numpy as np
from scipy.sparse import csr_matrix

from .source import ROOT

ROOT_DATA = ROOT / 'data/jao/full-2025-v1'


def read_day(region: str, day: date):
    if region not in {'core', 'nordic'}:
        raise ValueError(f'Unknown JAO region: {region}')
    name = f'{day:%Y%m%d}'
    path = ROOT_DATA / region / f'{name}.json.gz'
    receipt_path = ROOT_DATA / region / f'{name}.meta.json'
    receipt = json.loads(receipt_path.read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != receipt['sha256']:
        raise ValueError(f'JAO daily witness hash mismatch: {region}/{day}')
    with gzip.open(path, 'rt', encoding='utf-8') as file:
        data = json.load(file)
    if data['region'] != region or data['date'] != str(day) or len(data['rows']) != receipt['total_rows']:
        raise ValueError(f'JAO daily metadata mismatch: {region}/{day}')
    if data['filter'] != receipt['filter'] or receipt['market_domain_complete']:
        raise ValueError('JAO filter/completeness classification changed')
    flag = 'presolved' if region == 'core' else 'nonRedundant'
    if any(row.get(flag) is not True for row in data['rows']):
        raise ValueError(f'JAO returned a row outside requested {flag} filter')
    stamps = {row['dateTimeUtc'] for row in data['rows']}
    if len(stamps) != receipt['distinct_time_steps']:
        raise ValueError('JAO time-step coverage changed')
    return data['rows'], receipt


def compatibility(rows, zones):
    """Count exact compatible columns; preserve every nonzero JAO PTDF name."""
    zones = set(zones)
    missing = Counter()
    direct = 0
    missing_ram = 0
    undefined_ptdf = 0
    invalid_ptdf = 0
    for row in rows:
        ram = row.get('ram')
        if ram is None or not np.isfinite(ram):
            missing_ram += 1
        raw_keys = [(key[5:], value) for key, value in row.items() if key.startswith('ptdf_')]
        if not raw_keys or any(value is not None and not np.isfinite(value)
                               for _, value in raw_keys):
            invalid_ptdf += 1
            continue
        if any(value is None for _, value in raw_keys):
            undefined_ptdf += 1
        keys = [(name, float(value)) for name, value in raw_keys if value is not None]
        outside = {name for name, value in keys if value != 0 and name not in zones}
        missing.update(outside)
        if not outside and not any(value is None for _, value in raw_keys) and ram is not None and np.isfinite(ram):
            direct += 1
    return {'rows': len(rows), 'direct_zone_rows': direct,
            'rows_requiring_extra_hubs_or_mapping': len(rows) - direct,
            'missing_ram_rows': missing_ram, 'undefined_ptdf_rows': undefined_ptdf,
            'invalid_ptdf_rows': invalid_ptdf,
            'unmapped_nonzero_hub_row_counts': dict(sorted(missing.items()))}


def time_step_domain(rows, timestamp, *, skip_incomplete=False):
    """Return a named-hub PTDF matrix, with no lossy projection onto model zones.

    It is a source-domain data object. The accepted LP does not yet have all
    these market-hub variables, so this matrix must not be added to that LP.
    """
    selected = [row for row in rows if row['dateTimeUtc'] == timestamp]
    if not selected:
        raise ValueError(f'No JAO rows for {timestamp}')
    rejected = []
    complete = []
    for row in selected:
        fields = [value for key, value in row.items() if key.startswith('ptdf_')]
        if row.get('ram') is None or not np.isfinite(row['ram']) or not fields or any(
                value is None or not np.isfinite(value) for value in fields):
            rejected.append(str(row['id']))
        else:
            complete.append(row)
    if rejected and not skip_incomplete:
        raise ValueError(f'{len(rejected)} JAO rows have missing RAM/PTDF at {timestamp}')
    selected = complete
    names = sorted({key[5:] for row in selected for key in row if key.startswith('ptdf_')})
    ids = {name: j for j, name in enumerate(names)}
    row_id, column_id, coefficient, ram, source_id = [], [], [], [], []
    for i, row in enumerate(selected):
        value = row.get('ram')
        if value is None or not np.isfinite(value):
            raise ValueError(f'Missing JAO RAM at {timestamp}')
        ram.append(float(value))
        source_id.append(str(row['id']))
        for key, raw in row.items():
            if not key.startswith('ptdf_'):
                continue
            if raw is None or not np.isfinite(raw):
                raise ValueError(f'Invalid JAO PTDF: {key}/{timestamp}')
            if raw != 0:
                row_id.append(i)
                column_id.append(ids[key[5:]])
                coefficient.append(float(raw))
    matrix = csr_matrix((coefficient, (row_id, column_id)),
                        shape=(len(selected), len(names)))
    if len(set(source_id)) != len(source_id):
        raise ValueError(f'Duplicate JAO CNEC IDs at {timestamp}')
    return {'timestamp': timestamp, 'hub_names': names, 'ptdf': matrix,
            'ram_mw': np.array(ram), 'source_id': source_id,
            'rejected_incomplete_source_id': rejected}


def exact_zone_rows(rows, timestamp, zones):
    """Extract only source rows with defined PTDFs and no unmapped nonzero hub.

    These are structurally expressible with zone net-position variables, but
    their market reference and combination with the physical LP are unvalidated.
    """
    zone_index = {name: j for j, name in enumerate(zones)}
    selected = []
    for row in rows:
        if row['dateTimeUtc'] != timestamp:
            continue
        fields = [(key[5:], value) for key, value in row.items() if key.startswith('ptdf_')]
        if row.get('ram') is None or not np.isfinite(row['ram']) or not fields:
            continue
        if any(value is None or not np.isfinite(value) or
               (value != 0 and name not in zone_index) for name, value in fields):
            continue
        selected.append(row)
    row_id, column_id, coefficient = [], [], []
    for i, row in enumerate(selected):
        for name, value in [(key[5:], value) for key, value in row.items()
                            if key.startswith('ptdf_')]:
            if value != 0:
                row_id.append(i)
                column_id.append(zone_index[name])
                coefficient.append(float(value))
    matrix = csr_matrix((coefficient, (row_id, column_id)),
                        shape=(len(selected), len(zones)))
    return (matrix, np.array([float(row['ram']) for row in selected]),
            [str(row['id']) for row in selected])
