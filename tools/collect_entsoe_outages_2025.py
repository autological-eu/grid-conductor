"""Page through 2025 ENTSO-E A80 generation-unit outage publications.

Historical extracts include later revisions; they are not a day-ahead vintage.
Do not sum documents into available MW without unit/revision reconciliation.
"""
import io
import json
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime, timezone

from collect_entsoe_additional_2025 import OUT, NETWORK
from eu_zones import ZONES, EXTERIORS
from flow_tracing import fetch


def months():
    return [(datetime(2025,m,1,tzinfo=timezone.utc),
             datetime(2025+(m==12),m%12+1,1,tzinfo=timezone.utc)) for m in range(1,13)]


def plan():
    zones=json.loads(NETWORK.read_text())['zones']
    codes={z:eic for z,eic,*_ in ZONES+EXTERIORS}
    return [(z,codes[z],a,b) for z in zones if z in codes for a,b in months()]


def collect(item):
    zone,eic,start,end=item
    month=start.strftime('%Y-%m')
    pages=[]
    for offset in range(0,5000,200):
        if shutil.disk_usage(OUT).free<2*1024**3:
            raise RuntimeError('Less than 2 GiB workspace headroom')
        params=dict(documentType='A80',biddingZone_Domain=eic,
                    periodStart=start.strftime('%Y%m%d%H%M'),
                    periodEnd=end.strftime('%Y%m%d%H%M'),offset=offset)
        raw=fetch(params,OUT/'raw')
        if not zipfile.is_zipfile(io.BytesIO(raw)):
            if offset==0:return dict(zone=zone,month=month,status='no_data',documents=0,pages=0)
            return dict(zone=zone,month=month,status='complete',documents=sum(pages),pages=len(pages))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            count=len(archive.namelist())
        if count>200 or count==0:raise ValueError('Unexpected outage page length')
        pages.append(count)
        if count<200:
            return dict(zone=zone,month=month,status='complete',documents=sum(pages),pages=len(pages))
    raise RuntimeError('Outage pagination reached its declared limit')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    journal=OUT/'generation-outage-coverage.jsonl'
    old=[json.loads(line) for line in journal.read_text().splitlines()] if journal.exists() else []
    done={(r['zone'],r['month']) for r in old if r['status'] in ('complete','no_data')}
    todo=[item for item in plan() if (item[0],item[2].strftime('%Y-%m')) not in done]
    print(f'{len(todo)} remaining of {len(plan())} zone-months',flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(collect,item):item for item in todo}
        for future in as_completed(futures):
            zone,_,start,_=futures[future]
            try:row=future.result()
            except Exception as error:
                row=dict(zone=zone,month=start.strftime('%Y-%m'),status='error',reason=str(error)[:180])
            with journal.open('a') as output:output.write(json.dumps(row,sort_keys=True)+'\n')
            print(row['zone'],row['month'],row['status'],row.get('documents',''),flush=True)


if __name__=='__main__':main()
