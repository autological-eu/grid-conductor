"""Metered geography controls, never replacement of total Norwegian demand."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sigmoid_month_pairs_2025 import ROOT,digest
SOURCE=ROOT/'data/bidding-zone-source-audit-2025/elhub-annual-v1'
def observed(zones,hours=1416):
 summary=json.loads((SOURCE/'summary.json').read_text());audit=json.loads((SOURCE/'audit.json').read_text());assert audit['summary_sha256']==digest(SOURCE/'summary.json');assert digest(SOURCE/'hourly.csv')==summary['hourly_sha256']
 frame=pd.read_csv(SOURCE/'hourly.csv');rows=[];axis=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC').as_unit('ns')
 for zone in zones:
  f=frame[frame.zone.eq(zone)].copy();f['date']=pd.to_datetime(f.utc,utc=True).dt.as_unit('ns');f=f.sort_values('date');assert not f.date.duplicated().any();np.testing.assert_array_equal(f.date.to_numpy(),axis.to_numpy());rows.append(f.metered_consumption_mwh.to_numpy(float)[:hours])
 values=np.column_stack(rows)
 if not np.isfinite(values).all() or (values<0).any() or (values.sum(axis=1)<=0).any():raise ValueError('Incomplete/nonpositive metered demand')
 return values

def allocate(gross,metered,kind):
 gross=np.asarray(gross,float);metered=np.asarray(metered,float)
 if gross.shape!=metered.shape or (gross<0).any() or not np.isfinite(gross).all():raise ValueError('Invalid demand')
 total=gross.sum(axis=1);residual=total-metered.sum(axis=1)
 if kind=='metered_plus_original_residual':
  if (residual < -1e-4).any():raise ValueError('Negative non-metered residual; scope cannot support additive control')
  result=metered+residual[:,None]*gross/total[:,None]
 elif kind=='metered_proportional_scope_control':
  result=total[:,None]*metered/metered.sum(axis=1)[:,None]
 else:raise ValueError('Unknown predeclared control')
 np.testing.assert_allclose(result.sum(axis=1),total,atol=1e-7,rtol=0)
 if result.min() < -1e-7:raise ValueError('Negative allocated load')
 return result,dict(minimum_nonmetered_residual_mw=float(residual.min()),maximum_nonmetered_residual_mw=float(residual.max()),negative_residual_hours=int((residual<0).sum()),net_country_energy_difference_mwh=float((result-gross).sum()))
