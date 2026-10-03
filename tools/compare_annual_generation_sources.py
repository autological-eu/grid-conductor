"""FR cross-provider matched-hour consistency check, not independent validation."""
import datetime as dt,json
from pathlib import Path
from carbon_pilot import ROOT,UTC,iso
MAPPING={'Nuclear':'B14','Hydro Run-of-River':'B11','Biomass':'B01','Fossil hard coal':'B05','Fossil oil':'B06','Fossil gas':'B04','Hydro water reservoir':'B12','Waste':'B17','Wind offshore':'B18','Wind onshore':'B19','Solar':'B16'}
def compare():
 root=ROOT/'data/carbon-pilot';other=json.loads((root/'annual-independent/fr-energy-charts.json').read_text())
 series={MAPPING[x['name']]:dict(zip([iso(dt.datetime.fromtimestamp(t,UTC)) for t in other['unix_seconds']],x['data'])) for x in other['production_types'] if x['name'] in MAPPING}
 comparisons=[]
 for month in range(1,13):
  rows=[json.loads(x) for x in (root/f'entsoe/2025-{month:02d}/hourly.jsonl').read_text().splitlines()];rows=[r for r in rows if r['zone']=='FR']
  for kind,values in series.items():
   pairs=[(r['generation_mwh_by_type'].get(kind),values.get(r['start'])) for r in rows]
   pairs=[(a,b) for a,b in pairs if a is not None and b is not None]
   a=sum(x[0] for x in pairs);b=sum(x[1] for x in pairs)
   comparisons.append(dict(month=month,type=kind,matched_hours=len(pairs),entsoe_mwh=a,energy_charts_mwh=b,relative_difference=(a-b)/b if b else None))
 result=dict(scope='France national production, matched UTC hours, MW hourly samples integrated for one hour',
  limitations=['Providers may share upstream ENTSO-E/RTE observations; not independent measurement','Missing timestamps and categories excluded, never filled','Matched-hour sums are not full monthly totals'],comparisons=comparisons)
 (root/'annual-independent/fr-comparison.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 print('Wrote 12-month matched-hour FR consistency check')
if __name__=='__main__':compare()
