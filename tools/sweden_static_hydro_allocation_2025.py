"""Source plant-capacity geography instead of inherited hourly dispatch shares."""
import numpy as np
import xarray as xr
from nordic_ror_reconciliation_2025 import NATIVE
from run_network_stock_retiming_2025 import WATER,read

def net_demand(gross,country_power,plant_shares):
 gross=np.asarray(gross,float);power=np.asarray(country_power,float);share=np.asarray(plant_shares,float)
 if gross.shape!=(len(power),len(share)) or (power<0).any() or (share<0).any() or abs(share.sum()-1)>1e-8:raise ValueError('Unsupported hydro allocation')
 net=gross-power[:,None]*share
 np.testing.assert_allclose((gross-net).sum(axis=1),power,atol=1e-7,rtol=0)
 return net

def correct(state,market):
 s,d,A,emergency,sourcecap=state;T=1416;zones=np.array(s['zones']);se=np.array([z.startswith('SE') for z in zones]);gross=np.zeros((T,int(se.sum())))
 with xr.open_dataset(NATIVE) as n:
  buszone=dict(zip(n.buses_i.values,n.buses_bidding_zone.values));selected=list(zones[se])
  for j,bus in enumerate(n.loads_bus.values):
   zone=buszone[bus]
   if zone in selected:gross[:,selected.index(zone)]+=n.loads_t_p_set.values[:T,j]
 power=d['fixed_generation'][:T,s['countries'].index('SE'),s['technologies'].index('reservoir')];np.testing.assert_allclose((gross-d['load'][:T,se]).sum(axis=1),power,atol=1e-4,rtol=0)
 shares=read(WATER/'water.npz')['static_allocation'];new=net_demand(gross,power,shares);changed=d.copy();changed['load']=d['load'].copy();changed['load'][:T,se]=new;np.testing.assert_allclose(changed['load'].sum(axis=1),d['load'].sum(axis=1),atol=1e-7,rtol=0);market.load=changed['load']/1000
 return (s,changed,A,emergency,sourcecap),dict(zones=selected,static_plant_capacity_shares=shares.tolist(),country_net_demand_change_mwh=float((new-d['load'][:T,se]).sum()),limitations=['Country pooling and static capacity shares are still a geographic approximation, not zonal reservoir/inflow routing.','Independent reported generation validates the result; it is never used as an availability/allocation profile.'])
