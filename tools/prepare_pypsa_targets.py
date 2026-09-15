"""Inventory actual PyPSA-Eur OSM borders before operational inputs are ready.

No fabricated opportunity values. Source release 0.7 is a February 2026 snapshot,
so existence in this inventory does not establish January commissioning status.
"""
import csv
import json
from pathlib import Path
from pypsa_border_targets import ROOT, UPSTREAM_COMMIT, digest, write_json

COUNTRIES = 'AL AT BA BE BG CH CZ DE DK EE ES FI FR GB GR HR HU IE IT LT LU LV ME MK NL NO PL PT RO RS SE SI SK XK'.split()
EXPECTED_MD5 = {
    'buses': '031c30f04dc24e99210b3f5ad8a01c94',
    'lines': '04d1e7cb33835de9c7d8be4716c6a8bf',
    'links': '2ddd515a30cfc19205e6681def579fbd',
    'converters': 'fe13a4f336fdc273c808cdfc485b4753',
    'transformers': 'b6730b52097d2691d49231bdd53c7bd4',
}


def input_readiness(bank_path, jao_paths):
    bank = json.loads(bank_path.read_text(encoding='utf-8'))
    # Explicit mappings only. DE-LU cannot be split into national demand here.
    split = {'DK': ['DK1', 'DK2'], 'SE': ['SE1', 'SE2', 'SE3', 'SE4']}
    rows = []
    for country in COUNTRIES:
        zones = split.get(country, [country])
        issues = []
        if country in ['DE', 'LU']:
            issues.append('Joint DE-LU demand requires geographic reconciliation')
        if country == 'IT':
            issues.append('Italian bidding-zone registry must be reconciled before aggregation')
        for zone in zones:
            load = bank.get('load_mw', {}).get(zone, [])
            generation = bank.get('generation_mw', {}).get(zone, {})
            if len(load) != 2976 or any(v is None for v in load):
                issues.append(f'{zone}: missing or incomplete demand')
            if not generation or any(len(v) != 2976 or any(x is None for x in v) for v in generation.values()):
                issues.append(f'{zone}: missing or incomplete reported generation')
        rows.append(dict(country=country, quantity_series_complete=not issues, issues=issues))
    return dict(status='not_validated', entsoe_bank_sha256=digest(bank_path), countries=rows,
                jao_publications=[dict(file=p.name, sha256=digest(p)) for p in jao_paths],
                note='Completeness of included series is not proof of complete generation coverage, balance or model validity. JAO domains are evidence only until mapped to model results.')


def inventory(folder):
    import hashlib
    tables = {}
    sources = []
    for part, expected in EXPECTED_MD5.items():
        path = folder / (part + '.csv')
        if hashlib.md5(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Official archive checksum mismatch: {part}')
        with path.open(encoding='utf-8', newline='') as stream:
            tables[part] = list(csv.DictReader(stream))
        sources.append(dict(url=f'https://zenodo.org/records/18619025/files/{part}.csv',
                            sha256=digest(path), archive_md5=expected))
    buses = {b['bus_id']: b for b in tables['buses']}
    countries = {}
    for bus in buses.values():
        if bus['country'] in COUNTRIES and bus['under_construction'] == 'f':
            countries.setdefault(bus['country'], []).append(bus)
    borders = {}
    for component in ['lines', 'links']:
        for row in tables[component]:
            if row['under_construction'] != 'f':
                continue
            a, b = buses[row['bus0']], buses[row['bus1']]
            if a['under_construction'] != 'f' or b['under_construction'] != 'f':
                continue
            a, b = sorted([a['country'], b['country']])
            if a == b or a not in COUNTRIES or b not in COUNTRIES:
                continue
            target = borders.setdefault(f'{a}-{b}', dict(id=f'{a}-{b}', a=a, b=b,
                status='awaiting_operational_baseline', opportunity_meur=None,
                modelled_opportunity_meur=None, assets=[]))
            target['assets'].append(dict(component='Line' if component == 'lines' else 'Link',
                                         id=row['line_id' if component == 'lines' else 'link_id']))
    return dict(schema_version=1, status='awaiting_operational_baseline',
        start='2026-01-01T00:00:00Z', end_exclusive='2026-02-01T00:00:00Z',
        additional_mw=100, metric='system_operating_cost_reduction', unit='MEUR/period',
        upstream_commit=UPSTREAM_COMMIT, annual_opportunity_meur=None,
        source_release='PyPSA-Eur OSM 0.7; retrieved by upstream 2026-02-11',
        attribution='OpenStreetMap contributors; PyPSA-Eur; ODbL-1.0', sources=sources,
        excluded_countries=['UA', 'MD'],
        limitations=['All cross-country connections in the configured 34-country upstream scope; not every geographic European country.',
            'January commissioning/outage status has not yet been reconciled with the February source snapshot.',
            'No operational baseline or opportunity calculation has been run for this inventory.',
            'ENTSO-E generation/load/flow and JAO validation are pending; publication coverage is not validation.'],
        nodes=[dict(id=c, x=sum(float(b['x']) for b in rows)/len(rows),
                    y=sum(float(b['y']) for b in rows)/len(rows)) for c, rows in sorted(countries.items())],
        targets=sorted(borders.values(), key=lambda t: t['id']))


if __name__ == '__main__':
    report = inventory(ROOT/'data/pypsa-eur/source-osm')
    report['validation'] = input_readiness(ROOT/'data/eu-market/bank-2026-01-v2.json',
        [ROOT/'public/research/jao-january-coverage.json', ROOT/'public/research/jao-nordic-january-coverage.json'])
    write_json(ROOT/'public/research/pypsa-targets.json', report)
    print(json.dumps(dict(countries=len(report['nodes']), borders=len(report['targets']), status=report['status'])))
