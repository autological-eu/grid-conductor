"""Resumable monthly ENTSO-E collection and coverage-gated annual accounting.

No extrapolation: incomplete generation or positive unmapped fuels block the
full annual estimate. Outputs are offline research inputs, not app validation.
"""
import argparse,datetime as dt,hashlib,json,os,sys
from pathlib import Path
from carbon_pilot import ROOT,UTC,AREAS,FACTORS,FACTOR_VERSION,STORAGE,download,parse_generation,calculate,iso

def aggregate(rows,expected_hours):
    times=[r['start'] for r in rows]
    if len(times)!=len(set(times)):raise ValueError('Duplicate zone hours')
    complete=[r for r in rows if r['primary_generation_mwh'] is not None]
    energy=sum(r['primary_generation_mwh'] for r in complete)
    supported_rows=[r for r in complete if r['carbon_intensity'] is not None and not any(v>0 and k not in FACTORS and k not in STORAGE for k,v in r['generation_mwh_by_type'].items())]
    emissions=sum(r['primary_generation_mwh']*r['carbon_intensity'] for r in supported_rows)
    supported=len(supported_rows)
    mix={k:sum(r['generation_mwh_by_type'].get(k,0) for r in complete) for k in sorted({k for r in complete for k in r['generation_mwh_by_type'] if k not in STORAGE})}
    return dict(expected_hours=expected_hours,available_rows=len(rows),complete_generation_hours=len(complete),full_factor_hours=supported,
        complete_hour_generation_mwh=energy,generation_mix_complete_hours_mwh=mix,
        annual_lifecycle_gco2e_kwh=emissions/energy if energy and len(complete)==expected_hours and supported==expected_hours else None,
        partial_period_lifecycle_gco2e_kwh=emissions/energy if energy and supported==len(complete) else None,
        missing_generation_hours=expected_hours-len(complete),
        positive_unmapped_types=sorted({k for r in complete for k,v in r['generation_mwh_by_type'].items() if v>0 and k not in FACTORS and k not in STORAGE}))

def run(args):
    output=args.output;output.mkdir(parents=True,exist_ok=True)
    all_rows=[];sources={}
    for month in range(1,13):
        start=dt.datetime(args.year,month,1,tzinfo=UTC)
        end=dt.datetime(args.year+1,1,1,tzinfo=UTC) if month==12 else dt.datetime(args.year,month+1,1,tzinfo=UTC)
        folder=output/f'{args.year}-{month:02d}';folder.mkdir(exist_ok=True)
        rows=[];provenance={}
        for zone in args.zones:
            raw,metadata=download(zone,start,end,output/'raw')
            rows.extend(calculate(parse_generation(raw,AREAS[zone]),zone,start,end,1500))
            provenance[zone]=metadata
        data=''.join(json.dumps(r,allow_nan=False)+'\n' for r in rows)
        (folder/'hourly.jsonl').write_text(data)
        summary=dict(start=iso(start),end_exclusive=iso(end),source=provenance,factor_version=FACTOR_VERSION,
            hourly_sha256=hashlib.sha256(data.encode()).hexdigest(),zones={z:aggregate([r for r in rows if r['zone']==z],int((end-start).total_seconds()/3600)) for z in args.zones})
        (folder/'annual-collection-summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
        all_rows.extend(rows);sources[f'{month:02d}']=summary
        (output/'annual-status.json').write_text(json.dumps(dict(year=args.year,verified_collected_months=month,pid=os.getpid(),status='collecting' if month<12 else 'collected'),indent=2)+'\n')
        print(f'Collected and parsed month {month}/12',flush=True)
    start=dt.datetime(args.year,1,1,tzinfo=UTC);end=dt.datetime(args.year+1,1,1,tzinfo=UTC)
    expected=int((end-start).total_seconds()/3600)
    for z in args.zones:
        times=sorted(r['start'] for r in all_rows if r['zone']==z)
        if times!=[iso(start+dt.timedelta(hours=i)) for i in range(expected)]:raise ValueError('Annual chronology mismatch')
    annual=dict(year=args.year,start=iso(start),end_exclusive=iso(end),factor_version=FACTOR_VERSION,
        scope='Reported production only; absent categories do not prove zero generation; not consumption or marginal intensity',
        monthly=sources,zones={z:aggregate([r for r in all_rows if r['zone']==z],expected) for z in args.zones})
    (output/f'annual-{args.year}.json').write_text(json.dumps(annual,indent=2,allow_nan=False)+'\n')
    print(json.dumps(annual['zones'],indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--year',type=int,default=2025);p.add_argument('--zones',nargs='+',choices=AREAS,default=['FR','DK-DK1','DK-DK2']);p.add_argument('--output',type=Path,default=ROOT/'data/carbon-pilot/entsoe')
    args=p.parse_args();run(args)
