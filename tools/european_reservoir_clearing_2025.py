"""Chronological reservoir clearing conditional on retained reference inventories."""
import json,time,logging,csv,argparse
from pathlib import Path
import numpy as np
import pandas as pd
import pypsa,highspy
from scipy.sparse import coo_matrix,block_diag,hstack,vstack
from european_physical_bids_2025 import compile_model,ROOT
from synthetic_bids_2025 import SOURCE,HASH
from irena_linear_dispatch_capacity import load_and_apply
from hourly_renewable_estimates import digest
from submonthly_inventory_driver import verify_annual
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
REFERENCE=ROOT/'data/pypsa-eur/submonthly-coordination/stabilised-001/candidate-006'
WORKSPACE=ROOT/'data/pypsa-eur/submonthly-inventory-workspace/master-workspace.json'
FOLDER=ROOT/'data/synthetic-europe-physical-2025-irena-linear/hydro-warm-v1'

def aggregate_offers(n,m):
    groups={};zones=n.generators.bus.map(m['buszone']).values
    for j,z in enumerate(zones):
        key=(z,m['cost'][:,j].tobytes(),n.generators.iloc[j].carrier=='emergency')
        groups.setdefault(key,[]).append(j)
    entries=list(groups.items());old=m['ng'];m['native_cost']=m['cost'].copy()
    representatives=[js[0] for _,js in entries]
    # Original generator columns are identical within each area; verify before merging.
    for _,js in entries:
        for j in js[1:]:
            if (m['A'][:,j]!=m['A'][:,js[0]]).nnz:raise ValueError('Non-equivalent offer columns')
    m['A']=m['A'][:,representatives+list(range(old,m['A'].shape[1]))].tocsc()
    m['cost']=m['cost'][:,representatives];m['availability']=np.column_stack([m['availability'][:,js].sum(axis=1) for _,js in entries]);m['ng']=len(entries)
    m['offer_zones']=np.array([key[0] for key,_ in entries]);m['emergency_mask']=np.array([key[2] for key,_ in entries])
    return m

def reservoir_matrix(n,m,start,end,initial,terminal):
    ids=n.storage_units.index[n.storage_units.carrier=='hydro'];s=n.storage_units.loc[ids];nr=len(ids);T=end-start;nb=m['A'].shape[1]
    inflow=n.get_switchable_as_dense('StorageUnit','inflow').loc[:,ids].iloc[start:end].values
    power=s.p_nom.values;capacity=power*s.max_hours.values;eta=s.efficiency_dispatch.values;phi=(1-s.standing_loss.values)
    if (not np.isfinite(inflow).all() or (inflow<0).any() or np.any(s.p_min_pu.values!=0) or np.any(s.efficiency_store.values!=0) or np.any(eta<=0) or np.any(eta>1)):
        raise ValueError('Unsupported reservoir physics')
    for x in [initial,terminal]:
        if x.shape!=(nr,) or not np.isfinite(x).all() or np.any(x<0) or np.any(x>capacity+1e-6):raise ValueError('Invalid reservoir boundaries')
    if not n.storage_units_t.p_max_pu.empty:raise ValueError('Unsupported temporal turbine power')
    # Hour-major [base variables, turbine MW, end inventory MWh, spill MW].
    width=nb+3*nr;rowwidth=m['A'].shape[0]+nr
    rr=[];cc=[];vv=[];base=m['A'].tocoo()
    for t in range(T):
        rr.extend((base.row+t*rowwidth).tolist());cc.extend((base.col+t*width).tolist());vv.extend(base.data.tolist())
        for j,bus in enumerate(s.bus):
            z=m['zones'].index(m['buszone'][bus]);rr.append(t*rowwidth+z);cc.append(t*width+nb+j);vv.append(1.)
            r=t*rowwidth+m['A'].shape[0]+j
            for col,value in [(t*width+nb+j,1/eta[j]),(t*width+nb+nr+j,1),(t*width+nb+2*nr+j,1)]:rr.append(r);cc.append(col);vv.append(value)
            if t:rr.append(r);cc.append((t-1)*width+nb+nr+j);vv.append(-phi[j])
    A=coo_matrix((vv,(rr,cc)),shape=(T*rowwidth,T*width)).tocsc()
    cost=np.c_[m['cost'][start:end],np.zeros((T,m['nl']+m['nz'])),np.tile(s.marginal_cost.values,(T,1)),np.zeros((T,2*nr))].ravel()
    lower=np.c_[np.zeros((T,m['ng'])),m['link_min'][start:end],np.full((T,m['nz']),-np.inf),np.zeros((T,3*nr))]
    upper=np.c_[m['availability'][start:end],m['link_max'][start:end],np.full((T,m['nz']),np.inf),np.tile(power*s.p_max_pu.values,(T,1)),np.tile(capacity,(T,1)),inflow]
    lower[-1,nb+nr:nb+2*nr]=terminal;upper[-1,nb+nr:nb+2*nr]=terminal
    water=inflow.copy();water[0]+=phi*initial
    lo=np.c_[m['load'][start:end],np.zeros((T,len(m['islands']))),np.tile(-m['ratings'],(T,1)),water]
    hi=np.c_[m['load'][start:end],np.zeros((T,len(m['islands']))),np.tile(m['ratings'],(T,1)),water]
    return dict(A=A,cost=cost,lower=lower.ravel(),upper=upper.ravel(),row_lower=lo.ravel(),row_upper=hi.ravel(),width=width,rowwidth=rowwidth,ids=ids,initial=initial,terminal=terminal,inflow=inflow,capacity=capacity,eta=eta,phi=phi)

def solve_block(n,m,start,end,initial,terminal,limit=180):
    prep=time.perf_counter();p=reservoir_matrix(n,m,start,end,initial,terminal);A=p['A'];cached=m.get('_reservoir_cache')
    if cached and cached[0]==end-start:
        h=cached[1];columns=np.arange(A.shape[1],dtype=np.int32);rows=np.arange(A.shape[0],dtype=np.int32)
        h.changeColsBounds(len(columns),columns,p['lower'],p['upper']);h.changeColsCost(len(columns),columns,p['cost']);h.changeRowsBounds(len(rows),rows,p['row_lower'],p['row_upper'])
    else:
        h=highspy.Highs()
        for k,v in [('output_flag',False),('threads',1),('solver','simplex'),('time_limit',limit)]:h.setOptionValue(k,v)
        lp=highspy.HighsLp();lp.num_col_=A.shape[1];lp.num_row_=A.shape[0];lp.col_cost_=p['cost'];lp.col_lower_=p['lower'];lp.col_upper_=p['upper'];lp.row_lower_=p['row_lower'];lp.row_upper_=p['row_upper'];lp.a_matrix_.format_=highspy.MatrixFormat.kColwise;lp.a_matrix_.start_=A.indptr;lp.a_matrix_.index_=A.indices;lp.a_matrix_.value_=A.data
        h.passModel(lp);m['_reservoir_cache']=(end-start,h)
    preparation=time.perf_counter()-prep;started=time.perf_counter();h.run();cold_retry=False
    if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:
        cold_retry=True;h.clearSolver();h.run()
    elapsed=time.perf_counter()-started
    if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:raise ValueError('Reservoir solve not optimal: '+str(h.getModelStatus()))
    solution=h.getSolution();x=np.asarray(solution.col_value);ax=A@x
    residual=max(float(np.maximum(p['lower']-x,0).max()),float(np.maximum(x-p['upper'],0).max()),float(np.maximum(p['row_lower']-ax,0).max()),float(np.maximum(ax-p['row_upper'],0).max()))
    if residual>1e-4:raise ValueError('Independent reservoir/network residual failed')
    T=end-start;nr=len(p['ids']);nb=m['A'].shape[1];values=x.reshape(T,p['width']);power=values[:,nb:nb+nr];state=values[:,nb+nr:nb+2*nr];spill=values[:,nb+2*nr:]
    previous=np.vstack([initial,state[:-1]]);water_residual=float(abs(state-previous*p['phi']-p['inflow']+power/p['eta']+spill).max())
    if water_residual>1e-4:raise ValueError('Independent water equation failed')
    return dict(values=values,prices=np.array(solution.row_dual).reshape(T,p['rowwidth'])[:,:m['nz']],objective=float(h.getObjectiveValue()),maximum_primal_residual=residual,maximum_water_residual=water_residual,solver_seconds=elapsed,cold_retry=cold_retry,preparation_seconds=preparation,hydro_power=power,inventory=state,spill=spill)

def native_check(n,m,start,end,initial,terminal,objective):
    p=n.copy(snapshots=n.snapshots[start:end]);hydro=n.storage_units.index[n.storage_units.carrier=='hydro'];p.remove('StorageUnit',p.storage_units.index.difference(hydro));p.remove('Store',p.stores.index)
    p.storage_units.cyclic_state_of_charge=False;p.storage_units.state_of_charge_initial=pd.Series(initial,index=hydro)
    for z in m['zones']:p.add('Bus','zone:'+z,carrier='AC',v_nom=380)
    p.generators.bus=p.generators.bus.map(m['buszone']).map(lambda z:'zone:'+z);p.storage_units.bus=p.storage_units.bus.map(m['buszone']).map(lambda z:'zone:'+z)
    p.generators_t.marginal_cost=pd.DataFrame(m.get('native_cost',m['cost'])[start:end],index=p.snapshots,columns=p.generators.index)
    p.remove('Load',p.loads.index)
    for i,z in enumerate(m['zones']):p.add('Load','load:'+z,bus='zone:'+z,p_set=pd.Series(m['load'][start:end,i],index=p.snapshots))
    distribution={}
    for z,ws in m['weights'].items():
        distribution[z]=[]
        for b,w in ws.items():
            name='redistribute:'+z+':'+b;distribution[z].append((name,w));p.add('Link',name,bus0='zone:'+z,bus1=b,p_nom=1e6,p_min_pu=-1,efficiency=1)
    def extra(net,snapshots):
        v=net.model['Link-p']
        for z,ids in distribution.items():
            total=v.sel(name=[name for name,_ in ids]).sum('name')
            for name,w in ids:net.model.add_constraints(v.sel(name=name)==w*total,name='gsk:'+name)
        net.model.add_constraints(net.model['StorageUnit-state_of_charge'].sel(snapshot=snapshots[-1])==pd.Series(terminal,index=hydro).rename_axis('name').to_xarray(),name='fixed-final-reservoir')
    status,condition=p.optimize(solver_name='highs',solver_options={'threads':1,'output_flag':False,'time_limit':180},extra_functionality=extra)
    if status!='ok' or condition!='optimal':raise ValueError('Native reservoir comparison failed')
    difference=float(p.objective-objective)
    if abs(difference)>max(.05,abs(objective)*1e-8):raise ValueError('Native reservoir objective mismatch')
    return dict(hours=end-start,start_hour=start,native_objective_eur=float(p.objective),fast_objective_eur=objective,difference_eur=difference)

def setup():
    if digest(SOURCE)!=HASH:raise ValueError('Source changed')
    n=pypsa.Network(SOURCE);np.testing.assert_array_equal(n.snapshots.values,pd.date_range('2025-01-01',periods=8760,freq='h').values);np.testing.assert_array_equal(n.snapshot_weightings.stores,1)
    capacity_audit=load_and_apply(n);domain=json.loads(WORKSPACE.read_text());verify_annual(REFERENCE,domain)
    with np.load(REFERENCE/'annual-state.npz',allow_pickle=False) as a:state=a['inventories_mwh'].reshape(60,160)
    hydro=n.storage_units.index[n.storage_units.carrier=='hydro'];indices=[domain['storage_ids'].index(i) for i in hydro];states=state[:,indices].copy();caps=(n.storage_units.loc[hydro].p_nom*n.storage_units.loc[hydro].max_hours).values
    correction=float(np.maximum(-states,0).max())
    if correction>1e-6 or np.maximum(states-caps,0).max()>1e-6:raise ValueError('Reference boundary bounds fail')
    states=np.minimum(np.maximum(states,0),caps);np.testing.assert_allclose(states[0],states[-1],atol=1e-6,rtol=0)
    n.determine_network_topology();original=len(n.generators)
    for _,bs in n.buses.groupby(['sub_network','country']):n.add('Generator','emergency:'+bs.index[0],bus=bs.index[0],p_nom=1e6,marginal_cost=10000,carrier='emergency')
    return n,aggregate_offers(n,compile_model(n)),domain,states,capacity_audit,original,correction

def run(mode):
    logging.getLogger('pypsa').setLevel(logging.WARNING);FOLDER.mkdir(parents=True,exist_ok=True)
    n,m,domain,states,audit,original,correction=setup()
    if mode=='verify':
        result=solve_block(n,m,0,48,states[0],states[0]);print('Fast 48h solve seconds',result['solver_seconds'],flush=True);check=native_check(n,m,0,48,states[0],states[0],result['objective']);check['producer_sha256']=digest(__file__);(FOLDER/'native-check.json').write_text(json.dumps(check,indent=2)+'\n');print(check,flush=True);return
    check=json.loads((FOLDER/'native-check.json').read_text())
    if check['producer_sha256']!=digest(__file__):raise ValueError('Native check producer changed')
    outputs=[];rows=[];source_signature=dict(source=digest(SOURCE),producer=digest(__file__),base=digest(ROOT/'tools/european_physical_bids_2025.py'),capacity=digest(ROOT/'tools/irena_linear_dispatch_capacity.py'),annual_state=digest(REFERENCE/'annual-state.npz'),workspace=digest(WORKSPACE),gsk=digest(ROOT/'tools/derive_physical_zonal_constraints.py'),cost=digest(ROOT/'tools/synthetic_bids_2025.py'))
    manifest=FOLDER/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())!=source_signature:raise ValueError('Frozen computation identity changed')
    manifest.write_text(json.dumps(source_signature,indent=2)+'\n')
    for i,b in enumerate(domain['blocks']):
        path=FOLDER/f'{i:02d}.npz';receipt=FOLDER/f'{i:02d}.json'
        if path.exists():
            if not receipt.exists():raise ValueError('Partial block requires review')
            r=json.loads(receipt.read_text())
            if r['witness_sha256']!=digest(path):raise ValueError('Saved witness hash mismatch')
            with np.load(path,allow_pickle=False) as a:result={k:a[k] for k in a.files}
        else:
            result=solve_block(n,m,b['start_hour'],b['end_hour_exclusive'],states[i],states[i+1]);np.savez_compressed(path,**{k:v for k,v in result.items() if isinstance(v,np.ndarray)})
            r={k:v for k,v in result.items() if not isinstance(v,np.ndarray)};r.update(index=i,start_hour=b['start_hour'],end_hour=b['end_hour_exclusive'],witness_sha256=digest(path));receipt.write_text(json.dumps(r,indent=2)+'\n')
        outputs.append(result);rows.append(r);print(i,b['end_hour_exclusive'],r['solver_seconds'],flush=True)
    publish(n,m,domain,states,audit,original,correction,outputs,rows,check,source_signature)

def publish(n,m,domain,states,audit,original,correction,outputs,rows,check,signature):
    values=np.concatenate([o['values'] for o in outputs]);prices=np.concatenate([o['prices'] for o in outputs]);hp=np.concatenate([o['hydro_power'] for o in outputs]);inventory=np.concatenate([o['inventory'] for o in outputs]);spill=np.concatenate([o['spill'] for o in outputs]);hydro=n.storage_units.query("carrier=='hydro'");no=hydro.bus.map(n.buses.country).eq('NO').values
    emergency=values[:,:m['ng']][:,m['emergency_mask']].sum(axis=1);nz=m['nz'];gzone=m['offer_zones'];hzone=hydro.bus.map(m['buszone']).values
    areas=[]
    for j,z in enumerate(m['zones']):
        shortage=values[:,:m['ng']][:,(gzone==z)&m['emergency_mask']].sum(axis=1)
        areas.append(dict(area=z,demand_twh=float(m['load'][:,j].sum()/1e6),emergency_supply_twh=float(shortage.sum()/1e6),hydro_generation_twh=float(hp[:,hzone==z].sum()/1e6),shortage_hours=int(np.count_nonzero(shortage>1e-6)),mean_price_eur_mwh=float(prices[:,j].mean())))
    out=ROOT/'public/research/european-reservoir-clearing-2025';out.mkdir(exist_ok=True)
    de=m['zones'].index('0:DE');observed=np.array([np.nan if v is None else v for v in json.loads((ROOT/'public/research/zone-prices-2025/DE-LU.json').read_text())]);valid=np.isfinite(observed);error=prices[valid,de]-observed[valid]
    inflow=n.get_switchable_as_dense('StorageUnit','inflow').loc[:,hydro.index].values
    summary=dict(status='annual_conditional_reservoir_dispatch_not_annual_optimum',hours=8760,blocks=59,original_generators=original,aggregated_offers=m['ng'],hydro_units=len(hydro),other_storage_units_excluded=len(n.storage_units)-len(hydro),signature=signature,capacity_reconciliation=audit,maximum_boundary_roundoff_correction_mwh=correction,native_check=check,total_operating_cost_eur=sum(r['objective'] for r in rows),solver_seconds=sum(r['solver_seconds'] for r in rows),preparation_seconds=sum(r['preparation_seconds'] for r in rows),maximum_primal_residual_mw=max(r['maximum_primal_residual'] for r in rows),maximum_water_residual_mwh=max(r['maximum_water_residual'] for r in rows),emergency_supply_twh=float(emergency.sum()/1e6),shortage_hours=int(np.count_nonzero(emergency>1e-6)),area_summary=areas,norway=dict(hydro_generation_twh=float(hp[:,no].sum()/1e6),inflow_twh=float(inflow[:,no].sum()/1e6),spill_twh=float(spill[:,no].sum()/1e6),initial_inventory_twh=float(states[0,no].sum()/1e6),final_inventory_twh=float(inventory[-1,no].sum()/1e6)),germany=dict(mae_eur_mwh=float(abs(error).mean()),bias_eur_mwh=float(error.mean()),rmse_eur_mwh=float(np.sqrt((error**2).mean()))),limitations=['Fixed retained-reference hydro inventories at 60 boundaries; optimised hourly operation is conditional, not annual optimum','Other batteries and pumped storage excluded; hydro inflow/efficiency/standing loss preserved','Original country/island GSK and physical N-0 assumptions; bidding zones, fleet/weather/demand and hydrology not observed-data validated','Native check is 48h with equal initial/final reference inventory, not full-year native parity'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    with (out/'area-summary.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(areas[0]));w.writeheader();w.writerows(areas)
    with (out/'norway-hourly.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['utc','hydro_mw','inflow_mw','spill_mw','end_inventory_mwh'])
        for t in range(8760):w.writerow([str(n.snapshots[t]),hp[t,no].sum(),inflow[t,no].sum(),spill[t,no].sum(),inventory[t,no].sum()])
    fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained');axes[0].plot(n.snapshots,inventory[:,no].sum()/1e6);axes[0].set(ylabel='Reservoir inventory TWh',title='Norway — chronological reservoir inventory, fixed reference boundaries');axes[1].plot(n.snapshots,hp[:,no].sum()/1000,label='Turbine output');axes[1].plot(n.snapshots,inflow[:,no].sum()/1000,label='Water-energy inflow',alpha=.5);axes[1].legend();axes[1].set(ylabel='GW');fig.savefig(out/'norway-hydro.svg');plt.close(fig)
    print(json.dumps({k:summary[k] for k in ['status','solver_seconds','emergency_supply_twh','norway','germany']}),flush=True)

if __name__=='__main__':
    import fcntl,resource
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3))
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['verify','annual'],required=True);args=p.parse_args()
    FOLDER.mkdir(parents=True,exist_ok=True)
    with (FOLDER/'driver.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(args.mode)
