"""ROR availability from the same inflow budget as the reservoir reconstruction.

Retains the existing capacity-based reservoir/ROR partition as an explicit
assumption; no dispatch or observed generation is used as availability.
"""
import json
from pathlib import Path
import numpy as np
import xarray as xr
from run_network_stock_retiming_2025 import read,NORWAY,WATER
from sigmoid_month_pairs_2025 import ROOT,digest
NATIVE=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1/native.nc'
NO_META=ROOT/'data/hydro-observations-2025/nve-updated-model-v5/summary.json'

def river_profile(total_inflow,reservoir_share,turbine_by_zone):
 flow=np.asarray(total_inflow,float);nom=np.asarray(turbine_by_zone,float)
 if not np.isfinite(flow).all() or (flow<0).any() or not 0<reservoir_share<1 or (nom<=0).any():raise ValueError('Invalid hydro source')
 river=flow*(1-reservoir_share);potential=river[:,None]*nom/nom.sum();available=np.minimum(potential,nom);spill=potential-available
 np.testing.assert_allclose(available.sum(axis=1)+spill.sum(axis=1)+flow*reservoir_share,flow,atol=1e-7,rtol=0)
 return available,spill

def correct(state,market):
 s,d,A,emergency,sourcecap=state;T=1416;capacity=d['capacity'].copy();sourcecap=sourcecap.copy();records=[]
 with xr.open_dataset(NATIVE) as n:
  mapping=dict(zip(n.buses_i.values,n.buses_bidding_zone.values));zone=np.array([mapping[b] for b in n.generators_bus.values]);ror=n.generators_carrier.values=='ror';nom=n.generators_p_nom.values
 no=read(NORWAY/'hydro.npz');se=read(WATER/'water.npz');meta=json.loads(NO_META.read_text())
 for country in ['NO','SE']:
  ids=[i for i,g in enumerate(s['groups']) if g['country']==country and g['technology']=='ror'];zones=[s['groups'][i]['zone'] for i in ids];turbines=np.array([nom[ror&(zone==z)].sum() for z in zones])
  allnom=nom[ror&np.array([str(z).startswith(country) for z in zone])].sum();np.testing.assert_allclose(turbines.sum(),allnom,atol=1e-6,rtol=0)
  share=float(meta['reservoir_share']) if country=='NO' else float(se['reservoir_share']);total=no['source_inflow'][:T]/share if country=='NO' else se['source_total_inflow'];new,spill=river_profile(total,share,turbines)
  old=capacity[:T,ids].copy();capacity[:T,ids]=new
  for col,g in enumerate(ids):
   originals=np.flatnonzero(np.asarray(s['mapping'])==g)
   if len(originals)!=1:raise ValueError('New ROR profile needs explicit original-group allocation')
   sourcecap[:T,originals[0]]=new[:,col]
  records.append(dict(country=country,zones=zones,turbines_mw=turbines.tolist(),reservoir_share=share,old_available_twh=[float(old[a:b].sum()/1e6) for a,b in [(0,744),(744,T)]],new_available_twh=[float(new[a:b].sum()/1e6) for a,b in [(0,744),(744,T)]],capped_spill_twh=[float(spill[a:b].sum()/1e6) for a,b in [(0,744),(744,T)]]))
 untouched=[i for i,g in enumerate(s['groups']) if not(g['country'] in ['NO','SE'] and g['technology']=='ror')];np.testing.assert_array_equal(capacity[:,untouched],d['capacity'][:,untouched]);np.testing.assert_array_equal(capacity[T:],d['capacity'][T:])
 adapted=d.copy();adapted['capacity']=capacity;market.capacity=capacity/1000
 return (s,adapted,A,emergency,sourcecap),records
