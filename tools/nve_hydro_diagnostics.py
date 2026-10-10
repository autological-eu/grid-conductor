"""Source-verified NVE case and independent physical-offset diagnostic helpers."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
import highspy
from hourly_renewable_estimates import digest
from hybrid_fixed_hydro_2025 import load,compiled,resource_costs,verified_fuel,FUEL
from simple_resource_bids import cost_assumptions
from european_physical_bids_2025 import compile_model,solver
from european_reservoir_clearing_2025 import FOLDER
from fixed_reservoir_screening_2025 import fixed_injections
from nve_hydro_inputs_2025 import ROOT,compile_inputs

NVE=ROOT/'data/hydro-observations-2025/nve-updated-model-v5'

def rebuild():
    s=json.loads((NVE/'summary.json').read_text());a=json.loads((NVE/'audit.json').read_text())
    assert a['summary_sha256']==digest(NVE/'summary.json')
    for name,sha in s['new_sources'].items():assert digest(ROOT/'tools'/name)==sha
    for name,sha in s['dependencies']['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    assert digest(NVE/'resource_bids.npz')==s['witness_sha256']
    assert digest(NVE/'water.npz')==s['water_witness_sha256']
    n,b,c=load();su=n.storage_units.query("carrier=='hydro'");mask=(su.bus.map(n.buses.country)=='NO').values
    with np.load(NVE/'water.npz',allow_pickle=False) as w:water={k:w[k].copy() for k in w.files}
    with xr.open_dataarray(ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/profile_hydro.nc') as weather:f,stock,cap,source=compile_inputs(weather.sel(countries='NO').values)
    assert source['compiler_sha256']==s['hydro_source']['compiler_sha256']
    ror=n.generators.index[(n.generators.carrier=='ror')&(n.generators.bus.map(n.buses.country)=='NO')]
    share=su.loc[su.index[mask]].p_nom.sum()/(su.loc[su.index[mask]].p_nom.sum()+n.generators.loc[ror].p_nom.sum())
    n.generators_t.p_max_pu.loc[:,ror]=np.minimum(f[:,None]*(1-share)/n.generators.loc[ror].p_nom.sum(),1.)
    np.testing.assert_allclose(water['inflow'],f[:,None]*share*(su.loc[su.index[mask]].p_nom.values/su.loc[su.index[mask]].p_nom.sum())/water['eta'],rtol=0,atol=1e-6)
    hp=np.concatenate([np.load(FOLDER/f'{i:02d}.npz',allow_pickle=False)['hydro_power'] for i in range(59)])
    hp[:,mask]=water['power'];base=compile_model(n)
    base['load']=c['source_load']-fixed_injections(hp,su.bus.map(base['buszone']).tolist(),base['zones'])
    cost=resource_costs(n,b['cost'],verified_fuel(FUEL),cost_assumptions()[0],'resource_bids');m=compiled(n,base,cost)
    return n,m,hp,mask,water,s


def offsets(n,m,hp,mask,case):
    """Only relocate Norway's unchanged fixed hydro and optionally fixed demand."""
    off=pd.DataFrame(0.,index=n.snapshots,columns=n.buses.index)
    if case=='country':return off
    su=n.storage_units.query("carrier=='hydro'")
    for j in np.flatnonzero(mask):
        bus=su.iloc[j].bus;zone=m['buszone'][bus]
        off[bus]+=hp[:,j]
        for b,w in m['weights'][zone].items():off[b]-=hp[:,j]*w
    if case=='hydro_and_demand_buses':
        ld=n.get_switchable_as_dense('Load','p_set')
        for name,row in n.loads.iterrows():
            if n.buses.loc[row.bus,'country']!='NO':continue
            off[row.bus]-=ld[name].values
            for b,w in m['weights'][m['buszone'][row.bus]].items():off[b]+=ld[name].values*w
    for keys in m['islands']:
        buses=[b for b,z in m['buszone'].items() if z in keys]
        assert abs(off[buses].sum(axis=1)).max()<1e-7,'Offset changes island energy'
    return off


def branch_offsets(n,off):
    parts=[]
    for _,row in n.sub_networks.iterrows():
        sn=row.obj
        if len(sn.buses_i())<2:continue
        sn.calculate_PTDF();parts.append(off.loc[:,sn.buses_o].values@np.asarray(sn.PTDF).T)
    return np.concatenate(parts,axis=1)


def point(h,m,t,flow_offset,delta=0.,area='1:NO'):
    cols=np.arange(m['ng']+m['nl'],dtype=np.int32);rows=np.arange(m['nz'],dtype=np.int32)
    h.changeColsBounds(len(cols),cols,np.r_[np.zeros(m['ng']),m['link_min'][t]],np.r_[m['availability'][t],m['link_max'][t]])
    h.changeColsCost(m['ng'],np.arange(m['ng'],dtype=np.int32),m['cost'][t])
    demand=m['load'][t].copy();demand[m['zones'].index(area)]+=delta
    h.changeRowsBounds(len(rows),rows,demand,demand)
    br=np.arange(m['nz']+len(m['islands']),m['A'].shape[0],dtype=np.int32)
    h.changeRowsBounds(len(br),br,-m['ratings']-flow_offset,m['ratings']-flow_offset)
    h.setOptionValue('time_limit',h.getRunTime()+10.);h.run()
    if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:
        h.clearSolver();h.setOptionValue('time_limit',h.getRunTime()+10.);h.run()
    status=h.modelStatusToString(h.getModelStatus())
    if status!='Optimal':return dict(status=status),None
    sol=h.getSolution();x=np.asarray(sol.col_value);ax=m['A']@x
    residual=max(float(abs(ax[:m['nz']]-demand).max()),float(abs(ax[m['nz']:m['nz']+len(m['islands'])]).max()),float(np.maximum(abs(ax[len(rows)+len(m['islands']):]+flow_offset)-m['ratings'],0).max()),float(np.maximum(-x[:m['ng']],0).max()),float(np.maximum(x[:m['ng']]-m['availability'][t],0).max()),float(np.maximum(m['link_min'][t]-x[m['ng']:m['ng']+m['nl']],0).max()),float(np.maximum(x[m['ng']:m['ng']+m['nl']]-m['link_max'][t],0).max()))
    if residual>1e-4:raise ValueError('Point primal replay failed')
    return dict(status=status,objective_eur=float(h.getObjectiveValue()),price_eur_mwh=float(sol.row_dual[m['zones'].index(area)]),maximum_residual_mw=residual,emergency_mw=float(x[:m['ng']][m['emergency_mask']].sum())),x


def native_point(n,m,t,offset,objective):
    p=n.copy(snapshots=n.snapshots[t:t+1])
    for c in ['StorageUnit','Store']:p.remove(c,p.df(c).index)
    for z in m['zones']:p.add('Bus','zone:'+z,carrier='AC',v_nom=380)
    p.generators.bus=p.generators.bus.map(m['buszone']).map(lambda z:'zone:'+z)
    p.generators.marginal_cost=m['native_cost'][t];p.generators_t.marginal_cost=pd.DataFrame()
    p.remove('Load',p.loads.index)
    for i,z in enumerate(m['zones']):p.add('Load','load:'+z,bus='zone:'+z,p_set=float(m['load'][t,i]))
    for b,value in offset.items():
        if abs(value)>1e-10:p.add('Load','fixed-relocation:'+b,bus=b,p_set=-float(value))
    distribution={}
    for z,ws in m['weights'].items():
        ids=[]
        for b,w in ws.items():
            name='redistribute:'+z+':'+b;ids.append((name,w));p.add('Link',name,bus0='zone:'+z,bus1=b,p_nom=1e6,p_min_pu=-1,efficiency=1)
        distribution[z]=ids
    def extra(net,snapshots):
        v=net.model['Link-p']
        for z,ids in distribution.items():
            total=v.sel(name=[name for name,_ in ids]).sum('name')
            for name,w in ids:net.model.add_constraints(v.sel(name=name)==w*total,name='gsk:'+name)
    status,condition=p.optimize(solver_name='highs',solver_options={'threads':1,'output_flag':False},extra_functionality=extra)
    if (status,condition)!=('ok','optimal'):raise ValueError('Native offset check failed')
    diff=float(p.objective-objective)
    if abs(diff)>max(.05,abs(objective)*1e-8):raise ValueError('Native offset objective mismatch')
    return dict(hour=int(t),objective_difference_eur=diff,native_objective_eur=float(p.objective))
