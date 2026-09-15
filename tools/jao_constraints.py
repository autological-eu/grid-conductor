"""JAO final flow-based domains: paginated, hashed, UTC-aligned evidence.

JAO_API_TOKEN is read only from the environment. Raw compressed responses and
normalised constraints stay under ignored data/jao, never in the browser bundle.
"""
import argparse
import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
from carbon_pilot import ROOT, timestamp, iso

BASE='https://publicationtool.jao.eu'
ENDPOINTS={'finalComputation','bexRestrictions','allocationConstraint','lta','ltn','netPos','activeFbConstraints','alphaFactor'}


def month_summary(region,start,end,days):
    # Publication granularity verified against January 2026 API responses.
    minutes=15 if region=='nordic' else 60
    stamps={t for record in days for t in record.get('timestamps',{})}
    hours=int((end-start).total_seconds()/3600)
    expected={iso(start+dt.timedelta(minutes=minutes*i)) for i in range(hours*60//minutes)}
    complete_hours=sum(all(iso(start+dt.timedelta(hours=h,minutes=m)) in stamps for m in range(0,60,minutes)) for h in range(hours))
    return dict(region=region,month=start.strftime('%Y-%m'),published_hour_coverage=complete_hours/hours,
        published_interval_coverage=len(stamps&expected)/len(expected),publication_interval_minutes=minutes,
        expected_hours=hours,expected_intervals=len(expected),missing_intervals=sorted(expected-stamps),
        unexpected_timestamps=sorted(stamps-expected),constraint_rows=sum(r.get('rows',0) for r in days),
        days=days,market_baseline_validated=False)


def page(region, start, end, skip, take, directory, endpoint='finalComputation', presolved=False):
    if region not in {'core','nordic'}:raise ValueError('Unknown JAO region')
    if endpoint not in ENDPOINTS:raise ValueError('Unknown JAO endpoint')
    params=dict(FromUtc=iso(start),ToUtc=iso(end),skip=skip,take=take)
    if presolved:params['filter']=json.dumps(dict(presolved=True,cnecName='',tso=[],hubFrom=[],hubTo=[],contingency=''))
    if region=='nordic':
        params['filter']=json.dumps(dict(nonRedundant=True if presolved else None,cnecName='',tso=[],biddingZoneFrom=[],biddingZoneTo=[],contingency=''))
    url=f'{BASE}/{region}/api/data/{endpoint}?'+urllib.parse.urlencode(params)
    key=hashlib.sha256(url.encode()).hexdigest()
    raw_path=directory/(key+'.json.gz');meta_path=directory/(key+'.meta.json')
    if raw_path.exists() and meta_path.exists():
        raw=gzip.decompress(raw_path.read_bytes());meta=json.loads(meta_path.read_text())
        if meta['url']!=url or meta['sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('JAO cache mismatch')
        return json.loads(raw),meta
    token=os.environ.get('JAO_API_TOKEN')
    headers={'Accept':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=60) as response:
                raw=response.read()
            break
        except urllib.error.HTTPError as error:
            if error.code not in {429,500,502,503,504} or attempt==2:
                raise ValueError(f'JAO {region} HTTP {error.code}') from None
            time.sleep(2**attempt)
        except (urllib.error.URLError,TimeoutError):
            if attempt==2:raise ValueError('JAO network failure') from None
            time.sleep(2**attempt)
    payload=json.loads(raw)
    if payload.get('rejected') or not isinstance(payload.get('data'),list):raise ValueError('JAO rejected or malformed response')
    meta=dict(url=url,sha256=hashlib.sha256(raw).hexdigest(),retrieved_at=iso(dt.datetime.now(dt.timezone.utc)))
    directory.mkdir(parents=True,exist_ok=True)
    raw_path.write_bytes(gzip.compress(raw));meta_path.write_text(json.dumps(meta))
    return payload,meta


def normalize(rows,start,end):
    result=[];seen={}
    for row in rows:
        instant=timestamp(row['dateTimeUtc'])
        if not start<=instant<end:continue
        identity=str(row['id'])
        if identity in seen:
            if row!=seen[identity]:raise ValueError('Conflicting JAO rows')
            continue
        seen[identity]=row
        ram=row.get('ram')
        coefficients={k[5:]:v for k,v in row.items() if k.startswith('ptdf_') and v is not None}
        if not coefficients or not isinstance(ram,(int,float)) or not math.isfinite(ram):raise ValueError('Missing RAM/PTDF')
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in coefficients.values()):raise ValueError('Invalid PTDF')
        result.append(dict(id=identity,start=iso(instant),ram_mw=ram,ptdf=coefficients,
            cne_eic=row.get('cneEic'),cne_name=row.get('cneName'),direction=row.get('direction'),
            contingency=row.get('contName'),presolved=row.get('presolved',row.get('nonRedundant')),
            hub_from=row.get('hubFrom',row.get('biddingZoneFrom')),hub_to=row.get('hubTo',row.get('biddingZoneTo'))))
    return result


def collect(region,start,end,directory=ROOT/'data/jao',presolved=False):
    if end<=start or (end-start).total_seconds()>86400:raise ValueError('Collect chunks of at most one day')
    rows=[];provenance=[];skip=0;total=None;modified=None
    while True:
        payload,meta=page(region,start,end,skip,5000,directory/'raw',presolved=presolved)
        if presolved and (payload.get('appliedFilter') or {}).get('nonRedundant' if region=='nordic' else 'presolved') is not True:
            raise ValueError('JAO did not apply the presolved filter')
        reported=payload.get('totalRowsWithFilter')
        if not isinstance(reported,int) or reported<0:raise ValueError('Missing JAO pagination count')
        if total is not None and reported!=total:raise ValueError('JAO row count changed during pagination; retry')
        if payload.get('skip')!=skip:raise ValueError('JAO ignored pagination offset')
        # lastModifiedOn is page-dependent, not a whole-result revision token.
        total=reported;modified=max(modified or '',payload.get('lastModifiedOn') or '')
        batch=payload['data']
        if not batch and skip<total:raise ValueError('Truncated JAO response')
        rows.extend(batch);provenance.append(meta);skip+=len(batch)
        if skip>=total:break
    if len(rows)!=total or len({row['id'] for row in rows})!=total:
        raise ValueError('Overlapping or incomplete JAO pagination')
    constraints=normalize(rows,start,end)
    if presolved and any(row['presolved'] is not True for row in constraints):raise ValueError('Unexpected redundant rows')
    slots=collections.Counter(r['start'] for r in constraints)
    hubs=sorted({h for r in constraints for h in r['ptdf']})
    bundle=dict(source='JAO finalComputation',region=region,start=iso(start),end_exclusive=iso(end),
        constraints=constraints,provenance=provenance,last_modified=modified,presolved_only=presolved,
        market_domain_complete=False,
        limitations=['Final flow-based domain only; LTA inclusion, allocation restrictions and HVDC hub coupling are not yet reconstructed.',
            'PTDF hubs are retained exactly. Virtual hubs must not be dropped or silently set to zero.',
            'Published time steps are preserved; no assumption that a row lasts a whole hour.'])
    directory.mkdir(parents=True,exist_ok=True)
    name=f"{region}-{start.strftime('%Y%m%dT%H%M')}-{end.strftime('%Y%m%dT%H%M')}"
    if presolved:name+='-presolved'
    path=directory/(name+'.json.gz')
    raw=json.dumps(bundle,allow_nan=False).encode();path.write_bytes(gzip.compress(raw))
    return dict(region=region,status='downloaded_not_market_complete',start=iso(start),end_exclusive=iso(end),
        rows=len(constraints),timestamps=dict(sorted(slots.items())),hubs=hubs,
        presolved_only=presolved,
        bundle_path=str(path.relative_to(ROOT)),bundle_sha256=hashlib.sha256(raw).hexdigest(),
        annual_opportunity_meur=None,limitations=bundle['limitations'])


def collect_day(region,start):
    try:return collect(region,start,start+dt.timedelta(days=1),presolved=True)
    except ValueError as error:
        original_error=str(error)
    chunks=[]
    for hour in range(0,24,6):
        instant=start+dt.timedelta(hours=hour)
        try:chunks.append(collect(region,instant,instant+dt.timedelta(hours=6),presolved=True))
        except ValueError as error:chunks.append(dict(start=iso(instant),status='unavailable',error=str(error)))
    return dict(start=iso(start),end_exclusive=iso(start+dt.timedelta(days=1)),region=region,
        status='downloaded_not_market_complete' if all('rows' in r for r in chunks) else 'partial',
        rows=sum(r.get('rows',0) for r in chunks),
        timestamps={t:n for r in chunks for t,n in r.get('timestamps',{}).items()},
        original_daily_error=original_error,chunks=chunks)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start',default='2026-01-01T00:00:00Z');p.add_argument('--hours',type=int,default=1)
    p.add_argument('--regions',nargs='+',choices=['core','nordic'],default=['core','nordic'])
    p.add_argument('--output',type=Path,default=ROOT/'public/research/jao-coverage.json')
    p.add_argument('--month',help='Collect a month in resumable daily presolved-domain chunks')
    args=p.parse_args();start=timestamp(args.start);end=start+dt.timedelta(hours=args.hours)
    reports=[]
    if args.month:
        start=dt.datetime.strptime(args.month,'%Y-%m').replace(tzinfo=dt.timezone.utc)
        end=(start.replace(day=28)+dt.timedelta(days=4)).replace(day=1)
        for region in args.regions:
            day=start;days=[]
            while day<end:
                try:days.append(collect_day(region,day))
                except ValueError as error:days.append(dict(start=iso(day),status='unavailable',error=str(error)))
                print(region,iso(day),days[-1]['status'],flush=True)
                day+=dt.timedelta(days=1)
            reports.append(month_summary(region,start,end,days))
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(dict(source='JAO',regions=reports),indent=2,allow_nan=False))
        print('Monthly coverage report:',args.output)
        return
    for region in args.regions:
        try:reports.append(collect(region,start,end))
        except ValueError as error:reports.append(dict(region=region,status='unavailable',error=str(error)))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(dict(source='JAO',regions=reports),indent=2,allow_nan=False))
    print(json.dumps(reports,indent=2))


if __name__=='__main__':main()
