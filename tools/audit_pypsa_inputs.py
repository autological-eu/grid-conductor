"""Audit the pinned upstream demand and plant inventory for January, without fills."""
import csv
import datetime as dt
import json
import math
from pypsa_border_targets import ROOT, digest, write_json
from prepare_pypsa_targets import COUNTRIES


def audit():
    start = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    end = dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc)
    expected = {start+dt.timedelta(hours=i) for i in range(744)}
    demand_path = ROOT/'data/pypsa-eur/entsoe-demand-2026-02-02.csv'
    plants_path = ROOT/'data/pypsa-eur/powerplants-0.8.1.csv'
    observed = {c: {} for c in COUNTRIES}
    with demand_path.open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            instant = dt.datetime.fromisoformat(row[''])
            if instant.tzinfo is None:
                raise ValueError('Demand archive timezone missing')
            instant = instant.astimezone(dt.timezone.utc)
            if not start <= instant < end:
                continue
            if instant not in expected:
                raise ValueError('Demand archive is not hourly aligned')
            for country in COUNTRIES:
                value = row.get(country, '')
                if not value:
                    continue
                value = float(value)
                if not math.isfinite(value) or value < 0:
                    continue
                if instant in observed[country]:
                    raise ValueError('Duplicate archive hour')
                observed[country][instant] = value
    plants = {}; missing_dates = 0; dated_after_january = 0
    with plants_path.open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            capacity = float(row['Capacity']) if row['Capacity'] else float('nan')
            if not math.isfinite(capacity) or capacity <= 0:
                continue
            year_in = float(row['DateIn']) if row['DateIn'] else None
            year_out = float(row['DateOut']) if row['DateOut'] else None
            if year_in is not None and year_in >= 2026:
                dated_after_january += 1
                continue  # year-only commissioning cannot establish January availability
            if year_out is not None and year_out < 2026:
                continue
            missing_dates += year_in is None
            key = row['Country']+' / '+row['Fueltype']
            plants[key] = plants.get(key, 0)+capacity
    return dict(status='input_audit_not_model_validation', start=start.isoformat(),
        end_exclusive=end.isoformat(),
        demand_source_sha256=digest(demand_path), plant_source_sha256=digest(plants_path),
        demand=[dict(country=c, observed_hours=len(v), expected_hours=744,
                     observed_energy_mwh=sum(v.values()), complete=len(v)==744)
                for c, v in observed.items()],
        capacity_mw_by_country_fuel=plants,
        undated_commissioning_rows=missing_dates,
        commissioning_2026_or_later_excluded_rows=dated_after_january,
        limitations=['Upstream demand is an ENTSO-E-derived hourly archive; native-resolution completeness must still be checked.',
            'Installed capacity is not outage-adjusted available capacity.',
            'Missing commissioning dates and retirement dates within 2026 need asset-level reconciliation.',
            'Demand coverage is not a pass for generation, storage, network or market validation.'])


if __name__ == '__main__':
    report = audit()
    write_json(ROOT/'public/research/pypsa-input-audit.json', report)
    print(json.dumps(dict(complete_demand_countries=sum(r['complete'] for r in report['demand']),
                         countries=len(report['demand']), status=report['status'])))
