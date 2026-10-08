"""Bounded historical JAO probes; no annual coverage or dispatch-readiness claim."""
import concurrent.futures
import datetime as dt
import gzip,json
from pathlib import Path
from jao_constraints import collect,page
from hourly_renewable_estimates import digest
from carbon_pilot import ROOT,iso,timestamp
from audit_jao_sample import check_positions

STARTS=['2025-01-15T12:00:00Z','2025-07-15T12:00:00Z','2025-12-15T12:00:00Z']
DIRECTORY=ROOT/'data/jao/probe-2025-v1'

def probe(region,text):
    start=timestamp(text);end=start+dt.timedelta(hours=1)
    result=dict(region=region,start=iso(start),end_exclusive=iso(end),market_domain_complete=False)
    try:
        summary=collect(region,start,end,DIRECTORY,presolved=True)
        result.update(summary)
        if not summary['rows']:raise ValueError('No final-domain constraints returned')
        bundle=json.loads(gzip.decompress((ROOT/summary['bundle_path']).read_bytes()))
        auxiliary={};receipts=[]
        for endpoint in ['netPos','allocationConstraint','bexRestrictions','lta','ltn']:
            try:
                payload,meta=page(region,start,end,0,5000,DIRECTORY/'raw',endpoint)
                data=payload['data']
                if payload.get('totalRowsWithFilter',len(data))>len(data):raise ValueError('Auxiliary pagination incomplete')
                auxiliary[endpoint]=dict(rows=len(data),sha256=meta['sha256'])
                receipts.append(meta)
                if endpoint=='netPos':
                    # Match exact published intervals; only the legacy hourly Core
                    # domain is applied across its own one-hour probe window.
                    checks=[];slots=sorted(summary['timestamps'])
                    for position in data:
                        instant=timestamp(position['dateTimeUtc'])
                        if not start<=instant<end:continue
                        slot=iso(instant)
                        if slot not in slots and region=='core' and slots==[iso(start)]:slot=iso(start)
                        constraints=[r for r in bundle['constraints'] if r['start']==slot]
                        if not constraints:raise ValueError('No matching domain interval for net position')
                        checks.extend(check_positions(constraints,[position]))
                    result['position_checks']=checks
                    result['positions_checked']=len(checks)
                    result['position_data_check_passed']=bool(checks) and all(c['passed'] for c in checks)
                    result['position_check_status']='not_available' if not checks else ('passed' if all(c['passed'] for c in checks) else 'failed_simple_ptdf_ram_check')
            except (ValueError,KeyError) as e:
                auxiliary[endpoint]=dict(status='unavailable_or_unverified',reason=str(e))
        result['auxiliary']=auxiliary
        result['auxiliary_request_receipts']=receipts
    except (ValueError,KeyError) as e:
        result.update(status='failed_or_unavailable',reason=str(e))
    return result

if __name__=='__main__':
    output=ROOT/'public/research/jao-2025-probes.json'
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(probe,region,start) for region in ['core','nordic'] for start in STARTS]
        rows=[f.result() for f in futures]
    report=dict(status='historical_samples_not_annual_coverage',samples=rows,
                producer_sha256=digest(__file__),collector_sha256=digest(Path(__file__).with_name('jao_constraints.py')),
                limitations=['Three fixed hours per region cannot establish 8760-hour coverage.',
                             'Presolved/nonredundant final-domain rows alone do not reconstruct full allocation or LTA inclusion.',
                             'Virtual hubs retained; no dispatch compilation or counterfactual welfare claim.',
                             'Core single-hour rows may be checked against positions within that hour; finer rows match exact timestamps.'])
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    for r in rows:print(r['region'],r['start'],r['status'],r.get('rows'),r.get('positions_checked'),r.get('position_data_check_passed'),r.get('reason',''))
