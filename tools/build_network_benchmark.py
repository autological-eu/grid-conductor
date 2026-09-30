"""Export a real-data matched dispatch benchmark from the pinned PyPSA network.

This is 2013 weather/load with the archive's existing capacities and cost assumptions,
not a 2025 historical model. AC lines become thermal-bound transport edges in the
canonical input; a separate native AC run measures that explicit physics reduction.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pypsa
from fetch_pypsa_benchmark import fetch, SHA256, URL, MEMBER
from market_model import validate

ROOT=Path(__file__).resolve().parents[1]

def build(hours=168, start='2013-01-01'):
    source=fetch();n=pypsa.Network(source)
    snapshots=n.snapshots[n.snapshots>=start][:hours]
    if len(snapshots)!=hours or not np.all(np.diff(snapshots.values)==np.timedelta64(1,'h')):
        raise ValueError('Exact consecutive source period required')
    if not np.all(n.snapshot_weightings.loc[snapshots].to_numpy()==1):
        raise ValueError('Non-hourly weights are unsupported')
    if len(n.stores) or len(n.transformers) or len(n.global_constraints):
        raise ValueError('Unsupported source components/constraints')
    if n.generators.committable.any() or n.generators.ramp_limit_up.notna().any() or n.generators.ramp_limit_down.notna().any():
        raise ValueError('Unsupported commitment/ramp physics in this source adapter')
    generators=[];excluded=[]
    for identity,g in n.generators.iterrows():
        if g.p_nom==0:excluded.append(identity);continue
        if g.p_nom<0 or g.p_min_pu!=0 or g.marginal_cost<0:
            raise ValueError('Unsupported generator assumptions')
        profile=n.generators_t.p_max_pu.loc[snapshots,identity] if identity in n.generators_t.p_max_pu else np.full(hours,g.p_max_pu)
        maximum=np.asarray(profile,dtype=float)*g.p_nom
        if not np.isfinite(maximum).all() or (maximum<0).any():raise ValueError('Invalid generation availability')
        intensity=float(n.carriers.loc[g.carrier,'co2_emissions'])/float(g.efficiency)
        generators.append(dict(id=identity,zone=g.bus,max_mw=maximum.tolist(),cost_eur_mwh=float(g.marginal_cost),co2_t_per_mwh=intensity))
    edges=[];mapping=[]
    for identity,e in n.lines.iterrows():
        if e.s_nom<0:raise ValueError('Invalid thermal rating')
        bound=float(e.s_nom*e.s_max_pu)
        edges.append(dict(id='ac:'+identity,a=e.bus0,b=e.bus1,ab_mw=[bound]*hours,ba_mw=[bound]*hours))
        mapping.append(dict(id='ac:'+identity,component='Line',source_id=identity,meaning='fixed impedance, thermal bound relief; transport omits Kirchhoff laws'))
    for identity,e in n.links.iterrows():
        if e.efficiency!=1 or e.p_min_pu!=-1 or e.p_max_pu!=1 or e.marginal_cost!=0:
            raise ValueError('Only lossless bidirectional source links supported')
        edges.append(dict(id='dc:'+identity,a=e.bus0,b=e.bus1,ab_mw=[float(e.p_nom)]*hours,ba_mw=[float(e.p_nom)]*hours))
        mapping.append(dict(id='dc:'+identity,component='Link',source_id=identity,meaning='lossless bidirectional HVDC nominal rating, not hourly commercial ATC'))
    storage=[]
    for identity,s in n.storage_units.iterrows():
        if s.p_nom<0 or s.p_max_pu!=1 or s.marginal_cost!=0:raise ValueError('Unsupported storage cost/bounds')
        if s.p_nom==0:continue
        inflow=n.storage_units_t.inflow.loc[snapshots,identity].to_numpy() if identity in n.storage_units_t.inflow else np.zeros(hours)
        charge=float(-s.p_nom*s.p_min_pu)
        if charge<0 or ((inflow<0)|~np.isfinite(inflow)).any():raise ValueError('Invalid inflow/charging capacity')
        if s.efficiency_store==0 and charge!=0:raise ValueError('Zero efficiency with charging enabled')
        storage.append(dict(id=identity,zone=s.bus,power_mw=float(s.p_nom),charge_power_mw=charge,energy_mwh=float(s.p_nom*s.max_hours),initial_mwh=0,terminal_mwh=0,cyclic=bool(s.cyclic_state_of_charge),charge_efficiency=float(s.efficiency_store) if charge else 1.0,discharge_efficiency=float(s.efficiency_dispatch),standing_loss=float(s.standing_loss),inflow_mw=inflow.tolist(),throughput_cost_eur_mwh=0))
    load=n.loads_t.p_set.loc[snapshots].T.groupby(n.loads.bus).sum().T
    zones=list(n.buses.index)
    if set(load.columns)!=set(zones) or not np.isfinite(load.to_numpy()).all() or (load.to_numpy()<0).any():raise ValueError('Incomplete load geography')
    assumptions=[
        'Technical benchmark: 2013 hourly weather/load, existing archived capacities; renewable capacity estimation year 2020 and source cost year 2030. Not a 2025 historical reconstruction.',
        'All generation and network capacity expansion disabled; only explicit intervention patches change fixed nominal capacities.',
        '37 clustered buses are physical model nodes, not bidding zones. Swedish SE1 0 / SE2 0 labels are cluster IDs, not SE1/SE2 market zones or SE4.',
        'Lossless transport relaxation uses archived AC thermal bounds (s_nom × 0.7) and DC nominal ratings, not commercial NTC/ATC. The native AC benchmark separately retains Kirchhoff constraints.',
        'Prepared renewable p_max_pu availability is retained, not reconstructed from solved dispatch. Source reservoir inflows, efficiencies and pumped storage are retained.',
        f'Exactly {hours} consecutive hourly intervals; source cyclic storage is closed over this benchmark period. No annual extrapolation; weekly cycle changes the source annual water boundary.',
        'Unserved energy penalty €10,000/MWh is a declared feasibility diagnostic. Shortage-affected benefits are not ordinary investment welfare.',
        'Storage benchmark additions use empty initial/terminal inventory and zero throughput cost to match native StorageUnit economics; public lab default battery costs are separate.',
    ]
    data=dict(schema_version=2,dataset_id=f'pypsa-eur-37-2013-{hours}h',provenance=dict(source='Zenodo 7646728 / networks/elec_s_37.nc (CC BY 4.0)',source_sha256=SHA256,assumptions=assumptions),timestamps=[str(t.isoformat())+'Z' for t in snapshots],interval_hours=1,zones=zones,load_mw={z:load[z].tolist() for z in zones},external_net_import_mw={z:[0.0]*hours for z in zones},generators=generators,edges=edges,storage=storage,flow_based_regions=[],unserved_cost_eur_mwh=10000)
    validate(data)
    swepol=next(e['id'] for e in edges if e['id']=='dc:14823')
    mesh=next(e['id'] for e in edges if e['id'].startswith('ac:') and {n.buses.loc[e['a'],'country'],n.buses.loc[e['b'],'country']}=={'DE','FR'})
    battery=dict(id='benchmark-battery-PL',zone='PL1 0',power_mw=100,energy_mwh=400,initial_mwh=0,terminal_mwh=0,charge_efficiency=.95,discharge_efficiency=.95,throughput_cost_eur_mwh=0)
    cases=[dict(id='baseline',edge_additions_mw={},storage=[])]
    for value in [100,500,1000]:cases.append(dict(id=f'swepol-plus-{value}',edge_additions_mw={swepol:value},storage=[]))
    cases.extend([dict(id='battery-PL-100-400',edge_additions_mw={},storage=[battery]),dict(id='mixed-500-battery',edge_additions_mw={swepol:500},storage=[battery]),dict(id='meshed-DE-FR-plus-500',edge_additions_mw={mesh:500},storage=[])])
    manifest=dict(status='experimental_technical_benchmark_not_validated',dataset_id=data['dataset_id'],source_url=URL,source_member=MEMBER,source_sha256=SHA256,license='CC BY 4.0; attribute PyPSA-Eur authors and Zenodo 7646728',source_pypsa_version='0.22.1',source_release='v0.7.0',source_weather_year=2013,renewable_capacity_estimation_year=2020,cost_year=2030,hours=hours,start=data['timestamps'][0],end_exclusive=(snapshots[-1]+np.timedelta64(1,'h')).isoformat()+'Z',buses=len(zones),generators=len(generators),storage_units=len(storage),edges=len(edges),excluded_zero_capacity_generators=excluded,edge_mapping=mapping,assumptions=assumptions,cases=cases)
    return data,manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--hours',type=int,default=168);p.add_argument('--start',default='2013-01-01');p.add_argument('--output',type=Path,default=ROOT/'public/research/network-benchmark')
    a=p.parse_args();data,manifest=build(a.hours,a.start);a.output.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(data,allow_nan=False,separators=(',',':'))+'\n').encode();(a.output/'input.json').write_bytes(raw);manifest['input_file_sha256']=hashlib.sha256(raw).hexdigest();(a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ['dataset_id','hours','buses','generators','storage_units','edges','input_file_sha256']}));print('Input bytes',len(raw))
