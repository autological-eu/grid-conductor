"""Export the prepared 2025 conditional window without replacing availability with dispatch.

Native input must already specify fixed initial and terminal storage inventories.
Unsupported source features fail explicitly. This is not an annual valuation.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pypsa
from market_model import validate

def export(source,output):
    n=pypsa.Network(source);n.calculate_dependent_values()
    hours=len(n.snapshots);start=n.snapshots[0]
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
        if e.efficiency!=1 or e.p_min_pu not in (-1,0) or e.p_max_pu!=1 or e.marginal_cost!=0:
            raise ValueError('Only lossless bidirectional source links supported')
        edges.append(dict(id='dc:'+identity,a=e.bus0,b=e.bus1,ab_mw=[float(e.p_nom)]*hours,ba_mw=[float(-e.p_nom*e.p_min_pu)]*hours))
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
    storage_ids={s['id'] for s in storage}
    for s in storage:
        if n.storage_units.loc[s['id'],'cyclic_state_of_charge']:
            raise ValueError('Conditional window requires explicit fixed boundaries')
        s['cyclic']=False
        s['initial_mwh']=float(n.storage_units.loc[s['id'],'state_of_charge_initial'])
        s['terminal_mwh']=float(n.storage_units_t.state_of_charge_set[s['id']].iloc[-1])
    data=dict(schema_version=3,dataset_id=f'pypsa-eur-128-2025-january-{hours}h-conditional',provenance=dict(source='Prepared PyPSA-Eur v2026.08.0 conditional window',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),assumptions=['Fixed storage boundaries from sequential monthly reference; not annual valuation.','2024 country nuclear availability proxy; not historically calibrated.','Original renewable availability retained; no dispatch substitution.','Nodal spill and shortage variables are explicit diagnostics, matched in both solvers.']),timestamps=[t.isoformat()+'Z' for t in snapshots],interval_hours=1,zones=zones,load_mw={z:load[z].tolist() for z in zones},external_net_import_mw={z:[0.0]*hours for z in zones},generators=generators,edges=edges,storage=storage,flow_based_regions=[],unserved_cost_eur_mwh=10000,ac_branches=[dict(edge_id='ac:'+i,reactance=float(e.x_pu_eff)) for i,e in n.lines.iterrows()])
    validate(data)
    output.write_text(json.dumps(data,allow_nan=False,separators=(',',':'))+'\n')
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();d=export(a.source,a.output);print('Exported',len(d['timestamps']),'hours')
