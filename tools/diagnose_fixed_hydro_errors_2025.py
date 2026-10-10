"""Untuned capacity, water and marginal-price diagnostics for the selected model.
Sensitivity probes are not replacement baselines or physically accepted scenarios.
"""
import argparse,json,time,resource,signal
from pathlib import Path
import numpy as np
import pandas as pd
import highspy
import european_physical_bids_2025 as physical
from hybrid_fixed_hydro_2025 import load,compiled,resource_costs,verified_fuel,FUEL,TOL
from simple_resource_bids import cost_assumptions
from compare_daily_dispatch_prices import model_area,metrics,audit_observations
from hourly_renewable_estimates import digest
from european_reservoir_clearing_2025 import FOLDER
ROOT=Path(__file__).resolve().parents[1]


def point(m,t,delta=0.,area='1:NO'):
    h=physical.solver(m);g=np.arange(m['ng'],dtype=np.int32);c=np.arange(m['ng']+m['nl'],dtype=np.int32);r=np.arange(m['nz'],dtype=np.int32)
    demand=m['load'][t].copy();demand[m['zones'].index(area)]+=delta
    h.changeColsCost(len(g),g,m['cost'][t]);h.changeColsBounds(len(c),c,np.r_[np.zeros(m['ng']),m['link_min'][t]],np.r_[m['availability'][t],m['link_max'][t]])
    h.changeRowsBounds(len(r),r,demand,demand);h.setOptionValue('time_limit',10.);h.run()
    if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:raise ValueError('Nonoptimal diagnostic')
    x=np.asarray(h.getSolution().col_value);ax=m['A']@x
    if abs(ax[:m['nz']]-demand).max()>TOL:raise ValueError('Diagnostic balance failed')
    return float(h.getObjectiveValue()),float(h.getSolution().row_dual[m['zones'].index(area)])


def run(folder,out):
    start=time.perf_counter();summary=json.loads((folder/'summary.json').read_text());replay=json.loads((folder/'replay.json').read_text())
    if replay['summary_sha256']!=digest(folder/'summary.json'):raise ValueError('Detached annual replay')
    witness=folder/'resource_bids.npz'
    if digest(witness)!=summary['cases']['resource_bids']['witness_sha256']:raise ValueError('Changed primal')
    for name,sha in summary['provenance']['dependencies'].items():
        if digest(ROOT/'tools'/name)!=sha:raise ValueError('Changed model source')
    n,b,common=load();cost=resource_costs(n,b['cost'],verified_fuel(FUEL),cost_assumptions()[0],'resource_bids');m=compiled(n,b,cost)
    with np.load(witness,allow_pickle=False) as a:prices=a['prices'].copy();values=a['values'].copy();obj=a['objectives'].copy()
    source=ROOT/'data/price-trace/dispatch-validation-2025-v2';manifest=json.loads((source/'manifest.json').read_text());errors=[]
    spike=prices[:,m['zones'].index('1:NO')]>1000
    for zone,meta in manifest['zones'].items():
        area,scope=model_area(zone)
        if area not in m['zones']:continue
        path=source/(zone+'.json');observed=np.array([np.nan if x is None else x for x in json.loads(path.read_text())])
        if digest(path)!=meta['hourly_sha256']:raise ValueError('Changed observed series')
        audit_observations(zone,meta,observed)
        if not np.isfinite(observed).any():continue
        modeled=prices[:,m['zones'].index(area)];valid=np.isfinite(observed);high=modeled>1000
        total=float(abs(modeled[valid]-observed[valid]).sum())
        errors.append(dict(zone=zone,area=area,scope=scope,annual=metrics(modeled,observed),
            above_1000_hours=int((high&valid).sum()),above_1000_error_fraction=float(abs(modeled[high&valid]-observed[high&valid]).sum()/total),
            non_spike=metrics(modeled[~high],observed[~high])))
    errors.sort(key=lambda r:-r['annual']['mae_eur_mwh'])
    ember=ROOT/'data/pypsa-eur/ember-current-release/monthly.csv';receipt=json.loads(ember.with_name('receipt.json').read_text())
    if digest(ember)!=receipt['sha256']:raise ValueError('Changed Ember raw source')
    df=pd.read_csv(ember,usecols=['Date','ISO 3 code','Area type','Electricity source','Generation (TWh)']);df=df[df.Date.str.startswith('2025')];capacity=json.loads((ROOT/'public/research/irena-capacity-2025/summary.json').read_text())
    countries={'NO':'NOR','DK':'DNK','EE':'EST','LT':'LTU','LV':'LVA','FI':'FIN','SE':'SWE'};fleet=[]
    hyd=n.storage_units.query("carrier=='hydro'");gc=n.generators.bus.map(n.buses.country);hc=hyd.bus.map(n.buses.country)
    # Match the compiler's exact groups; dispatch by carrier is published only for unambiguous ROR groups.
    groups={}
    for j,z in enumerate(n.generators.bus.map(m['buszone'])):
        key=(z,cost[:,j].tobytes(),n.generators.iloc[j].carrier=='emergency');groups.setdefault(key,[]).append(j)
    for country,iso in countries.items():
        zi=[i for i,z in enumerate(m['zones']) if z.split(':')[1]==country];ids=(gc==country)&(n.generators.carrier!='emergency')
        raw=n.generators[ids].groupby('carrier').p_nom.sum().div(1000).to_dict();hydro_gw=float(hyd[hc==country].p_nom.sum()/1000+raw.get('ror',0))
        fixed=float((common['source_load']-b['load'])[:,zi].sum()/1e6);ror_lo=0.;ror_hi=0.
        for j,((z,_,_),js) in enumerate(groups.items()):
            if z.split(':')[1]!=country:continue
            carriers=set(n.generators.iloc[js].carrier)
            if 'ror' in carriers:
                rids=[k for k in js if n.generators.iloc[k].carrier=='ror'];oids=[k for k in js if k not in rids]
                rav=b['availability'][:,rids].sum(axis=1);other=b['availability'][:,oids].sum(axis=1) if oids else 0.
                ror_lo+=np.maximum(values[:,j]-other,0).sum()/1e6;ror_hi+=np.minimum(values[:,j],rav).sum()/1e6
        sub=df[(df['ISO 3 code']==iso)&(df['Area type'].str.lower().str.startswith('country'))]
        counts=sub.groupby('Electricity source').size().to_dict();energy=sub.groupby('Electricity source')['Generation (TWh)'].sum().to_dict()
        if counts.get('Hydro')!=12 or counts.get('Demand')!=12:raise ValueError('Incomplete Ember national year '+country)
        ir=[r for r in capacity['irena_rows'] if r['country']==country];ir={r['technology']:r['capacity_2025']['mw']/1000 for r in ir}
        fleet.append(dict(country=country,source_generator_capacity_gw=raw,source_hydro_including_ror_gw=hydro_gw,irena_hydropower_2025_gw=ir.get('Hydropower'),
            source_demand_twh=float(common['source_load'][:,zi].sum()/1e6),fixed_reservoir_output_twh=fixed,model_ror_output_bounds_twh=[float(ror_lo),float(ror_hi)],
            model_total_hydro_bounds_twh=[fixed+float(ror_lo),fixed+float(ror_hi)],ember_2025_twh=energy,ember_month_counts=counts))
    power=np.concatenate([np.load(FOLDER/f'{i:02d}.npz',allow_pickle=False)['hydro_power'] for i in range(59)])
    inflow=n.get_switchable_as_dense('StorageUnit','inflow').loc[:,hyd.index].to_numpy();mask=(hc=='NO').to_numpy();eta=hyd.efficiency_dispatch.to_numpy()
    headroom=((hyd.p_nom*hyd.p_max_pu).to_numpy()[mask]-power[:,mask]).sum(axis=1)
    highhours=np.flatnonzero(spike);sensitivity=[]
    for t in highhours:
        low,_=point(m,int(t),-1);up,_=point(m,int(t),1)
        sensitivity.append(dict(hour=int(t),utc=str(n.snapshots[t]),saved_price=float(prices[t,m['zones'].index('1:NO')]),
            downward_incremental_cost_eur_mwh=float(obj[t]-low),upward_incremental_cost_eur_mwh=float(up-obj[t])))
    # Diagnose capacity-only injection weights excluding all reservoir turbines.
    original=physical.gsk
    extra=hyd.loc[hc=='NO'].groupby('bus').p_nom.sum()
    def hydro_gsk(buses,country,capacity):return original(buses,country,capacity.add(extra,fill_value=0))
    physical.gsk=hydro_gsk
    try:newbase=physical.compile_model(n)
    finally:physical.gsk=original
    newbase['load']=b['load'].copy();gm=compiled(n,newbase,cost)
    probes=[dict(hour=int(t),price_eur_mwh=point(gm,int(t))[1]) for t in highhours]
    native_hour=int(highhours[0]);native_obj,_=point(gm,native_hour)
    native=physical.native_check(n,gm|dict(cost=gm['native_cost']),native_hour,native_obj)
    em=values[:,:m['ng']][:,m['emergency_mask']].sum(axis=1)
    result=dict(status='selected_model_error_diagnostics',producer_sha256=digest(__file__),annual_summary_sha256=digest(folder/'summary.json'),
        annual_witness_sha256=digest(witness),model_dependencies=summary['provenance']['dependencies'],observed_manifest_sha256=digest(source/'manifest.json'),
        source_receipts=dict(ember=receipt,irena_summary_sha256=digest(ROOT/'public/research/irena-capacity-2025/summary.json')),
        ranked_errors=errors,capacity_and_energy=fleet,
        norway=dict(high_price_hours=len(highhours),high_price_hours_without_emergency=int(np.count_nonzero(spike&(em<=1e-6))),
            turbine_headroom_min_on_spikes_mw=float(headroom[spike].min()),turbine_headroom_mean_on_spikes_mw=float(headroom[spike].mean()),
            source_reservoir_inflow_water_twh=float(inflow[:,mask].sum()/1e6),source_reservoir_inflow_electrical_equivalent_twh=float((inflow[:,mask]*eta[mask]).sum()/1e6),
            price_interval_probes=sensitivity,hydro_capacity_gsk_probe=probes,hydro_gsk_native_check=native,
            original_weights=m['weights']['1:NO'],hydro_inclusive_weights=gm['weights']['1:NO']),
        elapsed_seconds=time.perf_counter()-start,limitations=['One-MW demand perturbations diagnose local marginal kinks, not observed bids or calibrated prices',
            'Hydro-inclusive GSK probes change an assumed network distribution, not capacity, water or commercial geography; not adopted',
            'IRENA end-year and prepared fleet have different temporal/classification scopes; Ember national totals are not zonal constraints',
            'Fixed output is not a hydro-price parameter: changing marginal_cost cannot change these injected volumes'])
    out.write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')
    print(json.dumps({k:result['norway'][k] for k in ['high_price_hours','high_price_hours_without_emergency','turbine_headroom_min_on_spikes_mw','turbine_headroom_mean_on_spikes_mw']}))

if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(600)
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.run,a.out)
