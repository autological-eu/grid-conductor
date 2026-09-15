"""Check a one-hour Core domain against JAO's published quarter-hour positions.

This is network-data validation, not validation of estimated supply offers.
"""
import argparse
import datetime as dt
import gzip
import json
from pathlib import Path
from carbon_pilot import ROOT, timestamp, iso
from jao_constraints import collect, page


def check_positions(constraints,positions,tolerance_mw=.1):
    checks=[]
    for position in positions:
        values={k[4:]:v for k,v in position.items() if k.startswith('hub_') and v is not None}
        needed={h for row in constraints for h in row['ptdf']}
        if not needed<=set(values):raise ValueError('Missing published hub positions')
        residuals=[sum(v*values[h] for h,v in row['ptdf'].items())-row['ram_mw'] for row in constraints]
        balance=sum(values.values())
        worst=max(residuals) if residuals else None
        checks.append(dict(start=position['dateTimeUtc'],net_position_sum_mw=balance,
            max_constraint_violation_mw=max(0,worst) if worst is not None else None,
            passed=worst is not None and worst<=tolerance_mw and abs(balance)<=tolerance_mw))
    return checks


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start',default='2026-01-01T00:00:00Z')
    p.add_argument('--output',type=Path,default=ROOT/'public/research/jao-network-validation.json')
    args=p.parse_args();start=timestamp(args.start);end=start+dt.timedelta(hours=1)
    if start.minute or start.second:raise ValueError('Use a full UTC hour')
    summary=collect('core',start,end)
    bundle=json.loads(gzip.decompress((ROOT/summary['bundle_path']).read_bytes()))
    if set(r['start'] for r in bundle['constraints'])!={iso(start)}:
        raise ValueError('Sample expects one published hourly domain; do not blend changing domains')
    auxiliary={};provenance=[]
    for endpoint in ['bexRestrictions','allocationConstraint','lta','ltn','netPos','activeFbConstraints','alphaFactor']:
        payload,meta=page('core',start,end,0,5000,ROOT/'data/jao/raw',endpoint)
        if len(payload['data'])>=5000 or payload.get('totalRowsWithFilter',len(payload['data']))>len(payload['data']):
            raise ValueError('Auxiliary sample needs pagination')
        auxiliary[endpoint]=[r for r in payload['data'] if start<=timestamp(r['dateTimeUtc'])<end]
        provenance.append(meta)
    expected={iso(start+dt.timedelta(minutes=15*i)) for i in range(4)}
    actual={iso(timestamp(r['dateTimeUtc'])) for r in auxiliary['netPos']}
    if actual!=expected or len(auxiliary['netPos'])!=4:raise ValueError('Incomplete quarter-hour net positions')
    checks=check_positions(bundle['constraints'],auxiliary['netPos'])
    detail=ROOT/'data/jao/core-sample-auxiliary.json.gz'
    detail.write_bytes(gzip.compress(json.dumps(dict(start=iso(start),tables=auxiliary,provenance=provenance)).encode()))
    report=dict(source='JAO Core final domain and published net positions',start=iso(start),end_exclusive=iso(end),
        network_data_check_passed=all(r['passed'] for r in checks),tolerance_mw=.1,
        constraints=summary['rows'],presolved_constraints=sum(r['presolved'] is True for r in bundle['constraints']),
        hubs=summary['hubs'],checks=checks,auxiliary_rows={k:len(v) for k,v in auxiliary.items()},
        bundle_sha256=summary['bundle_sha256'],market_baseline_validated=False,annual_opportunity_meur=None,
        remaining=['Expand historical coverage beyond this hour.',
            'Connect virtual HVDC hubs, long-term-rights inclusion and allocation constraints to dispatch.',
            'Resolve ENTSO-E quantity gaps and generation geography before fitting supply.',
            'Map Nordic virtual hubs and cross-region hybrid connections.'],
        interpretation='Hourly Core domain tested against four published quarter-hour positions. This does not validate generator offers or counterfactual welfare.')
    args.output.write_text(json.dumps(report,allow_nan=False,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
