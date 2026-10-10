"""Collect source-audited 2025 A44 hourly prices without changing app data."""
import argparse
import datetime as dt
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import xml.etree.ElementTree as ET
from eu_zones import ZONES, EXTERIORS
from flow_tracing import fetch, parse_day_ahead_prices, hourly

ROOT = Path(__file__).resolve().parents[1]


def collect(zone, eic, out):
    samples = {}; receipts = []; failures = []
    for month in range(1, 13):
        begin = dt.datetime(2025, month, 1, tzinfo=dt.timezone.utc)
        end = dt.datetime(2025 + (month == 12), month % 12 + 1, 1, tzinfo=dt.timezone.utc)
        params = dict(documentType='A44', processType='A01', in_Domain=eic,
                      out_Domain=eic, periodStart=begin.strftime('%Y%m%d%H%M'),
                      periodEnd=end.strftime('%Y%m%d%H%M'))
        try:
            raw = fetch(params, ROOT / 'data/price-trace/entsoe' / zone)
            document = ET.fromstring(raw)
            for element in document.iter():
                element.tag = element.tag.split('}')[-1]
            for series in document.findall('TimeSeries'):
                for field in ('in_Domain.mRID', 'out_Domain.mRID'):
                    if series.findtext(field) not in (None, eic):
                        raise ValueError('Response domain mismatch')
            for stamp, value in parse_day_ahead_prices(raw).items():
                if begin <= stamp < end:
                    if stamp in samples and samples[stamp] != value:
                        raise ValueError('Conflicting observations')
                    samples[stamp] = value
            receipts.append(dict(month=month, request=params,
                                 sha256=hashlib.sha256(raw).hexdigest()))
        except Exception as exc:
            message = str(exc)
            token = os.environ.get('ENTSOE_API_KEY')
            if token:
                message = message.replace(token, '[redacted]')
            failures.append(dict(month=month, error=message))
    start = dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)
    values = [hourly(samples, start + dt.timedelta(hours=i)) for i in range(8760)]
    path = out / (zone + '.json')
    path.write_text(json.dumps(values, separators=(',', ':'), allow_nan=False) + '\n')
    return zone, dict(source='ENTSO-E A44 day-ahead prices', price_eic=eic,
                      known_hours=sum(v is not None for v in values),
                      hourly_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      receipts=receipts, failed_months=failures)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--include-registry', action='store_true', help='Also attempt all registered European zones, preserving unavailable observations')
    a = p.parse_args()
    if (a.output / 'manifest.json').exists():
        raise FileExistsError('Use a fresh collection output')
    a.output.mkdir(parents=True, exist_ok=True)
    # Existing offline collector credential convention; never publish contents.
    credential = ROOT / 'data/price-trace/.entsoe-key'
    if not os.environ.get('ENTSOE_API_KEY') and credential.exists():
        os.environ['ENTSOE_API_KEY'] = credential.read_text().strip()
    existing = json.loads((ROOT / 'public/research/zone-prices-2025/manifest.json').read_text())
    registry = {z[0]: z[1] for z in ZONES + EXTERIORS}
    manifest = dict(year=2025, start_utc='2025-01-01T00:00:00Z', hours=8760,
                    aggregation='Mean of all four quarter-hour observations; incomplete hours remain missing',
                    zones={})
    requested = registry if a.include_registry else existing
    manifest['requested_zones'] = sorted(requested)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(collect, z, registry[z], a.output) for z in sorted(requested)]
        for future in as_completed(futures):
            z, record = future.result(); manifest['zones'][z] = record
            (a.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
            print(z, record['known_hours'], 'hours;', len(record['failed_months']), 'failed months', flush=True)


if __name__ == '__main__':
    main()
