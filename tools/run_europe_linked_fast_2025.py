"""Same full-Europe order book, exact topology cache and resumable annual timing."""
import argparse
import fcntl
import json
import resource
import time
import numpy as np
from generation_mix_2025 import ROOT,digest
from europe_linked_clearing_2025 import load,daily_book,verify_dispatch,write,PLAN as SOURCE_PLAN
from cached_linked_book import CachedBook
from linked_order_reclearing import reclear

PLAN=ROOT/'config/europe-linked-clearing-fast-2025.json'
OUT=ROOT/'data/bidding-zone-network-2025/europe-linked-clearing-fast-v1'


def run(stage):
    began=time.perf_counter();loaded=load();d,active,p,s,m,c,families,reference,layout_path=loaded;adapter=json.loads(PLAN.read_text());assert adapter['baseline']==d['baseline'];prepared=time.perf_counter()-began
    OUT.mkdir(exist_ok=True);inputs_path=OUT/'inputs.json'
    names=['linked_profile_orders.py','linked_order_reclearing.py','solar_anchor_bids_2025.py','europe_linked_clearing_2025.py','cached_linked_book.py','test_linked_order_reclearing.py','test_cached_linked_book.py']
    files=[PLAN,SOURCE_PLAN,ROOT/d['baseline'],layout_path,*[ROOT/'tools'/n for n in names],*[ROOT/f for f in active['artifacts']]]
    inputs=dict(producer_sha256=digest(__file__),design=d,adapter=adapter,files={str(f.relative_to(ROOT)):digest(f) for f in files},zones=p['zones'],gas_families=len(families),gas_zones=sorted(set(str(s['offer_zones'][ids[0]]) for ids in families)))
    if inputs_path.exists():assert json.loads(inputs_path.read_text())==inputs,'No resume with changed inputs/code'
    else:write(inputs_path,inputs)
    days=d['benchmark_days'] if stage=='benchmark' else np.arange('2025-01-01','2026-01-01',dtype='datetime64[D]').astype(str).tolist()
    cache=CachedBook();rows=[];stage_started=time.perf_counter();reused=0
    for day in days:
        record_path=OUT/(day+'.json')
        if record_path.exists():
            row=json.loads(record_path.read_text());assert row['inputs_sha256']==digest(inputs_path)
            if row['status']!='price_checked_incumbent':raise RuntimeError('Unresolved saved day requires investigation')
            assert digest(ROOT/row['witness'])==row['witness_sha256'];rows.append(row);reused+=1;continue
        if time.perf_counter()-stage_started>adapter['annual_job_wall_seconds']:break
        started=time.perf_counter();building=time.perf_counter();book=daily_book(day,loaded);base,orders,reservations,storage,parts,hours,start=book
        lp=cache.compile(base,orders,reservations,storage);compile_seconds=time.perf_counter()-building
        result=reclear(lp,max_rounds=d['max_rounds'],time_limit=d['per_solve_seconds'],wall_limit=d['per_day_wall_seconds'])
        row={k:v for k,v in result.items() if k!='result'};row|=dict(day=day,compile_seconds=compile_seconds,order_count=len(orders),binary_count=len(lp['integers']),gas_packages=len(parts),storage_packages=len(storage),gas_package_mw=float(sum(part['reserved'].sum(axis=1).max() for part in parts)),eligible_gas_mw=float(m['availability'][start+hours][:,[j for ids in families for j in ids]].sum(axis=1).max()),solved_hours=hours.tolist(),reused_hours=24-len(hours),inputs_sha256=digest(inputs_path),template_builds=cache.builds)
        if result['result'] is not None:
            checking=time.perf_counter();r=result['result'];day_x,injections,physical=verify_dispatch(loaded,book,lp,r);row['verification_seconds']=time.perf_counter()-checking;row['physical']=physical
            path=OUT/(day+'.npz');np.savez_compressed(path,values=r['values'],row_duals=r['row_duals'],ratios=r['ratios'],effective_hourly_dispatch=day_x,storage_injection=injections,hours=start+hours)
            row|=dict(witness=str(path.relative_to(ROOT)),witness_sha256=digest(path))
        row['day_seconds']=time.perf_counter()-started;write(record_path,row);rows.append(row)
        write(OUT/(stage+'-progress.json'),dict(cases=rows,expected_days=len(days),source_preparation_seconds=prepared,stage_wall_seconds=time.perf_counter()-stage_started))
        print(day,row['status'],'seconds',round(row['day_seconds'],3),'rounds',len(row['history']),'matrix builds',cache.builds,flush=True)
        if row['status']!='price_checked_incumbent':break
    complete=len(rows)==len(days) and all(r['status']=='price_checked_incumbent' for r in rows)
    summary=dict(stage=stage,status='complete' if complete else 'partial_or_failed',inputs_sha256=digest(inputs_path),source_preparation_seconds=prepared,stage_wall_seconds=time.perf_counter()-stage_started,process_wall_seconds=time.perf_counter()-began,reused_days=reused,expected_days=len(days),completed_days=sum(r['status']=='price_checked_incumbent' for r in rows),cases=rows,template_builds=cache.builds)
    write(OUT/(stage+'-summary.json'),summary)
    receipt=OUT/(stage+'-invocation-'+str(time.time_ns())+'.json');write(receipt,{k:v for k,v in summary.items() if k!='cases'})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['benchmark','annual']);args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));lock=(OUT.parent/'europe-linked-clearing-fast-v1.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(args.stage)
