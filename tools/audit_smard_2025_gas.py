"""Bounded SMARD German hourly gas-generation reference, not validation.

SMARD filter 4071 is reported feed-in energy (MWh per interval), not gas
capacity or original renewable availability. Preserve missing observations.
"""
import argparse
import fcntl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import urllib.request

from monthly_dispatch import digest, save

BASE = 'https://www.smard.de/app/chart_data/4071/DE/'
START = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp()*1000)
END = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()*1000)
HOUR = 3600000


def aggregate(series):
    values = {}
    for timestamp, value in series:
        if type(timestamp) is not int or timestamp % HOUR:
            raise ValueError('Exact UTC hour labels required')
        if not START <= timestamp < END:
            continue
        if timestamp in values:
            raise ValueError('Duplicate source interval; review overlapping chunks')
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
            raise ValueError('Invalid reported gas-generation energy')
        values[timestamp] = value
    hourly = [values.get(timestamp) for timestamp in range(START, END, HOUR)]
    months = []
    for month in range(1, 13):
        rows = [value for index, value in enumerate(hourly)
                if datetime.fromtimestamp((START+index*HOUR)/1000, timezone.utc).month == month]
        observed = [value for value in rows if value is not None]
        months.append(dict(month=month, expected_hours=len(rows), observed_hours=len(observed),
                           complete_reported_energy_mwh=math.fsum(observed) if len(observed) == len(rows) else None))
    observed = [value for value in hourly if value is not None]
    return dict(expected_hours=8760, observed_hours=len(observed),
                complete_reported_energy_mwh=math.fsum(observed) if len(observed) == 8760 else None,
                monthly=months)


def cached(cache, filename, download):
    path = cache/filename
    receipt = path.with_suffix(path.suffix+'.receipt.json')
    url = BASE+filename
    if not path.exists():
        if not download or receipt.exists():
            raise ValueError('Missing original cache; explicit download or receipt review required')
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read(2*2**20+1)
        if len(data) > 2*2**20:
            raise ValueError('Source chunk exceeds bounded size')
        json.loads(data)
        path.write_bytes(data)
        save(receipt, dict(source_url=url, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)))
    record = json.loads(receipt.read_text())
    if record['source_url'] != url or record['sha256'] != digest(path) or record['bytes'] != path.stat().st_size:
        raise ValueError('Original SMARD chunk receipt does not reproduce')
    return json.loads(path.read_text()), record


def audit(cache, download=False):
    cache.mkdir(parents=True, exist_ok=True)
    with (cache/'collection.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return audit_locked(cache, download)


def audit_locked(cache, download=False):
    cache.mkdir(parents=True, exist_ok=True)
    index, index_receipt = cached(cache, 'index_hour.json', download)
    starts = index['timestamps']
    if starts != sorted(set(starts)) or any(type(t) is not int for t in starts):
        raise ValueError('Ordered unique source chunk index required')
    selected = [timestamp for i, timestamp in enumerate(starts)
                if timestamp < END and (i == len(starts)-1 or starts[i+1] > START)]
    if not 1 <= len(selected) <= 60:
        raise ValueError('Bounded annual source chunks required')
    with ThreadPoolExecutor(max_workers=2) as pool:
        chunks = list(pool.map(lambda t: cached(cache, f'4071_DE_hour_{t}.json', download), selected))
    report = aggregate([row for data, _ in chunks for row in data['series']])
    report.update(status='smard_utc_gas_generation_reference_not_validation', year=2025,
                  source='Bundesnetzagentur SMARD', source_filter=4071, source_region='DE', unit='MWh per hourly interval',
                  time_scope='2025-01-01T00:00:00Z to 2026-01-01T00:00:00Z, end exclusive',
                  index_receipt=index_receipt, chunk_receipts=[receipt for _, receipt in chunks],
                  producer_sha256=digest(Path(__file__)), dependencies={'monthly_dispatch.py': digest(Path(__file__).parent/'monthly_dispatch.py')},
                  limitations=['Reported feed-in, not whole-fleet gross generation or capacity.',
                               'German territorial, ENTSO-E proxy and native mainland scopes require reconciliation.',
                               'Units follow documented SMARD filter 4071; UTC source-label interpretation requires further provider-method audit.',
                               'Sources may share underlying TSO measurements; agreement is not independent measurement.',
                               'No model-cost change, availability substitution, lifecycle intensity or empirical acceptance inferred.'])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve previous reference evidence')
    result = audit(args.cache, args.download)
    save(args.output, result)
    print(f"Audited {result['observed_hours']}/8760 reported gas-generation hours; no validation inferred.")
