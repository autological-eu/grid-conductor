"""Audit published hourly observation coverage before model comparison; no fit."""
import argparse
import calendar
import json
import math
from pathlib import Path
from monthly_dispatch import digest, save


def summarize(values, declared_hours):
    if len(values) != 8760 or any(v is not None and (type(v) not in (int, float) or not math.isfinite(v)) for v in values):
        raise ValueError('Expected 8,760 finite numeric/null hourly observations')
    known = [v for v in values if v is not None]
    if len(known) != declared_hours:
        raise ValueError('Declared observation coverage mismatch')
    rows = [];offset = 0
    for month in range(1, 13):
        hours = calendar.monthrange(2025, month)[1]*24
        subset = [v for v in values[offset:offset+hours] if v is not None]
        rows.append(dict(month=month, hours=hours, observed_hours=len(subset),
                         mean_price_eur_mwh=math.fsum(subset)/len(subset) if subset else None,
                         negative_price_hours=sum(v < 0 for v in subset)))
        offset += hours
    return dict(observed_hours=len(known), missing_hours=8760-len(known),
                first_missing_hour_index=next((i for i,v in enumerate(values) if v is None), None),
                mean_price_eur_mwh=math.fsum(known)/len(known) if known else None,
                minimum_price_eur_mwh=min(known) if known else None,
                maximum_price_eur_mwh=max(known) if known else None, monthly=rows)


def audit(folder):
    path=folder/'manifest.json';manifest=json.loads(path.read_text());rows=[]
    for zone,item in sorted(manifest.items()):
        if item['status'] != 'published':
            raise ValueError('Unpublished zone in observation inventory')
        file=folder/f'{zone}.json'
        rows.append(dict(zone=zone, hourly_sha256=digest(file), published_source=item,
                         **summarize(json.loads(file.read_text()),item['known_hours'])))
    return dict(status='observations_inventory_only', year=2025, unit='EUR/MWh',
                start='2025-01-01T00:00:00Z', end_exclusive='2026-01-01T00:00:00Z', step_hours=1,
                manifest_sha256=digest(path), producer_sha256=digest(Path(__file__)), zones=rows,
                limitations=['Hourly arrays inherit their published provider/interval aggregation provenance.',
                             'No missing observations filled; negative prices remain observations.',
                             'Coverage and summary statistics do not validate dispatch or price agreement.',
                             'Bidding-zone mapping, held-out protocol and acceptance thresholds remain open.',
                             'Generation mix and correctly labelled exchange observations require separate audits.'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prices',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=audit(args.prices)
    args.output.parent.mkdir(parents=True,exist_ok=True);save(args.output,report)
    print(f"Audited {len(report['zones'])} published price zones; observations inventory only, no empirical validation")
