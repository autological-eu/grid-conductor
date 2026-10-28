"""Bounded A78 grid-outage source pilot for four important 2025 corridors.

Documents are diagnostics only; a notice is not an hourly transfer limit.
"""
import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed

from collect_entsoe_additional_2025 import OUT
from collect_entsoe_outages_2025 import months
from eu_zones import ZONES, EXTERIORS
from flow_tracing import fetch

PAIRS=(('FR','BE'),('DE-LU','DK1'),('NO2','DK1'),('SE2','SE3'))


def plan():
    codes={z:eic for z,eic,*_ in ZONES+EXTERIORS}
    return [(a,b,codes[a],codes[b],start,end)
            for u,v in PAIRS for a,b in ((u,v),(v,u)) for start,end in months()]


def collect(item):
    a,b,ca,cb,start,end=item
    counts=[]
    for offset in range(0,5000,200):
        request=dict(documentType='A78',out_Domain=ca,in_Domain=cb,
                     periodStart=start.strftime('%Y%m%d%H%M'),
                     periodEnd=end.strftime('%Y%m%d%H%M'),offset=offset)
        raw=fetch(request,OUT/'raw')
        if not zipfile.is_zipfile(io.BytesIO(raw)):
            return dict(direction=a+'>'+b,month=start.strftime('%Y-%m'),
                        status='no_data' if not counts else 'complete',
                        documents=sum(counts),pages=len(counts))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:count=len(archive.namelist())
        if count>200 or count==0:raise ValueError('Unexpected grid-outage page length')
        counts.append(count)
        if count<200:
            return dict(direction=a+'>'+b,month=start.strftime('%Y-%m'),
                        status='complete',documents=sum(counts),pages=len(counts))
    raise RuntimeError('Grid-outage pagination reached its limit')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    journal=OUT/'grid-outage-pilot-coverage.jsonl'
    old=[json.loads(line) for line in journal.read_text().splitlines()] if journal.exists() else []
    done={(r['direction'],r['month']) for r in old if r['status'] in ('complete','no_data')}
    todo=[item for item in plan() if (item[0]+'>'+item[1],item[4].strftime('%Y-%m')) not in done]
    print(f'{len(todo)} remaining of {len(plan())} border-months',flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(collect,item):item for item in todo}
        for future in as_completed(futures):
            a,b,_,_,start,_=futures[future]
            try:row=future.result()
            except Exception as error:
                row=dict(direction=a+'>'+b,month=start.strftime('%Y-%m'),
                         status='error',reason=str(error)[:180])
            with journal.open('a') as output:output.write(json.dumps(row,sort_keys=True)+'\n')
            print(row['direction'],row['month'],row['status'],row.get('documents',''),flush=True)


if __name__=='__main__':main()
