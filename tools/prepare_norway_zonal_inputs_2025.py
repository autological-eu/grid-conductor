"""Collect and audit Norwegian metered zonal inputs; does not change the solver.

Elhub observations are validation/demand candidates, never renewable availability.
NVE current fleet snapshots cannot certify historical capacity or hydro inflows.
"""
import argparse
import concurrent.futures
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/bidding-zone-source-audit-2025'
ZONES = tuple('NO' + str(i) for i in range(1, 6))
GROUPS = {'consumption': ('cabin', 'household', 'primary', 'secondary', 'tertiary'),
          'production': ('hydro', 'other', 'solar', 'thermal', 'wind')}
START = dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)
END = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
HOURS = tuple(START + dt.timedelta(hours=i) for i in range(8760))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cached_json(url, folder):
    """Cache only complete successful JSON responses, verifying every reuse."""
    key = hashlib.sha256(url.encode()).hexdigest()
    path = folder / (key + '.json')
    receipt = folder / (key + '.meta.json')
    if path.exists() and receipt.exists():
        meta = json.loads(receipt.read_text())
        if meta['url'] != url or digest(path) != meta['sha256']:
            raise ValueError('Changed source cache')
        return json.loads(path.read_text()), meta
    with urllib.request.urlopen(url, timeout=45) as response:
        raw = response.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
        raise ValueError('Malformed Elhub response')
    folder.mkdir(parents=True, exist_ok=True)
    meta = dict(url=url, sha256=hashlib.sha256(raw).hexdigest(),
                retrieved_at=dt.datetime.now(dt.timezone.utc).isoformat())
    path.write_bytes(raw)
    receipt.write_text(json.dumps(meta, indent=2) + '\n')
    return payload, meta


def instant(text):
    value = dt.datetime.fromisoformat(text.replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('Missing source timezone')
    return value.astimezone(dt.timezone.utc)


def merge_payload(payload, kind, rows):
    """Exact UTC/group keys; wildcard generation is separate, never a total."""
    field = kind + 'PerGroupMbaHour'
    for area in payload['data']:
        zone = area['id']
        values = area['attributes'].get(field, [])
        if zone == '*':
            if values:
                raise ValueError('Unassigned price-area observations')
            continue
        if zone not in ZONES:
            raise ValueError('Unexpected price area')
        for row in values:
            start, end = instant(row['startTime']), instant(row['endTime'])
            if end - start != dt.timedelta(hours=1) or start.minute or start.second or start.microsecond:
                raise ValueError('Non-hourly interval')
            if row['priceArea'] != zone:
                raise ValueError('Conflicting price area')
            group = row[kind + 'Group']
            if group not in GROUPS[kind] and not (kind == 'production' and group == '*'):
                raise ValueError('Undeclared source group')
            value = float(row['quantityKwh']) / 1000  # interval energy MWh
            if not math.isfinite(value):
                raise ValueError('Nonfinite metered energy')
            if not START <= start < END:
                continue
            key = (zone, start, group)
            if key in rows and rows[key] != value:
                raise ValueError('Conflicting overlapping source observation')
            rows[key] = value


def collect(kind, folder):
    rows, receipts = {}, []
    # Provider date-only queries are local days. Extra boundary day covers the
    # last UTC hour of 2025; overlap is reconciled rather than silently overwritten.
    bounds = [(f'2025-{m:02d}-01', f'2025-{m+1:02d}-01' if m < 12 else '2026-01-01')
              for m in range(1, 13)] + [('2025-12-31', '2026-01-02')]
    for start, end in bounds:
        query = urllib.parse.urlencode(dict(dataset=kind.upper() + '_PER_GROUP_MBA_HOUR',
                                            startDate=start, endDate=end))
        url = 'https://api.elhub.no/energy-data/v0/price-areas?' + query
        payload, meta = cached_json(url, folder / 'raw')
        merge_payload(payload, kind, rows)
        receipts.append(meta)
        print(kind, start, 'verified', flush=True)
    return rows, receipts


def verified_snapshot(name):
    path = SOURCE / (name + '.json')
    meta = json.loads(path.with_name(name + '.meta.json').read_text())
    if digest(path) != meta['sha256']:
        raise ValueError('Changed NVE source snapshot')
    return json.loads(path.read_text()), meta


def fleet_summary():
    hydro, hm = verified_snapshot('nve-hydro')
    wind, wm = verified_snapshot('nve-wind')
    result = {}
    for zone in ZONES:
        h = [p for p in hydro if str(p['ElspotomraadeNummer']) == zone[-1]
             and p['VannKVTypeID'] in ('K', 'PK')]
        w = [p for p in wind if str(p['ElspotomraadeNummer']) == zone[-1]]
        result[zone] = dict(current_hydro_turbine_mw=sum(p['MaksYtelse'] for p in h),
                            current_wind_mw=sum(p['InstallertEffekt_MW'] for p in w),
                            hydro_plants=len(h), wind_plants=len(w),
                            hydro_first_operation_after_2025=sum(
                                bool(p.get('IDriftDato')) and p['IDriftDato'][:10] > '2025-12-31' for p in h))
    return dict(zones=result, sources=[hm, wm], historical_2025_capacity_verified=False,
                limitation='Current operating fleet; first operation dates do not date later upgrades or retired units. Pumps excluded from turbine MW; normal-year output is not 2025 output.')


def run(folder):
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {kind: pool.submit(collect, kind, folder) for kind in GROUPS}
        data = {kind: future.result() for kind, future in futures.items()}
    reservoir, receipt = verified_snapshot('nve-reservoir-history')
    stocks = [r for r in reservoir if r['omrType'] == 'EL' and r['omrnr'] in range(1, 6)
              and '2024-12-15' <= r['dato_Id'] <= '2026-01-15']
    annual = {}
    with (folder / 'hourly.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['zone', 'utc', 'metered_consumption_mwh',
                         *[g + '_mwh' for g in GROUPS['production']], 'unclassified_production_mwh'])
        for zone in ZONES:
            totals = {k: 0. for k in ('consumption', *GROUPS['production'], 'unclassified')}
            missing = {kind: [] for kind in GROUPS}
            negative = {kind: 0 for kind in GROUPS}
            for hour in HOURS:
                c = [data['consumption'][0].get((zone, hour, g)) for g in GROUPS['consumption']]
                p = [data['production'][0].get((zone, hour, g)) for g in GROUPS['production']]
                for kind, values in [('consumption', c), ('production', p)]:
                    if None in values:
                        missing[kind].append(hour.isoformat())
                    negative[kind] += sum(v is not None and v < 0 for v in values)
                load = sum(c) if None not in c else None
                unknown = data['production'][0].get((zone, hour, '*'))
                writer.writerow([zone, hour.isoformat(), load, *p, unknown])
                if load is not None:
                    totals['consumption'] += load / 1e6
                for group, value in zip(GROUPS['production'], p):
                    if value is not None:
                        totals[group] += value / 1e6
                if unknown is not None:
                    totals['unclassified'] += unknown / 1e6
            annual[zone] = dict(observed_energy_twh=totals,
                                complete_hours={k: 8760 - len(v) for k, v in missing.items()},
                                missing_hours=missing, negative_group_intervals=negative,
                                reservoir_iso_2025_observations=sum(r['iso_aar'] == 2025 and r['omrnr'] == int(zone[-1]) for r in stocks))
    (folder / 'reservoir-stocks.json').write_text(json.dumps(stocks, separators=(',', ':')) + '\n')
    summary = dict(status='audited_source_input_pilot_not_adopted_model', year=2025,
                   sources=[m for _, receipts in data.values() for m in receipts],
                   producer_sha256=digest(Path(__file__)), hourly_sha256=digest(folder / 'hourly.csv'),
                   zones=annual, fleet=fleet_summary(), reservoir_source=receipt,
                   reservoir_sha256=digest(folder / 'reservoir-stocks.json'),
                   limitations=['Metered consumption is not yet reconciled to ENTSO-E total load, losses or self-consumption.',
                                'Timestamp/group coverage does not certify metering completeness.',
                                'Production wildcard is unclassified and excluded from named technology sums, pending provider definition.',
                                'No observed generation has been used as renewable availability or reservoir inflow.',
                                'Weekly stocks do not determine hourly inflow/spill or reservoir cascades.'])
    (folder / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({z: {k: v for k, v in x.items() if k != 'missing_hours'} for z, x in annual.items()}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=SOURCE / 'elhub-annual-v1')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    run(args.out)
