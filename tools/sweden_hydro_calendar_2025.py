"""Parse source text and compile a fully covered Swedish Jan/Feb water calendar.

Published energy observations, not electricity-price targets. No fill of missing
weekly inflow observations. Full-year compilation requires additional reports.
"""
import re,datetime as dt,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/hydro-observations-2025/sweden-weekly-release-v2'

def parse(text):
 first=text.split('\f')[0];compact=' '.join(first.split());head=re.search(r'Vecka\s+(\d+)\b.*?år\s+(20\d\d)',compact)
 if not head:raise ValueError('Missing report week/year')
 week,year=map(int,head.groups());number=lambda x:float(x.replace(' ','').replace(',','.'))
 stock=re.search(r'till ([\d ]+) GWh denna vecka',compact);inflow=re.search(r'blev ([\d ]+) GWh',compact)
 if not stock or not inflow:raise ValueError('Incomplete source water numbers')
 zones={}
 for line in first.splitlines():
  match=re.search(r'\b(SE[1-4])\s+([\d,]+)\s+([\d ]+)\s*$',line)
  if match:zones[match[1]]=dict(percent=number(match[2]),stock_gwh=number(match[3]))
 if set(zones)!=set(['SE1','SE2','SE3','SE4']):raise ValueError('Incomplete regional stock rows')
 energy=number(stock[1]);flow=number(inflow[1])
 if abs(sum(z['stock_gwh'] for z in zones.values())-energy)>2.01:raise ValueError('Regional/national stock discrepancy exceeds rounding')
 if not 0<=energy<=33700 or flow<0:raise ValueError('Published energy outside stated33.7TWh stock capacity')
 return dict(year=year,week=week,stock_gwh=energy,inflow_gwh=flow,zones=zones)

def observations():
 rows={};sources={}
 for path in sorted(RAW.glob('*.pdf')):
  receipt=path.with_suffix('.json')
  if not receipt.exists():receipt=Path(str(path)+'.source.json')
  if not receipt.exists():continue
  source=json.loads(receipt.read_text());assert hashlib.sha256(path.read_bytes()).hexdigest()==source['sha256']
  row=parse(path.with_suffix('.txt').read_text());key=(row['year'],row['week'])
  if key in rows:raise ValueError('Multiple releases for week require explicit selection')
  rows[key]=row;sources[str(path.relative_to(ROOT))]=source
 return rows,sources

def compile_window(weather,hours=1416):
 rows,sources=observations();time=pd.date_range('2025-01-01',periods=hours,freq='h',tz='UTC');edges=pd.date_range('2025-01-01',periods=hours+1,freq='h',tz='UTC')
 flow=np.full(hours,np.nan);stock_points=[];details=[]
 for (year,week),row in rows.items():
  start=pd.Timestamp(dt.date.fromisocalendar(year,week,1)).tz_localize('Europe/Stockholm');end=start+pd.Timedelta(days=7);start=start.tz_convert('UTC');end=end.tz_convert('UTC')
  stock_points.append((end,row['stock_gwh']*1000));mask=(time>=start)&(time<end)
  if not mask.any():continue
  energy=row['inflow_gwh']*1000;complete=time[mask][0]==start and time[mask][-1]+pd.Timedelta(hours=1)==end
  if complete:
   weights=np.asarray(weather)[:hours][mask]
   if weights.sum()<=0:raise ValueError('Zero runoff shape')
   flow[mask]=energy*weights/weights.sum()
  else:flow[mask]=energy/168
  details.append(dict(year=year,week=week,full_week=complete,source_mwh=energy,used_mwh=float(flow[mask].sum())))
 if not np.isfinite(flow).all():raise ValueError('Missing weekly inflow: no silent filling')
 stock_points.sort();when=pd.DatetimeIndex([x[0] for x in stock_points]);values=np.array([x[1] for x in stock_points])
 if when[0]>edges[0] or when[-1]<edges[-1]:raise ValueError('Unbracketed stocks')
 target=np.interp(edges.asi8,when.asi8,values)
 return flow,target,33.7e6,dict(sources=sources,weeks=details,full_year_coverage='not established: do not extrapolate Jan/Feb result',stock_date_convention='reported end of ISO week: Monday00:00 Europe/Stockholm',inflow_method='Published calculated inflow energy; generation/stock dependence of source estimates not independently resolved. Retrospective reconstruction, not weather-only hydro forecast.',capacity_basis='PDF stated100%=33.7TWh; regional percentages use somewhat different implied denominators, not silently treated as exact capacity.')
