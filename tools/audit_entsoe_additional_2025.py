"""Replay ENTSO-E 2025 source receipts, documents and outage pagination."""
import hashlib
import io
import json
import zipfile
from collections import Counter
from datetime import datetime
import xml.etree.ElementTree as ET

from collect_entsoe_additional_2025 import OUT, plan as annual_plan
from collect_entsoe_outages_2025 import plan as outage_plan
from collect_entsoe_grid_outages_2025 import plan as grid_plan


def local(root):
    for node in root.iter():node.tag=node.tag.split('}')[-1]
    return root


def source(request):
    key=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()[:24]
    path=OUT/'raw'/(key+'.xml')
    raw=path.read_bytes();meta=json.loads(path.with_suffix('.json').read_text())
    digest=hashlib.sha256(raw).hexdigest()
    if meta['request']!=request or meta['sha256']!=digest:
        raise ValueError('Source receipt mismatch')
    return raw,digest


def annual():
    records=[json.loads(line) for line in (OUT/'annual-input-coverage.jsonl').read_text().splitlines()]
    latest={(r['zone'],r['product']):r for r in records}
    if len(latest)!=len(annual_plan()):raise ValueError('Annual source collection incomplete')
    tally=Counter()
    for zone,product,request in annual_plan():
        row=latest[zone,product]
        raw,digest=source(request)
        root=local(ET.fromstring(raw))
        if row['status']=='ok':
            if row['sha256']!=digest or root.tag!='GL_MarketDocument' or root.findtext('type')!=request['documentType']:
                raise ValueError('Annual document/receipt mismatch')
            series=root.findall('TimeSeries')
            if len(series)!=row['series']:raise ValueError('Annual series count mismatch')
            domain=request.get('in_Domain',request.get('outBiddingZone_Domain'))
            field='outBiddingZone_Domain.mRID' if product=='day_ahead_load_forecast' else 'inBiddingZone_Domain.mRID'
            if any(ts.findtext(field)!=domain for ts in series):
                raise ValueError('Annual zone identity mismatch')
        elif row['status']=='no_data':
            if root.tag!='Acknowledgement_MarketDocument':raise ValueError('Expected no-data acknowledgement')
        else:raise ValueError('Annual source request failed')
        tally[product,row['status']]+=1
    result=dict(status='complete',requests=len(latest),coverage=[dict(product=k[0],status=k[1],count=v)
                                                        for k,v in sorted(tally.items())])
    (OUT/'annual-input-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print('annual',result,flush=True)


def outages():
    records=[json.loads(line) for line in (OUT/'generation-outage-coverage.jsonl').read_text().splitlines()]
    latest={(r['zone'],r['month']):r for r in records}
    if len(latest)!=len(outage_plan()):raise ValueError('Outage collection incomplete')
    total_docs=0;later_created=0;counts=Counter()
    for zone,eic,start,end in outage_plan():
        month=start.strftime('%Y-%m');row=latest[zone,month]
        if row['status'] not in ('complete','no_data'):raise ValueError('Outage source request failed')
        count=0;last_page=0
        for page in range(row['pages']):
            request=dict(documentType='A80',biddingZone_Domain=eic,
                         periodStart=start.strftime('%Y%m%d%H%M'),
                         periodEnd=end.strftime('%Y%m%d%H%M'),offset=200*page)
            raw,_=source(request)
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                last_page=len(archive.namelist());count+=last_page
                for name in archive.namelist():
                    entry=archive.read(name)
                    root=local(ET.fromstring(entry))
                    if root.tag!='Unavailability_MarketDocument' or root.findtext('type')!='A80':
                        raise ValueError('Unexpected outage document')
                    if any(ts.findtext('biddingZone_Domain.mRID')!=eic
                           for ts in root.findall('TimeSeries')):
                        raise ValueError('Outage zone mismatch')
                    created=root.findtext('createdDateTime')
                    if created and datetime.fromisoformat(created.replace('Z','+00:00'))>end:
                        later_created+=1
        if row['status']=='no_data':
            request=dict(documentType='A80',biddingZone_Domain=eic,
                         periodStart=start.strftime('%Y%m%d%H%M'),
                         periodEnd=end.strftime('%Y%m%d%H%M'),offset=0)
            raw,_=source(request)
            if local(ET.fromstring(raw)).tag!='Acknowledgement_MarketDocument':
                raise ValueError('Expected no-data outage acknowledgement')
        if count!=row['documents'] or (last_page==200 and row['status']=='complete'):
            # A complete 200-document page must have been followed by an empty
            # page, but this journal does not record that terminal request.
            request=dict(documentType='A80',biddingZone_Domain=eic,
                         periodStart=start.strftime('%Y%m%d%H%M'),
                         periodEnd=end.strftime('%Y%m%d%H%M'),offset=200*row['pages'])
            if last_page==200 and local(ET.fromstring(source(request)[0])).tag!='Acknowledgement_MarketDocument':
                raise ValueError('Missing terminal outage page')
            if count!=row['documents']:raise ValueError('Outage page count mismatch')
        total_docs+=count;counts[row['status']]+=1
    result=dict(status='complete',zone_months=len(latest),counts=dict(counts),
                document_appearances=total_docs,created_after_query_month_end=later_created,
                caveat='Documents repeat across months and may have later revisions; appearances are not unique outages or unavailable MW.')
    (OUT/'generation-outage-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print('outages',result,flush=True)


def grid():
    records=[json.loads(line) for line in (OUT/'grid-outage-pilot-coverage.jsonl').read_text().splitlines()]
    latest={(r['direction'],r['month']):r for r in records}
    if len(latest)!=len(grid_plan()):raise ValueError('Grid pilot incomplete')
    counts=Counter();total=0
    for a,b,ca,cb,start,end in grid_plan():
        row=latest[a+'>'+b,start.strftime('%Y-%m')]
        if row['status'] not in ('complete','no_data'):raise ValueError('Grid pilot failed')
        found=0
        for page in range(row['pages'] if row['status']=='complete' else 1):
            request=dict(documentType='A78',out_Domain=ca,in_Domain=cb,
                         periodStart=start.strftime('%Y%m%d%H%M'),
                         periodEnd=end.strftime('%Y%m%d%H%M'),offset=200*page)
            raw,_=source(request)
            if row['status']=='no_data':
                if local(ET.fromstring(raw)).tag!='Acknowledgement_MarketDocument':
                    raise ValueError('Expected grid no-data acknowledgement')
                continue
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                found+=len(archive.namelist())
                for name in archive.namelist():
                    root=local(ET.fromstring(archive.read(name)))
                    if root.tag!='Unavailability_MarketDocument' or root.findtext('type')!='A78':
                        raise ValueError('Unexpected grid outage document')
        if found!=row['documents']:raise ValueError('Grid page count mismatch')
        counts[row['status']]+=1;total+=found
    result=dict(status='complete',border_months=len(latest),counts=dict(counts),
                document_appearances=total,
                caveat='Not unique outages or transfer limits; pilot covers four corridors only.')
    (OUT/'grid-outage-pilot-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print('grid',result,flush=True)


if __name__=='__main__':
    import sys
    {'annual':annual,'outages':outages,'grid':grid}[sys.argv[1]]()
