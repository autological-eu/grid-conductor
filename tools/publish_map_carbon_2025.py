"""Coverage-gated production intensity during observed price-separation hours.

No hourly extrapolation, no consumption attribution, no avoided-emission claims.
"""
import datetime as dt,hashlib,json
from pathlib import Path
from carbon_pilot import ROOT,UTC,FACTORS,STORAGE,FACTOR_VERSION,IPCC,iso
from collect_map_carbon_2025 import registry
from monthly_dispatch import save

def period_estimate(rows,indices):
 selected=[rows.get(i) for i in indices];valid=[r for r in selected if r is not None and r['primary_generation_mwh'] is not None]
 energy=sum(r['primary_generation_mwh'] for r in valid)
 mix={k:sum(r['generation_mwh_by_type'].get(k,0) for r in valid) for k in sorted({k for r in valid for k in r['generation_mwh_by_type'] if k not in STORAGE})}
 mapped=sum(v for k,v in mix.items() if k in FACTORS);emissions=sum(v*FACTORS[k][0] for k,v in mix.items() if k in FACTORS)
 unknown=sorted(k for k,v in mix.items() if v>0 and k not in FACTORS)
 return dict(expected_hours=len(indices),complete_generation_hours=len(valid),
  full_lifecycle_gco2e_kwh=emissions/energy if energy and len(valid)==len(indices) and not unknown else None,
  mapped_subset_gco2e_kwh=emissions/mapped if mapped else None,
  mapped_generation_share=mapped/energy if energy else None,positive_unmapped_types=unknown,
  generation_complete_hours_mwh=energy)

def publish():
 folder=ROOT/'data/carbon-pilot/map-2025';areas=registry();bank={};receipts={};zones={};start=dt.datetime(2025,1,1,tzinfo=UTC)
 for zone,area in areas.items():
  rows={};source=[]
  for month in range(1,13):
   path=folder/zone/f'{month:02d}.json';receipt=folder/zone/f'{month:02d}.receipt.json'
   if not path.exists() or not receipt.exists():continue
   r=json.loads(receipt.read_text())
   if r['eic']!=area['eic'] or r['sha256']!=hashlib.sha256(path.read_bytes()).hexdigest():raise ValueError('Generation source mismatch')
   for row in json.loads(path.read_text()):
    if row['factor_version']!=FACTOR_VERSION:raise ValueError('Factor version mismatch')
    i=int((dt.datetime.fromisoformat(row['start'].replace('Z','+00:00'))-start).total_seconds()/3600)
    if not 0<=i<8760 or row['start']!=iso(start+dt.timedelta(hours=i)) or i in rows:raise ValueError('Hourly identity mismatch')
    rows[i]=row
   source.append(r)
  bank[zone]=rows;receipts[zone]=source
  zones[zone]=dict(geographic_scope=area['scope'],collected_months=len(source),**period_estimate(rows,range(8760)))
 targets=json.loads((ROOT/'public/research/entsoe-fast-targets.json').read_text())['targets']
 pairs=sorted({tuple(sorted(t['border'].split('>'))) for t in targets});borders={}
 for a,b in pairs:
  if a not in areas or b not in areas:continue
  pa=json.loads((ROOT/f'public/research/zone-prices-2025/{a}.json').read_text());pb=json.loads((ROOT/f'public/research/zone-prices-2025/{b}.json').read_text())
  if len(pa)!=8760 or len(pb)!=8760:raise ValueError('Price chronology length mismatch')
  indices=[i for i,(x,y) in enumerate(zip(pa,pb)) if x is not None and y is not None and abs(x-y)>5]
  borders[a+'>'+b]=dict(hours_with_spread_gt_5=len(indices),zones={z:dict(geographic_scope=areas[z]['scope'],**period_estimate(bank[z],indices)) for z in (a,b)})
 output=ROOT/'public/research/production-carbon-2025';output.mkdir(exist_ok=True)
 hourly=output/'hourly';hourly.mkdir(exist_ok=True);hourly_files={}
 for zone in areas:
  values=[]
  for i in range(8760):
   item=period_estimate(bank[zone],[i])
   values.append([item['full_lifecycle_gco2e_kwh'],item['mapped_subset_gco2e_kwh'],item['mapped_generation_share']])
  raw=(json.dumps(values,allow_nan=False,separators=(',',':'))+'\n').encode()
  (hourly/f'{zone}.json').write_bytes(raw)
  hourly_files[zone]=dict(path=f'research/production-carbon-2025/hourly/{zone}.json',sha256=hashlib.sha256(raw).hexdigest(),hours=8760)

 save(output/'map-summary.json',dict(schema_version=1,year=2025,unit='gCO2e/kWh',basis='production lifecycle; not consumption or avoided emissions',
  selection='joint observed hourly prices, absolute spread strictly greater than 5 EUR/MWh; not proof of physical congestion',
  publisher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),price_sha256={z:hashlib.sha256((ROOT/f'public/research/zone-prices-2025/{z}.json').read_bytes()).hexdigest() for z in areas},
  hourly_files=hourly_files,hourly_start='2025-01-01T00:00:00Z',hourly_columns=['reported_generation_intensity_gco2e_kwh','mapped_subset_intensity_gco2e_kwh','mapped_generation_share'],
  factor_version=FACTOR_VERSION,factor_source=IPCC,factors=FACTORS,zones=zones,borders=borders,provenance=receipts,
  limitations=['Uncollected/missing generation never filled','Mapped subset is not full-zone intensity','Reported categories alone do not prove whole-fleet completeness','Generic factor proxies; biomass/CHP treatment remains unresolved','DE-LU uses labelled German national proxy, not DE-LU generation']))
 print('Prepared map carbon coverage for',len(zones),'zones and',len(borders),'borders')
if __name__=='__main__':publish()
