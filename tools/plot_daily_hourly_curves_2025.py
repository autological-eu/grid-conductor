"""Show every fitted daily curve at one local clock hour; no re-fitting."""
import json,csv
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import run_independent_hourly_transport_2025 as source
from independent_hourly_transport_2025 import economic_nodes
from forward_hourly_splines_2025 import month_hours
from intraday_offer_bids_2025 import TIMEZONES
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json

PARENT=ROOT/'data/bidding-zone-network-2025/monthly-mean-forward-100-v1'
PRIOR=ROOT/'data/bidding-zone-network-2025/hourly-curve-comparison-v1'
OUT=ROOT/'data/bidding-zone-network-2025/daily-1500-curves-v1'

def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'receipt.json').exists():raise ValueError('Already rendered; inspect existing output')
 pinned=json.loads((PRIOR/'artifact-receipt.json').read_text())
 for name,h in pinned.items():
  if digest(ROOT/name)!=h:raise ValueError('Changed comparison artifact '+name)
 _,(state,m,_,_)=source.setup();s,d,_,_,_=state
 wanted=[('DE-LU','gas'),('FR','nuclear'),('ES','gas'),('GB','gas'),('PL','hard_coal'),('SE3','biomass')]
 curves=[];rows=[];counts=[];files=[]
 for zone,tech in wanted:
  g=next(i for i,x in enumerate(s['groups']) if x['zone']==zone and x['technology']==tech);cases=[]
  for month in [1,2]:
   h=month_hours(month);utc=pd.Timestamp('2025-01-01',tz='UTC')+pd.to_timedelta(h,unit='h');local=utc.tz_convert(TIMEZONES[zone[:2]])
   with np.load(PARENT/f'month-{month:02d}/100-parameters.npz') as z:raw=z['theta'][:,g]
   with np.load(PARENT/f'month-{month:02d}/100-within.npz') as z:q=z['quantities_gw'][:,g]
   economic=economic_nodes(raw);bids=economic+d['source_cost'][h,g,None]+.01*np.linspace(0,1,6)
   selected=np.flatnonzero(np.asarray(local.hour==15));case=[]
   for t in selected:
    available=d['capacity'][h[t],g]
    if available<=0:continue
    frac=float(q[t]*1000/available);bid=float(np.interp(frac,np.linspace(0,1,6),bids[t]));day=int(local[t].day)
    case.append(dict(day=day,bids=bids[t],fraction=frac,bid=bid))
    for k in range(6):rows.append([zone,tech,month,str(local[t]),int(h[t]),day,k*20,available*k/5,bids[t,k],economic[t,k],frac*100])
   counts.append(dict(zone=zone,technology=tech,month=month,clock_hours=len(selected),curves=len(case),unavailable_hours=len(selected)-len(case)))
   cases.append(case)
  curves.append((zone,tech,cases))
 cmap=plt.get_cmap('viridis');norm=Normalize(1,31)
 def draw(axes,zone,tech,cases):
  for ax,month,case in zip(axes,[1,2],cases):
   for row in case:
    color=cmap(norm(row['day']));ax.plot(np.linspace(0,100,6),row['bids'],color=color,alpha=.72,lw=1)
    ax.scatter(row['fraction']*100,row['bid'],s=9,color=color,zorder=3)
   ax.set(title=f'{zone} · {tech} · {"January" if month==1 else "February"} ({len(case)} days)',xlabel='% of that hour’s available output',ylabel='Full marginal bid EUR/MWh',xlim=(0,100));ax.grid(alpha=.15)
 for zone,tech,cases in curves:
  fig,axes=plt.subplots(1,2,figsize=(12,4.6),sharey=True);draw(axes,zone,tech,cases)
  fig.suptitle('Every daily fitted curve at15:00 local time · dot = dispatch location on its bid curve')
  fig.tight_layout(rect=(0,0,.93,.94));cax=fig.add_axes([.945,.19,.012,.58]);fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),cax=cax,label='Day of month')
  path=OUT/f'{zone}-{tech}.png';fig.savefig(path,dpi=150);plt.close(fig);files.append(path)
 fig,axes=plt.subplots(6,2,figsize=(13,21),sharex=True)
 for axs,(zone,tech,cases) in zip(axes,curves):draw(axs,zone,tech,cases)
 fig.suptitle('All daily fitted curves at15:00 local time; color = day of month, dot = dispatch location')
 fig.tight_layout(rect=(0,0,.93,.97));cax=fig.add_axes([.95,.35,.012,.3]);fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),cax=cax,label='Day of month');path=OUT/'all-daily-curves.png';fig.savefig(path,dpi=130);plt.close(fig);files.append(path)
 with (OUT/'curve-nodes.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['zone','technology','month','local_timestamp','utc_hour_index','day','percent_available','output_mw','full_bid_eur_mwh','economic_markup_eur_mwh','dispatch_percent']);w.writerows(rows)
 lines=['# Every daily curve at15:00 local time','',
 'Independent January and February100-update reconstructions. Each line is one day; the same day-of-month color scale1–31 is used for both months. Panels share price axes within a technology/zone. Dots show fitted dispatch quantities evaluated on their own marginal bid curves; they are NOT observed prices or evidence that this resource set the zonal price.', '',
 'Full offer prices include hourly source/fuel cost anchors and the0.01EUR/MWh technical slope, unlike the earlier economic-markup envelopes. The x-axis is percent of each actual hour\'s available output, not installed capacity; the CSV also gives MW. Only availability-positive hours are plotted. Zero-bid renewables and fixed hydro are not learned thermal curves and are omitted. Full low/high portions remain shown even when weakly identified away from dispatch.', '',
 'All actual local15:00 hours in January/February are used, without day sampling or retraining. Both months use their OWN observed prices and generation in fitting, so these are reconstruction comparisons, not forward forecasts. Curve variation may include underidentification and the effects of imposed hourly/temporal regularization.', '',
 '[Full grid](all-daily-curves.png) · [All plotted nodes and MW CSV](curve-nodes.csv)','']
 for zone,tech,_ in curves:lines += [f'## {zone} {tech}','',f'![All daily curves]({zone}-{tech}.png)','']
 (OUT/'report.md').write_text('\n'.join(lines)+'\n')
 files += [OUT/'report.md',OUT/'curve-nodes.csv']
 atomic_json(OUT/'receipt.json',dict(status='all_daily_curves_rendered',hour_local=15,counts=counts,source_sha256=digest(__file__),parent_manifest_sha256=digest(PRIOR/'artifact-receipt.json'),artifacts={str(p.relative_to(ROOT)):digest(p) for p in files}))
 print(json.dumps(counts),flush=True)

if __name__=='__main__':run()
