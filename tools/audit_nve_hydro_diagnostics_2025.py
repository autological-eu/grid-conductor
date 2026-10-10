"""Replay saved geography/window witnesses from native component physics."""
import json, logging, resource, signal
import numpy as np
import pandas as pd
from nve_hydro_diagnostics import ROOT, NVE, rebuild, digest

BASE = ROOT/'data/hydro-observations-2025'

def read(folder, producer, witness):
    s=json.loads((folder/'summary.json').read_text())
    assert s['producer_sha256']==digest(ROOT/'tools'/producer)
    assert s['helper_sha256']==digest(ROOT/'tools/nve_hydro_diagnostics.py')
    assert s['witness_sha256']==digest(folder/witness)
    assert s['nve_summary_sha256']==digest(NVE/'summary.json')
    return s

def displacement(n,m,power,mask,start,case):
    T=len(power);out=pd.DataFrame(0.,index=range(T),columns=n.buses.index)
    if case=='country':return out
    su=n.storage_units.query("carrier=='hydro'").iloc[np.flatnonzero(mask)]
    for j,b in enumerate(su.bus):
        out[b]+=power[:,j]
        for bus,w in m['weights'][m['buszone'][b]].items():out[bus]-=w*power[:,j]
    if case=='hydro_buses':return out
    loads=n.get_switchable_as_dense('Load','p_set').iloc[start:start+T]
    for name,row in n.loads.iterrows():
        if n.buses.loc[row.bus,'country']=='NO':
            out[row.bus]-=loads[name].values
            for b,w in m['weights'][m['buszone'][row.bus]].items():out[b]+=w*loads[name].values
    return out

def physics(n,m,x,demand,off,start):
    ng,nl=m['ng'],m['nl'];T=len(x);g=x[:,:ng];f=x[:,ng:ng+nl];q=x[:,ng+nl:]
    supply=np.zeros((T,m['nz']))
    for j,z in enumerate(m['offer_zones']):supply[:,m['zones'].index(z)]+=g[:,j]
    checks=[float(abs(supply-demand-q).max())]
    for v,lo,hi in [(g,0,m['availability'][start:start+T]),(f,m['link_min'][start:start+T],m['link_max'][start:start+T])]:
        checks.extend([float(np.maximum(lo-v,0).max()),float(np.maximum(v-hi,0).max())])
    for z,ws in m['weights'].items():
        for b,w in ws.items():off[b]+=w*q[:,m['zones'].index(z)]
    for j,(_,e) in enumerate(n.links.iterrows()):off[e.bus0]-=f[:,j];off[e.bus1]+=e.efficiency*f[:,j]
    for _,row in n.sub_networks.iterrows():
        sn=row.obj;checks.append(float(abs(off[sn.buses_i()].sum(axis=1)).max()))
        if len(sn.buses_i())<2:continue
        sn.calculate_PTDF();flows=off[sn.buses_o].values@np.asarray(sn.PTDF).T
        limits=np.array([n.df(c).loc[name].s_nom*n.df(c).loc[name].s_max_pu for c,name in sn.branches_i()])
        checks.append(float(np.maximum(abs(flows)-limits,0).max()))
    assert max(checks)<=1e-4, checks
    return max(checks)

def audit():
    n,m,hp,mask,water,_=rebuild();annual=BASE/'bus-geography-annual-v1';windows=BASE/'bounded-windows-v1'
    a=read(annual,'run_nve_bus_geography_2025.py','annual.npz')
    w=read(windows,'run_nve_hydro_windows_2025.py','windows.npz')
    assert w['annual_geography_summary_sha256']==digest(annual/'summary.json')
    assert w['flexibility_sha256']==digest(ROOT/'tools/nve_hydro_flexibility.py')
    points=read(BASE/'price-geography-v1','diagnose_nve_hydro_prices_2025.py','points.npz')
    point_rows=[]
    with np.load(BASE/'price-geography-v1/points.npz',allow_pickle=False) as saved:
        for case, records in points['cases'].items():
            for r in records['records']:
                if r['status']!='Optimal':continue
                t=r['hour'];v=saved[case+'_'+str(t)][None,:]
                residual=physics(n,m,v,m['load'][t:t+1],displacement(n,m,hp[t:t+1][:,mask],mask,t,case),t)
                obj=float((v[0,:m['ng']]*m['cost'][t]).sum())
                assert abs(obj-r['objective_eur'])<=max(.05,abs(obj)*1e-8)
                point_rows.append(dict(hour=t,case=case,network_residual_mw=residual))
    with np.load(annual/'annual.npz',allow_pickle=False) as z:
        x=z['values'];objectives=z['objectives'];assert z['optimal'].all()
    off=displacement(n,m,hp[:,mask],mask,0,'hydro_and_demand_buses')
    residual=physics(n,m,x,m['load'],off,0)
    np.testing.assert_allclose((x[:,:m['ng']]*m['cost']).sum(axis=1),objectives,rtol=1e-8,atol=.05)
    previous=np.vstack([water['initial'],water['inventory'][:-1]])
    error=float(abs(water['inventory']-previous-water['inflow']+water['power']/water['eta']+water['spill']).max())
    assert error<=1e-4
    # Aggregate offers lose same-price generator identity; retain rigorous ROR bounds.
    availability=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    groups={}
    for j,name in enumerate(n.generators.index):
        z=m['buszone'][n.generators.loc[name].bus]
        key=(z,m['native_cost'][:,j].tobytes(),n.generators.loc[name].carrier=='emergency')
        groups.setdefault(key,[]).append(j)
    lo=hi=0.
    for k,ids in enumerate(groups.values()):
        r=[j for j in ids if n.generators.iloc[j].carrier=='ror' and n.buses.loc[n.generators.iloc[j].bus,'country']=='NO']
        if not r:continue
        other=[j for j in ids if j not in r];ra=availability[:,r].sum(axis=1)
        oa=availability[:,other].sum(axis=1) if other else np.zeros(8760)
        lo+=np.maximum(x[:,k]-oa,0).sum()/1e6;hi+=np.minimum(x[:,k],ra).sum()/1e6
    reservoir=float(water['power'].sum()/1e6);rows=[]
    su=n.storage_units.query("carrier=='hydro'").iloc[np.flatnonzero(mask)]
    with np.load(windows/'windows.npz',allow_pickle=False) as saved:
        for record in w['records']:
            assert record['status']=='Optimal';start,end=record['start_hour'],record['end_hour_exclusive'];case=record['case'];prefix=record['label']+'_'+case+'_'
            p,e,v=[saved[prefix+k] for k in ['power','inventory','values']];ref=hp[start:end][:,mask]
            initial=water['initial'] if start==0 else water['inventory'][start-1]
            prev=np.vstack([initial,e[:-1]])
            checks=[float(abs(e-prev-water['inflow'][start:end]+p/water['eta']+water['spill'][start:end]).max()),float(abs(e[-1]-water['inventory'][end-1]).max()),float(abs(p.sum(axis=0)-ref.sum(axis=0)).max()),float(np.maximum(.8*ref-p,0).max()),float(np.maximum(p-np.minimum(1.2*ref,su.p_nom.values),0).max()),float(np.maximum(-e,0).max()),float(np.maximum(e-water['capacity'],0).max())]
            assert max(checks)<=1e-4
            demand=m['load'][start:end].copy()
            for j,b in enumerate(su.bus):demand[:,m['zones'].index(m['buszone'][b])]+=ref[:,j]-p[:,j]
            network=physics(n,m,v,demand,displacement(n,m,p,mask,start,case),start)
            obj=float((v[:,:m['ng']]*m['cost'][start:end]).sum())
            assert abs(obj-record['objective_eur'])<=max(.05,abs(obj)*1e-8)
            rows.append(dict(label=record['label'],case=case,water_bounds_energy_residual_mwh=max(checks),network_residual_mw=network,objective_replay_error_eur=obj-record['objective_eur']))
    result=dict(status='saved_component_replay_passed',annual_summary_sha256=digest(annual/'summary.json'),window_summary_sha256=digest(windows/'summary.json'),point_summary_sha256=digest(BASE/'price-geography-v1/summary.json'),audit_producer_sha256=digest(__file__),annual_network_residual_mw=residual,annual_water_residual_mwh=error,reservoir_twh=reservoir,ror_bounds_twh=[lo,hi],total_hydro_bounds_twh=[reservoir+lo,reservoir+hi],windows=rows,points=point_rows,source_no_demand_twh=w['source_no_demand_twh'],note='Annual producer fixed_no_hydro_twh inherits prior ROR dispatch bounds. Use the freshly replayed bounds here for the relocated case. Price perturbation/infeasibility/native checks are producer evidence; saved feasible point, annual and window witnesses are independently component-replayed here.')
    (annual/'diagnostic-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(600);audit()
