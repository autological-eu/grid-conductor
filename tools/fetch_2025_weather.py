"""Fetch public 2025 ERA5 weather at audited archive-node coordinates.

This publishes a source-readiness audit, not generation availability or a validated
2025 model. No dispatch outputs are converted into availability.
"""
import hashlib,json,urllib.parse,urllib.request
from pathlib import Path
import numpy as np
import pandas as pd
import pypsa
from fetch_pypsa_benchmark import fetch
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'data/pypsa-eur/online-source-audit'

def main():
    n=pypsa.Network(fetch());nodes=list(n.buses.index)
    parameters=dict(latitude=','.join(f'{v:.6f}' for v in n.buses.y),longitude=','.join(f'{v:.6f}' for v in n.buses.x),start_date='2025-01-01',end_date='2025-12-31',hourly='wind_speed_100m,shortwave_radiation,temperature_2m',models='era5',timezone='UTC',wind_speed_unit='ms')
    url='https://archive-api.open-meteo.com/v1/archive?'+urllib.parse.urlencode(parameters)
    path=CACHE/'era5-node-weather-2025.json'
    if not path.exists():
        with urllib.request.urlopen(url,timeout=180) as response:payload=response.read()
        parsed=json.loads(payload)
        if not isinstance(parsed,list) or len(parsed)!=len(nodes):raise ValueError('Incomplete location response')
        path.write_bytes(payload)
    raw=path.read_bytes();results=json.loads(raw)
    expected=pd.date_range('2025-01-01',periods=8760,freq='h');rows=[]
    units={'wind_speed_100m':'m/s','shortwave_radiation':'W/m²','temperature_2m':'°C'}
    for identity,result in zip(nodes,results):
        stamps=pd.to_datetime(result['hourly']['time'])
        if not stamps.equals(expected) or result['utc_offset_seconds']!=0:raise ValueError('Incomplete UTC weather year')
        if any(result['hourly_units'].get(k)!=v for k,v in units.items()):raise ValueError('Unexpected weather units')
        for key in units:
            values=np.asarray(result['hourly'][key],dtype=float)
            if len(values)!=8760 or not np.isfinite(values).all():raise ValueError(f'Missing weather {identity}/{key}')
        rows.append(dict(node=identity,country=n.buses.loc[identity,'country'],requested_latitude=float(n.buses.loc[identity,'y']),requested_longitude=float(n.buses.loc[identity,'x']),returned_latitude=result['latitude'],returned_longitude=result['longitude'],hours=8760))
    report=dict(status='2025_weather_source_ready_model_not_assembled',year=2025,source_url=url,source_sha256=hashlib.sha256(raw).hexdigest(),source_bytes=len(raw),variables=units,nodes=rows,license='Weather service: Open-Meteo CC BY 4.0; ERA5: Copernicus Climate Change Service / ECMWF',limitations=['Weather at coarse archive-node centroids is not capacity-weighted wind/solar generation availability.','Weather-to-power conversion, 2025 installed fleet/costs, hydro inflow/boundaries and complete demand/network data remain model gates.','Archive node coordinates are a declared sampling geography, not a 2025 physical topology or SE4 bidding-zone mapping.'],generation_availability_published=False,historical_validation='not_performed')
    output=ROOT/'public/research/2025-weather-source-audit.json';output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['status','year','source_bytes','generation_availability_published']}))
if __name__=='__main__':main()
