"""Compile source-covered 2025 A69/A65 forecasts to hourly UTC MW arrays.

Requires all sub-hour slots for an hourly mean; unknown hours remain NaN.
This is observational evidence, not renewable availability or a vintage replay.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from collect_entsoe_additional_2025 import OUT,plan

START=datetime(2025,1,1,tzinfo=timezone.utc)
SLOTS=365*24*4
RESOLUTIONS={'PT15M':1,'PT30M':2,'PT60M':4}


def decode(raw,document_type):
    root=ET.fromstring(raw)
    for element in root.iter():element.tag=element.tag.split('}')[-1]
    if root.tag!='GL_MarketDocument' or root.findtext('type')!=document_type:
        raise ValueError('Unexpected ENTSO-E forecast document')
    output={}
    for series in root.findall('TimeSeries'):
        if series.findtext('quantity_Measure_Unit.name')!='MAW':
            raise ValueError('Forecast unit is not MW')
        psr=series.findtext('MktPSRType/psrType') if document_type=='A69' else 'load'
        key=(series.findtext('businessType'),psr)
        curve=series.findtext('curveType')
        if curve not in ('A01','A03'):raise ValueError('Unsupported forecast curve')
        values=output.setdefault(key,np.full(SLOTS,np.nan))
        for period in series.findall('Period'):
            begin=datetime.fromisoformat(period.findtext('timeInterval/start').replace('Z','+00:00'))
            end=datetime.fromisoformat(period.findtext('timeInterval/end').replace('Z','+00:00'))
            width=RESOLUTIONS.get(period.findtext('resolution'))
            if width is None:raise ValueError('Unsupported forecast resolution')
            count=(end-begin)/timedelta(minutes=15*width)
            if count<=0 or int(count)!=count:raise ValueError('Unaligned forecast period')
            points={int(p.findtext('position')):float(p.findtext('quantity'))
                    for p in period.findall('Point')}
            prior=None
            for position in range(1,int(count)+1):
                if position in points:prior=points[position]
                number=prior if curve=='A03' else points.get(position)
                if number is None:continue
                instant=begin+(position-1)*timedelta(minutes=15*width)
                index=(instant-START)/timedelta(minutes=15)
                if int(index)!=index:raise ValueError('Unaligned forecast timestamp')
                for q in range(width):
                    slot=int(index)+q
                    if 0<=slot<SLOTS:
                        if np.isfinite(values[slot]) and values[slot]!=number:
                            raise ValueError('Conflicting forecast revisions/intervals')
                        values[slot]=number
    return output


def hourly(values):
    blocks=values.reshape(8760,4)
    return np.where(np.isfinite(blocks).all(axis=1),blocks.mean(axis=1),np.nan)


def main():
    folder=OUT/'hourly-forecasts';folder.mkdir(exist_ok=True)
    latest={}
    for line in (OUT/'annual-input-coverage.jsonl').read_text().splitlines():
        record=json.loads(line);latest[record['zone'],record['product']]=record
    completed=0
    for zone,product,request in plan():
        if product not in ('day_ahead_renewable_forecast','day_ahead_load_forecast'):
            continue
        record=latest.get((zone,product))
        if not record or record['status']!='ok':continue
        key=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()[:24]
        raw=(OUT/'raw'/(key+'.xml')).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=record['sha256']:
            raise ValueError('Forecast source hash changed')
        series=decode(raw,request['documentType'])
        values={f'{business}_{psr}':hourly(v) for (business,psr),v in series.items()}
        out=folder/(zone+'-'+product+'.npz')
        np.savez_compressed(out,**values)
        receipt=dict(zone=zone,product=product,source_sha256=record['sha256'],
                     series={k:dict(hours=int(np.isfinite(v).sum()),
                                    minimum=float(np.nanmin(v)) if np.isfinite(v).any() else None,
                                    maximum=float(np.nanmax(v)) if np.isfinite(v).any() else None)
                             for k,v in values.items()})
        out.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n')
        completed+=1
    print('compiled',completed,'source-covered zone-products',flush=True)


if __name__=='__main__':main()
