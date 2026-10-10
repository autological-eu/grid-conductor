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
    'fixed-reservoir-screening-2025/resource-bids.json',
    'fixed-reservoir-screening-2025/resource-bids-curves.png',
    'fixed-reservoir-screening-2025/resource-bids-errors.png',
    'fixed-reservoir-screening-2025/area-summary.csv',
    'fixed-reservoir-screening-2025/hourly-de.csv.gz',
    'fixed-reservoir-screening-2025/model-prices.png', 'fixed-reservoir-screening-2025/model-hydro.png',
    'daily-fuel-annual-2025/compact-zonal.json', 'daily-fuel-annual-2025/compact-zonal.png',
    'daily-fuel-annual-2025/performance.json',
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
    performance = json.loads((folder / 'daily-fuel-annual-2025/performance.json').read_text())
    assert performance['reference_summary_sha256'] == daily['summary_sha256'], 'Detached performance baseline'
    assert performance['execution_driver_sha256'] == hashlib.sha256((ROOT / 'tools/fast_daily_market.py').read_bytes()).hexdigest(), 'Changed performance adapter'
    assert performance['coefficient_days_checked'] == 365 and len(performance['selected_days']) == 18
    for engine in performance['records']:
        assert all(row['attempts'][-1]['status'] == 'HighsModelStatus.kOptimal' for row in engine['days'])
    annual = performance['annual_validation']
    assert annual['hours'] == 8760 and annual['days'] == 365 and annual['preparation_arrays_identical']
    assert annual['execution_driver_sha256'] == performance['execution_driver_sha256']
    assert annual['replay']['closure_residual_mwh'] == 0 and annual['replay']['maximum_join_residual_mwh'] == 0
    assert annual['replay']['maximum_primal_residual'] <= 1e-4 and annual['simultaneous_storage_hours'] == 0
    compact = json.loads((folder / 'daily-fuel-annual-2025/compact-zonal.json').read_text())
    assert compact['hours'] == 8760 and compact['days'] == 365 and compact['window_statistics']['optimal_days'] == 365
    assert compact['source_summary_sha256'] == compact['replay']['summary_sha256'], 'Detached compact replay'
    assert compact['physics'] == compact['replay']['physics']
    assert compact['physics']['maximum_residual'] <= 1e-4 and compact['physics']['closure_mwh'] == 0
    assert compact['physics']['simultaneous_storage_hours'] == 0
    for name, sha in compact['provenance']['dependencies'].items():
        assert hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest() == sha, 'Changed compact calculation source'
    assert compact['publication_producer_sha256'] == hashlib.sha256((ROOT / 'tools/report_compact_zonal_2025.py').read_bytes()).hexdigest()
    assert compact['image_sha256'] == hashlib.sha256((folder / 'daily-fuel-annual-2025/compact-zonal.png').read_bytes()).hexdigest()
    assert len(compact['native_checks']) == 3
    assert all(abs(row['objective_difference_eur']) <= max(.05, abs(row['native_objective_eur'])*1e-8) for row in compact['native_checks'])
    fixed = json.loads(archived['fixed-reservoir-screening-2025/summary.json'])['provenance']
    assert hashlib.sha256(archived['european-reservoir-clearing-2025/summary.json']).hexdigest() == fixed['annual_summary_sha256'], 'Detached hydro source'
    assert hashlib.sha256((folder / 'european-reservoir-clearing-2025/replay.json').read_bytes()).hexdigest() == fixed['water_replay_sha256'], 'Detached water replay'
    combined = json.loads((folder / 'fixed-reservoir-screening-2025/resource-bids.json').read_text())
    assert combined['hours'] == 8760 and len(combined['cases']) == 3
    assert combined['source_summary_sha256'] == combined['replay']['summary_sha256'], 'Detached combined replay'
    assert combined['provenance']['reference_summary_sha256'] == hashlib.sha256(archived['fixed-reservoir-screening-2025/summary.json']).hexdigest(), 'Detached fixed reference'
    assert combined['water_residual_mwh'] <= 1e-4
    for variant, record in combined['cases'].items():
        assert record['optimal_hours'] == 8760 and record['physics'] == combined['replay']['cases'][variant]
        assert record['maximum_live_residual_mw'] <= 1e-4 and record['physics']['maximum_residual_mw'] <= 1e-4
        assert len(record['native_checks']) == 3
        assert all(abs(row['difference_eur']) <= max(.05, abs(row['native_objective_eur'])*1e-8) for row in record['native_checks'])
    for name, sha in combined['provenance']['dependencies'].items():
        assert hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest() == sha, 'Changed combined calculation source'
    assert combined['publication_producer_sha256'] == hashlib.sha256((ROOT / 'tools/evaluate_fixed_hydro_bids_2025.py').read_bytes()).hexdigest()
    for name, sha in combined['images'].items():
        assert hashlib.sha256((folder / 'fixed-reservoir-screening-2025' / name).read_bytes()).hexdigest() == sha, 'Changed combined figure'
    assert len(combined['mapped_zone_errors']) == 39 and len(combined['german_offer_examples']) == 9
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
