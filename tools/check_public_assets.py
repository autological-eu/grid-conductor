"""Reject unused/public intermediate data returning to the static publication."""
from pathlib import Path
import fnmatch
import gzip
import hashlib
import json
from pack_model_metadata import FILES

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = [
    'entsoe-fast-targets.json', 'carbon-spreads-2025.json',
    'zone-prices-2025/*.json', 'irena-capacity-2025/summary.json.gz',
    'european-reservoir-clearing-2025/summary.json.gz',
    'european-reservoir-clearing-2025/replay.json',
    'fixed-reservoir-screening-2025/summary.json.gz',
    'fixed-reservoir-screening-2025/area-summary.csv',
    'fixed-reservoir-screening-2025/hourly-de.csv.gz',
    'fixed-reservoir-screening-2025/model-prices.png', 'fixed-reservoir-screening-2025/model-hydro.png',
    'daily-fuel-annual-2025/replay.json', 'daily-fuel-annual-2025/price-comparison.json',
    'daily-fuel-annual-2025/summary.json.gz', 'daily-fuel-annual-2025/germany-prices.png',
    'daily-fuel-annual-2025/monthly-errors.png', 'daily-fuel-annual-2025/zone-errors.png',
    'daily-fuel-annual-2025/zone-errors.csv',
    'daily-fuel-annual-2025/border-errors.csv',
    'daily-fuel-annual-2025/germany-hourly.csv.gz',
]


def check():
    folder = ROOT / 'public/research'
    files = [p for p in folder.rglob('*') if p.is_file()]
    hydrated = [p for p in files if str(p.relative_to(folder)) in FILES]
    for p in hydrated:
        assert p.read_bytes() == gzip.decompress(p.with_name(p.name + '.gz').read_bytes()), 'Changed hydrated metadata'
    files = [p for p in files if p not in hydrated]
    archived = {name: gzip.decompress((folder / (name + '.gz')).read_bytes()) for name in FILES}
    for raw in archived.values():
        assert isinstance(json.loads(raw), dict), 'Invalid archived JSON'
    daily = json.loads((folder / 'daily-fuel-annual-2025/replay.json').read_text())
    assert hashlib.sha256(archived['daily-fuel-annual-2025/summary.json']).hexdigest() == daily['summary_sha256'], 'Detached daily replay'
    fixed = json.loads(archived['fixed-reservoir-screening-2025/summary.json'])['provenance']
    assert hashlib.sha256(archived['european-reservoir-clearing-2025/summary.json']).hexdigest() == fixed['annual_summary_sha256'], 'Detached hydro source'
    assert hashlib.sha256((folder / 'european-reservoir-clearing-2025/replay.json').read_bytes()).hexdigest() == fixed['water_replay_sha256'], 'Detached water replay'
    carbon = json.loads((folder / 'carbon-spreads-2025.json').read_text())
    assert carbon['year'] == 2025 and len(carbon['borders']) == 68
    assert carbon['metric_sha256'] == hashlib.sha256((ROOT / 'src/lib/carbon-spread.ts').read_bytes()).hexdigest(), 'Changed carbon metric'
    for zone, digest in carbon['price_sha256'].items():
        assert hashlib.sha256((folder / 'zone-prices-2025' / (zone + '.json')).read_bytes()).hexdigest() == digest, 'Changed carbon price selection'
    unexpected = [str(p.relative_to(folder)) for p in files
                  if not any(fnmatch.fnmatch(str(p.relative_to(folder)), pattern) for pattern in ALLOWED)]
    if unexpected:
        raise ValueError('Unapproved public intermediate assets: ' + ', '.join(unexpected))
    print(f'Public assets: {len(files)} files; {sum(p.stat().st_size for p in files)/1024**2:.2f} MiB; allowlist passed')


if __name__ == '__main__':
    check()
