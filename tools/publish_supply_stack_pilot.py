"""Cost-based generation stacks and observed-load comparison, not auction bids.

Uses prepared availability; observed dispatch never becomes capacity. Reservoir
hydro and pumped storage are excluded until inventory/opportunity costs exist.
"""
import hashlib,json
from pathlib import Path
import numpy as np,pandas as pd,pypsa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
LABELS=['Wind','Solar','Nuclear','Gas','Hard coal','Lignite','Run-of-river','Biomass','Reservoir hydro','Pumped storage','Other']
MODEL={'onwind':'Wind','offwind-ac':'Wind','offwind-dc':'Wind','offwind-float':'Wind','solar':'Solar','solar-hsat':'Solar','nuclear':'Nuclear','CCGT':'Gas','OCGT':'Gas','coal':'Hard coal','lignite':'Lignite','ror':'Run-of-river','biomass':'Biomass'}
OBSERVED={'Wind onshore':'Wind','Wind offshore':'Wind','Solar':'Solar','Nuclear':'Nuclear','Fossil gas':'Gas','Fossil hard coal':'Hard coal','Fossil brown coal / lignite':'Lignite','Hydro Run-of-River':'Run-of-river','Biomass':'Biomass','Hydro water reservoir':'Reservoir hydro','Hydro pumped storage':'Pumped storage'}
EXCLUDE={'Load','Residual load','Cross border electricity trading','Hydro pumped storage consumption','Renewable share of load','Renewable share of generation'}
def publish():
 cache=ROOT/'data/pypsa-eur/supply-stack-pilot';source=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/networks/base_s_128_elec_.nc';n=pypsa.Network(source);t=pd.Timestamp('2025-01-01T18:00:00');stamp=int(t.timestamp());out=ROOT/'public/research/supply-stack-pilot';out.mkdir(exist_ok=True)
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','svg.hashsalt':'grid-conductor-supply-stack','axes.spines.top':False,'axes.spines.right':False})
 countries=[]
 for country in ['PL','SE']:
  file=cache/(country+'-observed.json');raw=file.read_bytes();observed=json.loads(raw);times=np.asarray(observed['unix_seconds']);step=int(np.median(np.diff(times)));indices=np.where((times>=stamp)&(times<stamp+3600))[0]
  assert step in [900,3600] and len(indices)==3600//step and np.all(times[indices]==np.arange(stamp,stamp+3600,step))
  groups={};raw_series={};null_series=[]
  for series in observed['production_types']:
   values=[series['data'][i] for i in indices]
   if any(v is None for v in values):null_series.append(series['name']);continue
   value=float(np.mean(values));raw_series[series['name']]=value
   if series['name'] not in EXCLUDE:
    label=OBSERVED.get(series['name'],'Other');groups[label]=groups.get(label,0)+value
  if 'Load' not in raw_series:raise ValueError('Observed demand absent')
  buses=n.buses.index[n.buses.country==country];generators=n.generators[n.generators.bus.isin(buses)];units=n.storage_units[n.storage_units.bus.isin(buses)];available={};blocks=[]
  for identity,g in generators.iterrows():
   pu=float(n.generators_t.p_max_pu.loc[t,identity]) if identity in n.generators_t.p_max_pu else float(g.p_max_pu);power=float(g.p_nom)*pu
   if not np.isfinite(power) or power<0:raise ValueError('Invalid source availability')
   label=MODEL.get(g.carrier,'Other');available[label]=available.get(label,0)+power
   if power>1e-6:blocks.append(dict(id=identity,technology=str(g.carrier),available_mw=power,cost_eur_mwh=float(g.marginal_cost),co2_t_mwh=float(n.carriers.loc[g.carrier,'co2_emissions'])/float(g.efficiency)))
  load=float(n.loads_t.p_set.loc[t,n.loads.index[n.loads.bus.isin(buses)]].sum());demand=raw_series['Load'];scenarios=[]
  for carbon in [0,80]:
   stack=sorted([{**b,'scenario_cost_eur_mwh':b['cost_eur_mwh']+carbon*b['co2_t_mwh']} for b in blocks],key=lambda b:b['scenario_cost_eur_mwh']);total=0.;threshold=None
   for b in stack:
    total+=b['available_mw']
    if threshold is None and total>=demand:threshold=b['scenario_cost_eur_mwh']
   scenarios.append(dict(additional_carbon_eur_t=carbon,partial_stack_threshold_eur_mwh=threshold,available_generator_mw=total,blocks=stack))
  countries.append(dict(country=country,observed_load_mw=demand,prepared_load_mw=load,observed_generation_by_group_mw=groups,prepared_available_by_group_mw=available,excluded_storage_power_by_carrier_mw=units.groupby('carrier').p_nom.sum().to_dict(),null_observed_series=null_series,observed_hourly_series_mw=raw_series,observation_interval_seconds=step,observation_url=f'https://api.energy-charts.info/public_power?country={country.lower()}&start=2025-01-01&end=2025-01-02',observation_sha256=hashlib.sha256(raw).hexdigest(),scenarios=scenarios))
 price_raw=(cache/'PL-price.json').read_bytes();price=json.loads(price_raw);pt=np.asarray(price['unix_seconds']);pi=np.where((pt>=stamp)&(pt<stamp+3600))[0];ps=int(np.median(np.diff(pt)));assert ps in [900,3600] and len(pi)==3600//ps and np.all(pt[pi]==np.arange(stamp,stamp+3600,ps)) and all(price['price'][i] is not None for i in pi);observed_price=float(np.mean([price['price'][i] for i in pi]))
 fig,axes=plt.subplots(2,2,figsize=(14,9),sharex='row')
 for i,c in enumerate(countries):
  for j,scenario in enumerate(c['scenarios']):
   ax=axes[i,j];x=[0.];cost=[]
   for b in scenario['blocks']:x.append(x[-1]+b['available_mw']/1000);cost.append(b['scenario_cost_eur_mwh'])
   ax.stairs(cost,x,baseline=None,color='#0f766e',lw=2,label='Prepared available generators');ax.axvline(c['observed_load_mw']/1000,color='#b45309',lw=2,label='Observed load');ax.axvline(c['prepared_load_mw']/1000,color='#64748b',ls=':',label='Prepared model load')
   if c['country']=='PL':ax.axhline(observed_price,color='#2563eb',ls='--',label=f'Observed PL price €{observed_price:.2f}')
   ax.set(title=f'{c["country"]} · additional carbon €{scenario["additional_carbon_eur_t"]}/t',xlabel='Cumulative available generator power (GW)',ylabel='Assumed marginal cost (€/MWh)',ylim=(0,max(cost)*1.1));ax.legend(fontsize=8,loc='upper left')
 fig.suptitle('2025-01-01 18:00–19:00 UTC · partial domestic stacks, not market clearing',fontsize=14);fig.tight_layout();fig.savefig(out/'supply-demand-stacks.svg',metadata={'Date':None});plt.close(fig)
 fig,axes=plt.subplots(2,1,figsize=(12,8));x=np.arange(len(LABELS))
 for ax,c in zip(axes,countries):
  ax.bar(x-.2,[c['observed_generation_by_group_mw'].get(k,np.nan)/1000 for k in LABELS],.4,color='#d97706',label='Observed generation');ax.bar(x+.2,[c['prepared_available_by_group_mw'].get(k,np.nan)/1000 for k in LABELS],.4,color='#0f766e',label='Prepared available generator power');ax.set_xticks(x,LABELS,rotation=25,ha='right');ax.set(ylabel='GW',title=c['country']);ax.legend(fontsize=9)
 fig.suptitle('Generation is an outcome; availability is a model input',fontsize=14);fig.tight_layout();fig.savefig(out/'generation-versus-availability.svg',metadata={'Date':None});plt.close(fig)
 report=dict(status='exploratory_partial_supply_stack_not_calibrated',timestamp_utc=t.isoformat()+'Z',duration_hours=1,native_input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),countries=countries,observed_pl_price_eur_mwh=observed_price,price_source_url='https://api.energy-charts.info/price?bzn=PL&start=2025-01-01&end=2025-01-02',price_source_sha256=hashlib.sha256(price_raw).hexdigest(),price_license=price.get('license_info'),attribution='Fraunhofer ISE Energy-Charts API; prepared PyPSA-Eur v2026.08.0 inputs',limitations=['A New Year holiday hour is not representative of a full year.','Public net generation, prepared generation availability and prepared load can have different scopes.','Reservoir hydro and pumped storage excluded from supply curve; need inventory and opportunity costs.','Sweden is a national aggregate, not SE4; there is no single Swedish bidding-zone price.','No exchanges, internal network, commitment/minimum output, CHP heat obligations or bid markups.','2024 nuclear availability proxy and uncalibrated fleet; no inferred causal demand elasticity.','Carbon increments are scenarios, not observed hourly allowance prices.'])
 (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
 for c in countries:print(c['country'],'observed load',round(c['observed_load_mw']), 'model load',round(c['prepared_load_mw']),'partial thresholds',[round(s['partial_stack_threshold_eur_mwh'],2) if s['partial_stack_threshold_eur_mwh'] is not None else None for s in c['scenarios']])
 print('PL observed price',observed_price)
if __name__=='__main__':publish()
