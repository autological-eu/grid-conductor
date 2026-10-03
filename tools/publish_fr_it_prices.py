"""Publish public historical price intervals as explicitly aligned hourly means."""
import json,datetime,hashlib,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[1];start=int(datetime.datetime(2025,1,1,tzinfo=datetime.timezone.utc).timestamp());end=start+8760*3600
series={};sources=[]
for zone in ['FR','IT-North']:
 path=root/'data/price-trace'/f'{zone}.json';raw=path.read_bytes();d=json.loads(raw);t=d['unix_seconds'];v=d['price'];q={}
 for i,(stamp,value) in enumerate(zip(t,v)):
  duration=t[i+1]-stamp if i+1<len(t) else 900
  assert duration in (900,3600)
  if value is None:continue
  for instant in range(stamp,stamp+duration,900):
   if start<=instant<end:q[instant]=float(value)
 series[zone]=q;sources.append(dict(zone=zone,url=f'https://api.energy-charts.info/price?bzn={zone}&start=2025-01-01&end=2025-12-31',sha256=hashlib.sha256(raw).hexdigest(),license=d['license_info'],unit=d['unit']))
rows=[]
for hour in range(start,end,3600):
 points=list(range(hour,hour+3600,900));prices={z:float(np.mean([series[z][t] for t in points])) if all(t in series[z] for t in points) else None for z in series}
 rows.append(dict(time_utc=datetime.datetime.fromtimestamp(hour,datetime.timezone.utc).isoformat(),fr_eur_mwh=prices['FR'],it_north_eur_mwh=prices['IT-North'],spread_eur_mwh=None if None in prices.values() else prices['IT-North']-prices['FR']))
known=[r for r in rows if r['spread_eur_mwh'] is not None];out=root/'public/research/fr-it-screening';out.mkdir(exist_ok=True)
with (out/'hourly-prices.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
times=[datetime.datetime.fromisoformat(r['time_utc']) for r in rows];spread=np.array([np.nan if r['spread_eur_mwh'] is None else r['spread_eur_mwh'] for r in rows]);fig,(a,b)=plt.subplots(2,1,figsize=(13,7),sharex=True);a.plot(times,spread,lw=.5,color='#0f766e');a.axhline(0,color='#475569',lw=.8);a.axhline(5,color='#d97706',ls='--',label='€5 screening threshold');a.set(ylabel='Italy North − France (€/MWh)',title='Observed historical day-ahead price separation · hourly trace, 2025 UTC');a.legend();cumulative=np.cumsum(np.nan_to_num(np.maximum(spread,0)))*500/1e6;b.plot(times,cumulative,color='#b45309');b.set(ylabel='Fixed-spread 500 MW ladder (M€)',xlabel='2025 (UTC)');fig.text(.1,.01,'Cumulative curve assumes unchanged hourly prices and no network constraints; not welfare or project revenue. Missing intervals contribute nothing.',fontsize=9);fig.tight_layout(rect=(0,.04,1,1));fig.savefig(out/'hourly-price-trace.svg',metadata={'Date':None});plt.close(fig)
summary=dict(sources=sources,hours=len(rows),known_hours=len(known),missing_hours=[r['time_utc'] for r in rows if r['spread_eur_mwh'] is None],positive_spread_500_meur=float(cumulative[-1]),hourly_mean_spread=float(np.nanmean(spread)),above_5_hours=int(np.sum(spread>5)),limitations=['Public Energy-Charts/SMARD price data; not fetched directly from the original ENTSO-E bank.','Hourly values average complete quarter-hour prices; hourly source prices apply to all four quarters.','No scheduled-flow coverage mask; cannot establish parity with original screening input.'])
(out/'price-trace-provenance.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
