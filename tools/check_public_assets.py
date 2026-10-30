"""Verify only assets consumed by the live workbench and country explorer."""
from pathlib import Path
import fnmatch
import gzip
import hashlib
import json
from check_country_explorer import check as check_countries

root = Path(__file__).resolve().parents[1]
out = root / 'public/research/zone-prices-2025'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check():
    folder = root / 'public/research'
    check_countries()
    targets = json.loads((folder / 'entsoe-fast-targets.json').read_text())
    assert str(targets['year']) == '2025' and len(targets['targets']) >= 68
    manifest = json.loads((out / 'manifest.json').read_text())
    coverage = json.loads((out / 'coverage.json').read_text())
    assert coverage['year'] == 2025 and coverage['manifest_sha256'] == sha(out / 'manifest.json')
    assert coverage['zones'] == 39 and coverage['corridors'] == 68
    assert len(coverage['coverage']) == 68
    carbon = json.loads((folder / 'carbon-spreads-2025.json').read_text())
    assert carbon['year'] == 2025 and len(carbon['borders']) == 68
    assert carbon['metric_sha256'] == sha(root / 'src/lib/carbon-spread.ts')
    for zone, digest in carbon['price_sha256'].items():
        assert zone in manifest and sha(out / (zone + '.json')) == digest
    # This archive is also an input to the retained solar-capacity baseline.
    irena = json.loads(gzip.decompress((folder / 'irena-capacity-2025/summary.json.gz').read_bytes()))
    assert irena['country_count'] >= 30 and len(irena['irena_rows']) >= 400
    allowed = [
        'entsoe-fast-targets.json', 'carbon-spreads-2025.json',
        'zone-prices-2025/*.json', 'country-explorer-2025/*.json',
        'country-explorer-2025/*.json.gz',
        'irena-capacity-2025/summary.json.gz',
    ]
    files = [p for p in folder.rglob('*') if p.is_file()]
    unexpected = [str(p.relative_to(folder)) for p in files
                  if not any(fnmatch.fnmatch(str(p.relative_to(folder)), pattern) for pattern in allowed)]
    assert not unexpected, f'Unapproved public assets: {unexpected}'
    print(f'Public assets: {len(files)} files; {sum(p.stat().st_size for p in files)/1024**2:.2f} MiB; allowlist passed')


if __name__ == '__main__':
    check()
