"""Cache bounded original-provider candidates; access/coverage is not validation."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import urllib.request

SOURCES = {
    'owid': 'https://nyc3.digitaloceanspaces.com/owid-public/data/energy/owid-energy-data.csv',
    'ember-monthly': 'https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/monthly_full_release_long_format.csv',
    'energycharts-de': 'https://api.energy-charts.info/installed_power?country=de&year=2025',
}
MAX_BYTES = 100 * 1024 * 1024


def inspect(name, data):
    if name == 'energycharts-de':
        value = json.loads(data)
        if not isinstance(value, dict) or 'production_types' not in value:
            raise ValueError('Unexpected installed-power response')
        return dict(scope='Germany only; capacity units/dates require audit', keys=sorted(value),
                    technology_entries=len(value['production_types']))
    rows = csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
    field = 'year' if name == 'owid' else 'Date'
    if field not in (rows.fieldnames or []):
        raise ValueError('Provider time column changed')
    count = 0; areas = set(); dates = set()
    for row in rows:
        if str(row[field]).startswith('2025'):
            count += 1
            areas.add(row.get('country', row.get('Area', '')))
            dates.add(row[field])
    return dict(rows_2025=count, areas_2025=len(areas), dates_2025=sorted(dates),
                scope='Reported 2025 rows only; not complete country/technology coverage or hourly availability')


def collect(name, root):
    folder = root/name; folder.mkdir(parents=True, exist_ok=True)
    target = folder/'provider-data'; receipt = folder/'receipt.json'
    if target.exists() or receipt.exists():
        if not target.exists() or not receipt.exists():
            raise ValueError('Partial cache requires review')
        data = target.read_bytes(); record = json.loads(receipt.read_text())
        if record['source_url'] != SOURCES[name] or record['sha256'] != hashlib.sha256(data).hexdigest() or record['bytes'] != len(data):
            raise ValueError('Cached source identity changed')
        if record['coverage'] != inspect(name, data):
            raise ValueError('Cached coverage differs from provider data')
        return record
    with urllib.request.urlopen(SOURCES[name], timeout=60) as response:
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('Provider exceeds bounded cache limit')
        resolved = response.url
    coverage = inspect(name, data)
    record = dict(retrieved_utc=datetime.now(timezone.utc).isoformat(), source_url=SOURCES[name], resolved_url=resolved, bytes=len(data),
                  sha256=hashlib.sha256(data).hexdigest(), coverage=coverage,
                  status='candidate_source_access_checked_not_model_input_validation')
    # Exclusive files preserve prior evidence; incomplete writes require review.
    with target.open('xb') as stream: stream.write(data)
    with receipt.open('x') as stream: json.dump(record, stream, indent=2); stream.write('\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=SOURCES, required=True)
    parser.add_argument('--output', type=Path, default=Path('data/pypsa-eur/zonal-source-candidates'))
    args = parser.parse_args()
    print(json.dumps(collect(args.source, args.output), indent=2))
