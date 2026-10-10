"""Independent raw Elhub-to-CSV replay and national Ember comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.parse
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(folder):
    summary = json.loads((folder / 'summary.json').read_text())
    if digest(ROOT / 'tools/prepare_norway_zonal_inputs_2025.py') != summary['producer_sha256']:
        raise ValueError('Changed producer')
    if digest(folder / 'hourly.csv') != summary['hourly_sha256']:
        raise ValueError('Changed prepared observations')
    records = []
    for meta in summary['sources']:
        raw = folder / 'raw' / (hashlib.sha256(meta['url'].encode()).hexdigest() + '.json')
        if digest(raw) != meta['sha256']:
            raise ValueError('Changed provider response')
        query = urllib.parse.parse_qs(urllib.parse.urlparse(meta['url']).query)
        kind = query['dataset'][0].split('_')[0].lower()
        payload = json.loads(raw.read_text())
        for area in payload['data']:
            for row in area['attributes'].get(kind + 'PerGroupMbaHour', []):
                records.append((area['id'], row['priceArea'], kind, row[kind + 'Group'],
                                row['startTime'], row['endTime'], row['quantityKwh']))
    source = pd.DataFrame(records, columns=['zone', 'row_zone', 'kind', 'group', 'start', 'end', 'kwh'])
    source['utc'] = pd.to_datetime(source['start'], utc=True)
    end = pd.to_datetime(source['end'], utc=True)
    if not (end - source.utc == pd.Timedelta(hours=1)).all() or not (source.zone == source.row_zone).all():
        raise ValueError('Source geography/interval mismatch')
    source = source[(source.utc >= '2025-01-01') & (source.utc < '2026-01-01')]
    keys = ['zone', 'utc', 'kind', 'group']
    if source.groupby(keys).kwh.nunique().max() != 1:
        raise ValueError('Conflicting raw overlap')
    source = source.drop_duplicates(keys)
    prepared = pd.read_csv(folder / 'hourly.csv', parse_dates=['utc']).set_index(['zone', 'utc'])
    if prepared.index.has_duplicates or len(prepared) != 5 * 8760:
        raise ValueError('Prepared calendar mismatch')
    errors = {}
    for kind in ['consumption', 'production']:
        sub = source[source.kind == kind].copy()
        sub['mwh'] = pd.to_numeric(sub.kwh) / 1000
        groups = ['cabin', 'household', 'primary', 'secondary', 'tertiary'] if kind == 'consumption' else ['hydro', 'other', 'solar', 'thermal', 'wind', '*']
        wide = sub.pivot(index=['zone', 'utc'], columns='group', values='mwh').reindex(prepared.index)
        if kind == 'consumption':
            pairs = [('metered_consumption_mwh', wide.reindex(columns=groups).sum(axis=1, min_count=5))]
        else:
            pairs = [(('unclassified_production' if g == '*' else g) + '_mwh', wide.get(g, pd.Series(np.nan, index=wide.index))) for g in groups]
        for column, expected in pairs:
            actual = prepared[column]
            if not (actual.isna() == expected.isna()).all():
                raise ValueError('Missingness changed: ' + column)
            error = float((actual - expected).abs().max()) if expected.notna().any() else 0.
            if error > 1e-8:
                raise ValueError('Raw replay mismatch: ' + column)
            errors[column] = error
    ember = ROOT / 'data/pypsa-eur/ember-current-release/monthly.csv'
    receipt = json.loads(ember.with_name('receipt.json').read_text())
    if digest(ember) != receipt['sha256']:
        raise ValueError('Changed Ember source')
    df = pd.read_csv(ember, usecols=['Date', 'ISO 3 code', 'Area type', 'Electricity source', 'Generation (TWh)'])
    df = df[(df['ISO 3 code'] == 'NOR') & df.Date.str.startswith('2025') & df['Area type'].str.lower().str.startswith('country')]
    national = {}
    for category, column in [('Demand', 'metered_consumption_mwh'), ('Hydro', 'hydro_mwh'), ('Wind', 'wind_mwh'), ('Solar', 'solar_mwh')]:
        sub = df[df['Electricity source'] == category]
        if len(sub) != 12 or sub.Date.nunique() != 12:
            raise ValueError('Incomplete Ember comparison')
        observed = float(prepared[column].sum() / 1e6)
        reference = float(sub['Generation (TWh)'].sum())
        national[category] = dict(elhub_covered_twh=observed, ember_twh=reference,
                                  difference_twh=observed - reference,
                                  missing_zone_hours=int(prepared[column].isna().sum()))
    output = dict(status='raw_source_replay_passed_not_market_acceptance',
                  summary_sha256=digest(folder / 'summary.json'), auditor_sha256=digest(Path(__file__)),
                  max_replay_error_mwh=errors, national_comparison=national,
                  ember_sha256=receipt['sha256'],
                  unclassified_generation_twh=float(prepared.unclassified_production_mwh.sum() / 1e6),
                  limitation='Country differences are reported without rescaling; metered consumption and total-load scopes are not interchangeable.')
    (folder / 'audit.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=ROOT / 'data/bidding-zone-source-audit-2025/elhub-annual-v1')
    audit(parser.parse_args().folder)
