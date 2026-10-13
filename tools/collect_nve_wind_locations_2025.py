"""Snapshot public NVE operating-site geometry for a later weather correction.

No model inputs are changed. GIS site points are not individual turbine positions;
current operating-site coverage does not prove complete historical 2025 coverage.
"""
import argparse,datetime as dt,hashlib,json,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def collect(out):
    params=dict(where='1=1',outFields='anleggsnr,anleggnavn,effekt_mw_idrift,forsteidriftdato,utavdriftdato,objektstatus',
                outSR='4326',f='geojson',returnGeometry='true')
    url='https://kart.nve.no/enterprise/rest/services/Vindkraft2/MapServer/0/query?'+urllib.parse.urlencode(params)
    with urllib.request.urlopen(url,timeout=60) as response:raw=response.read()
    data=json.loads(raw)
    if data.get('error') or data.get('exceededTransferLimit'):raise ValueError('Incomplete GIS response')
    if data.get('type')!='FeatureCollection':raise ValueError('Expected GeoJSON')
    out.mkdir(parents=True,exist_ok=False);(out/'sites.geojson').write_bytes(raw)
    receipt=dict(url=url,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),retrieved_at=dt.datetime.now(dt.timezone.utc).isoformat())
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    path=ROOT/'data/bidding-zone-source-audit-2025/nve-wind.json'
    registry=json.loads(path.read_text());meta=json.loads(path.with_suffix('.meta.json').read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==meta['sha256']
    features={}
    for f in data['features']:
        key=str(f['properties']['anleggsnr']);features.setdefault(key,[]).append(f)
    matches=[];missing=[];ambiguous=[]
    for farm in registry:
        key=str(farm['AnleggsNr']);found=features.get(key,[])
        if not found:missing.append(dict(name=farm['Navn'],plant_id=key));continue
        if len(found)!=1:ambiguous.append(dict(name=farm['Navn'],plant_id=key,records=len(found)));continue
        point=found[0]['geometry']
        if not point or point['type']!='Point':raise ValueError('Expected operating-site point')
        lon,lat=point['coordinates'][:2]
        if not (-180<=lon<=180 and -90<=lat<=90):raise ValueError('Invalid WGS84 coordinate')
        matches.append(dict(name=farm['Navn'],registry_farm_id=farm['VindkraftAnleggId'],plant_id=key,zone='NO'+str(farm['ElspotomraadeNummer']),lon=lon,lat=lat,
            current_registry_mw=farm['InstallertEffekt_MW']))
    result=dict(status='source_location_inventory_only',receipt=receipt,registry_sha256=meta['sha256'],
        registry_farms=len(registry),gis_features=len(data['features']),matches=matches,missing=missing,ambiguous=ambiguous,
        limits=['Current operating GIS site points, not turbine coordinates or complete historical 2025 fleet.',
                'Registry extensions may share a plant ID and GIS point; keep separate turbine batches and do not duplicate them.',
                'No weather conversion, generation fitting, model-input substitution or baseline promotion.'])
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:len(result[k]) for k in ['matches','missing','ambiguous']},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();collect(a.out)
