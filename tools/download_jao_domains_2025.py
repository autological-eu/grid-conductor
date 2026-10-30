"""Checkpoint public JAO Core/Nordic finalComputation rows for 2025 UTC days.

The returned filtered rows are incomplete market-domain evidence. This tool
downloads data; it does not convert JAO rows into pairwise border capacity.
"""
from __future__ import annotations

import argparse
import fcntl
import gzip
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/jao/full-2025-v1'
PROBE = ROOT / 'data/jao/probe-2025-v1'
FILTER = {
    'core': {'presolved': True, 'cnecName': '', 'tso': [], 'hubFrom': [],
             'hubTo': [], 'contingency': ''},
    'nordic': {'nonRedundant': True, 'cnecName': '', 'tso': [],
               'biddingZoneFrom': [], 'biddingZoneTo': [], 'contingency': ''},
}
PAGE_SIZE = 20000  # JAO accepts a complete 96-step Nordic day in one page.


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url, tries=4):
    request = urllib.request.Request(url, headers={
        'Accept': 'application/json', 'User-Agent': 'GridConductorResearch/1.0'})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                if response.status != 200:
                    raise RuntimeError(f'JAO HTTP {response.status}')
                body = response.read()
            return json.loads(body), hashlib.sha256(body).hexdigest()
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == tries - 1:
                raise
            time.sleep(min(2 ** attempt, 8))


def day_url(region, day, skip, take=PAGE_SIZE):
    start = f'{day}T00:00:00Z'
    end = f'{day + timedelta(days=1)}T00:00:00Z'
    query = urllib.parse.urlencode(dict(FromUtc=start, ToUtc=end, skip=skip,
                                        take=take, filter=json.dumps(FILTER[region],
                                                                     separators=(',', ':'))))
    return f'https://publicationtool.jao.eu/{region}/api/data/finalComputation?{query}'


def one_day(region, day):
    folder = OUT / region
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{day:%Y%m%d}.json.gz'
    receipt_path = folder / f'{day:%Y%m%d}.meta.json'
    if path.exists() and receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt['sha256'] != sha(path):
            raise ValueError(f'Changed saved JAO day {region}/{day}')
        return receipt, True
    if path.exists() or receipt_path.exists():
        raise ValueError(f'Partial JAO checkpoint {region}/{day}; inspect before retry')
    records, pages = [], []
    skip = 0
    total = None
    modified = None
    while total is None or skip < total:
        url = day_url(region, day, skip)
        response, body_hash = fetch(url)
        if response.get('rejected') or response.get('messages'):
            raise RuntimeError(f'JAO rejected {region}/{day}: {response.get("messages")}')
        current_total = response['totalRowsWithFilter']
        if total is None:
            total = current_total
        if current_total != total:
            raise RuntimeError(f'JAO page count changed during {region}/{day}')
        page_modified = response.get('lastModifiedOn')
        if page_modified is not None:
            modified = max(modified or page_modified, page_modified)
        if response['skip'] != skip or response['take'] != PAGE_SIZE:
            raise RuntimeError('JAO pagination mismatch')
        rows = response['data']
        if len(rows) != min(PAGE_SIZE, total - skip):
            raise RuntimeError(f'JAO page length mismatch: {region}/{day}/{skip}')
        if not rows and total:
            raise RuntimeError('Empty JAO page before total')
        records.extend(rows)
        pages.append({'url': url, 'body_sha256': body_hash, 'rows': len(rows),
                      'last_modified_on': page_modified})
        skip += len(rows)
        if total == 0:
            break
    if len(records) != total:
        raise RuntimeError('JAO total count changed')
    identity = [(row['id'], row['dateTimeUtc']) for row in records]
    if len(set(identity)) != len(identity):
        raise RuntimeError(f'JAO pagination duplicated source rows: {region}/{day}')
    start = f'{day}T00:00:00Z'
    end = f'{day + timedelta(days=1)}T00:00:00Z'
    stamps = [row['dateTimeUtc'] for row in records]
    if any(not start <= t < end for t in stamps):
        raise RuntimeError('JAO row outside requested UTC day')
    distinct = sorted(set(stamps))
    payload = {'region': region, 'date': str(day), 'filter': FILTER[region],
               'last_modified': modified, 'rows': records}
    with gzip.open(path.with_suffix('.json.gz.tmp'), 'wt', encoding='utf-8') as file:
        json.dump(payload, file, separators=(',', ':'))
    path.with_suffix('.json.gz.tmp').replace(path)
    receipt = {'region': region, 'date': str(day), 'filter': FILTER[region],
               'source': 'JAO public finalComputation', 'last_modified': modified,
               'total_rows': total, 'distinct_time_steps': len(distinct),
               'minimum_time': distinct[0] if distinct else None,
               'maximum_time': distinct[-1] if distinct else None,
               'pages': pages, 'sha256': sha(path),
               'market_domain_complete': False,
               'reason': 'filtered presolved/nonredundant rows omit other allocation rules and hub coupling'}
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt, False


def run(region, start, end, workers=1):
    if region not in FILTER:
        raise ValueError('Unknown JAO region')
    if not date(2025, 1, 1) <= start < end <= date(2026, 1, 1):
        raise ValueError('Require an exclusive-end date range within 2025')
    if not 1 <= workers <= 4:
        raise ValueError('Require one to four concurrent daily requests')
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / f'{region}.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        days = [start + timedelta(days=i) for i in range((end - start).days)]
        counts = {'downloaded': 0, 'existing': 0, 'rows': 0, 'days_with_no_rows': 0}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending = {pool.submit(one_day, region, day): day for day in days}
            try:
                for future in as_completed(pending):
                    day = pending[future]
                    receipt, existing = future.result()
                    counts['existing' if existing else 'downloaded'] += 1
                    counts['rows'] += receipt['total_rows']
                    counts['days_with_no_rows'] += receipt['total_rows'] == 0
                    if not existing:
                        print(f'{region} {day}: {receipt["total_rows"]} rows, '
                              f'{receipt["distinct_time_steps"]} time steps', flush=True)
            except Exception:
                for future in pending:
                    future.cancel()
                raise
    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', choices=FILTER, required=True)
    parser.add_argument('--start', type=date.fromisoformat, required=True)
    parser.add_argument('--end', type=date.fromisoformat, required=True,
                        help='Exclusive UTC end date')
    parser.add_argument('--workers', type=int, default=1)
    args = parser.parse_args()
    run(args.region, args.start, args.end, args.workers)
