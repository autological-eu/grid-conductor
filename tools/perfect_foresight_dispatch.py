"""Linked hourly GSK-restricted dispatch; separate from fixed-reservoir research."""
import argparse, json, time, logging, fcntl, resource, signal
from pathlib import Path
import numpy as np
import pandas as pd
import pypsa, highspy
from scipy.sparse import coo_matrix, kron, eye
from european_reservoir_clearing_2025 import setup, aggregate_offers
from european_physical_bids_2025 import compile_model
from hourly_renewable_estimates import digest
from synthetic_bids_2025 import SOURCE


def apply_investments(n, investments, weather=None):
    """Explicit assets; topology stays fixed except added controllable transmission."""
    seen=set()
    for item in investments:
        kind=item['type']; name=item['id']
        if name in seen: raise ValueError('Duplicate investment id')
        seen.add(name)
        def positive(key):
            value=float(item[key])
            if not np.isfinite(value) or value<=0: raise ValueError('Positive finite '+key+' required')
            return value
        if kind in ('solar','wind'):
            carrier=item['carrier']; zone=item['area']
            allowed=['solar','solar-hsat'] if kind=='solar' else ['onwind','offwind-ac','offwind-dc','offwind-float']
            if carrier not in allowed: raise ValueError('Investment technology mismatch')
            # Use original per-generator availability, never realised dispatch.
            country=zone.split(':',1)[1]; island=zone.split(':',1)[0]
            buses=n.buses.index[(n.buses.country==country)&(n.buses.sub_network.astype(str)==island)]
            ids=n.generators.index[n.generators.bus.isin(buses)&(n.generators.carrier==carrier)]
            total=n.generators.loc[ids].p_nom.sum()
            if not total>0: raise ValueError('No original weather/profile fleet for area')
            old=n.generators.loc[ids,'p_nom'].copy(); added=positive('power_mw')*old/total
            profiles=n.get_switchable_as_dense('Generator','p_max_pu').copy()
            original=profiles if weather is None else weather
            profiles.loc[:,ids]=(profiles.loc[:,ids]*old+original.loc[:,ids]*added)/(old+added)
            n.generators.loc[ids,'p_nom']=old+added
            n.generators_t.p_max_pu=profiles
        elif kind=='battery':
            bus=item['bus']
            if bus not in n.buses.index or name in n.storage_units.index: raise ValueError('Invalid battery bus/id')
            power=positive('power_mw');energy=positive('energy_mwh');eta=positive('round_trip_efficiency')
            if eta>1: raise ValueError('Efficiency exceeds one')
            n.add('StorageUnit',name,bus=bus,carrier='battery',p_nom=power,max_hours=energy/power,
                  p_min_pu=-1,efficiency_store=np.sqrt(eta),efficiency_dispatch=np.sqrt(eta),
                  state_of_charge_initial=0,cyclic_state_of_charge=False)
        elif kind=='hydro':
            asset=item['asset']
            if asset not in n.storage_units.index or n.storage_units.loc[asset,'carrier'] not in ['hydro','PHS']: raise ValueError('Unknown hydro asset')
            old=n.storage_units.loc[asset]; power=old.p_nom+float(item.get('power_mw',0));energy=old.p_nom*old.max_hours+float(item.get('energy_mwh',0))
            increments=[float(item.get(k,0)) for k in ['power_mw','energy_mwh']]
            if not np.isfinite(increments).all() or min(increments)<0 or sum(increments)<=0: raise ValueError('Invalid hydro addition')
            n.storage_units.loc[asset,['p_nom','max_hours']]=[power,energy/power]
        elif kind=='transmission':
            asset=item['asset']; delta=positive('power_mw')
            if asset not in n.links.index: raise ValueError('Transmission expansion requires an original controllable link')
            n.links.loc[asset,'p_nom']+=delta
        elif kind=='new_line':
            a,b=item['bus0'],item['bus1']
            if a==b or a not in n.buses.index or b not in n.buses.index or name in n.links.index: raise ValueError('Invalid transmission endpoints/id')
            n.add('Link',name,bus0=a,bus1=b,p_nom=positive('power_mw'),p_min_pu=-1,efficiency=1,carrier='DC')
        else: raise ValueError('Unsupported investment type '+kind)
    return n


def compile_case(n, reference_model, investments, weather=None):
    # Compile network/GSK before changing renewable capacity: both cases retain
    # identical original capacity-weighted injection distribution.
    base=n.copy(); apply_investments(base,[x for x in investments if x['type'] not in ['solar','wind']])
    m=compile_model(base)
    if m['weights']!=reference_model['weights']: raise ValueError('Investment changed fixed GSK')
    apply_investments(base,[x for x in investments if x['type'] in ['solar','wind']],weather)
    m['availability']=base.get_switchable_as_dense('Generator','p_max_pu').values*base.generators.p_nom.values
    return base,aggregate_offers(base,m)


def build_lp(n,m,start,end,initial,terminal):
    T=end-start; s=n.storage_units; ns=len(s); nb=m['A'].shape[1]; nr=m['A'].shape[0]
    if T<=0 or start<0 or end>len(n.snapshots) or len(n.stores): raise ValueError('Unsupported horizon/Stores')
    if s.p_nom_extendable.any() or any(not v.empty for k,v in n.storage_units_t.items() if k!='inflow'): raise ValueError('Unsupported temporal storage/expansion')
    if np.any(s.p_max_pu<0) or np.any(s.p_min_pu>0): raise ValueError('Unsupported storage power signs')
    cap=(s.p_nom*s.max_hours).values; eta_d=s.efficiency_dispatch.values;eta_c=s.efficiency_store.values; phi=1-s.standing_loss.values
    discharge=(s.p_nom*s.p_max_pu).values; charge=(-s.p_nom*s.p_min_pu).values
    inflow=n.get_switchable_as_dense('StorageUnit','inflow').iloc[start:end].values
    for x in [initial,terminal]:
        if np.shape(x)!=(ns,) or not np.isfinite(x).all() or np.any(x<0) or np.any(x>cap+1e-6): raise ValueError('Invalid inventory boundaries')
    if not np.isfinite(inflow).all() or np.any(inflow<0) or np.any(eta_d<=0) or np.any(eta_d>1) or np.any(eta_c<0) or np.any(eta_c>1) or np.any(phi<=0) or np.any(phi>1) or np.any((charge>0)&(eta_c<=0)): raise ValueError('Invalid storage physics')
    # Hour-major [network, charge, discharge, end inventory, spill].
    width=nb+4*ns; rw=nr+ns; base=m['A'].tocoo()
    rows=[base.row];cols=[base.col];vals=[base.data]
    j=np.arange(ns); area=np.array([m['zones'].index(m['buszone'][bus]) for bus in s.bus])
    for c,v in [(nb+j,-np.ones(ns)),(nb+ns+j,np.ones(ns))]:rows.append(area);cols.append(c);vals.append(v)
    for c,v in [(nb+j,-eta_c),(nb+ns+j,1/eta_d),(nb+2*ns+j,np.ones(ns)),(nb+3*ns+j,np.ones(ns))]:rows.append(nr+j);cols.append(c);vals.append(v)
    local=coo_matrix((np.concatenate(vals),(np.concatenate(rows),np.concatenate(cols))),shape=(rw,width)).tocsc()
    previous=coo_matrix((-phi,(nr+j,nb+2*ns+j)),shape=(rw,width)).tocsc()
    A=(kron(eye(T,format='csc'),local,format='csc')+kron(eye(T,k=-1,format='csc'),previous,format='csc')).tocsc()
    water=inflow.copy();water[0]+=phi*initial
    lo=np.c_[np.zeros((T,m['ng'])),m['link_min'][start:end],np.full((T,m['nz']),-np.inf),np.zeros((T,4*ns))]
    hi=np.c_[m['availability'][start:end],m['link_max'][start:end],np.full((T,m['nz']),np.inf),np.tile(charge,(T,1)),np.tile(discharge,(T,1)),np.tile(cap,(T,1)),inflow]
    lo[-1,nb+2*ns:nb+3*ns]=terminal;hi[-1,nb+2*ns:nb+3*ns]=terminal
    cost=np.c_[m['cost'][start:end],np.zeros((T,m['nl']+m['nz']+ns)),np.tile(s.marginal_cost.values,(T,1)),np.zeros((T,2*ns))].ravel()
    rl=np.c_[m['load'][start:end],np.zeros((T,len(m['islands']))),np.tile(-m['ratings'],(T,1)),water].ravel()
    ru=np.c_[m['load'][start:end],np.zeros((T,len(m['islands']))),np.tile(m['ratings'],(T,1)),water].ravel()
    return dict(A=A,cost=cost,lower=lo.ravel(),upper=hi.ravel(),row_lower=rl,row_upper=ru,width=width,rowwidth=rw,ns=ns,nb=nb,inflow=inflow,eta_c=eta_c,eta_d=eta_d,phi=phi,initial=initial,terminal=terminal)


def solve(n,m,start,end,initial,terminal,time_limit=180):
    # Conservative preflight: matrix copies/factorisation and dense bounds can
    # multiply raw sparse storage. This is a planning guard, not peak-RSS proof.
    hours=end-start; ns=len(n.storage_units)
    estimated_bytes=hours*(m['A'].nnz+9*ns)*12*4 + hours*(m['A'].shape[1]+4*ns)*8*10
    if estimated_bytes>4*1024**3: raise ValueError(f'Full linked matrix estimate {estimated_bytes/1024**3:.2f} GiB exceeds 4 GiB working budget; annual needs sparse reduction or coordinated optimisation')
    begin=time.perf_counter();p=build_lp(n,m,start,end,initial,terminal);A=p['A'];prep=time.perf_counter()-begin
    h=highspy.Highs()
    for k,v in [('output_flag',False),('threads',1),('solver','ipm'),('time_limit',time_limit)]: h.setOptionValue(k,v)
    lp=highspy.HighsLp();lp.num_col_=A.shape[1];lp.num_row_=A.shape[0];lp.col_cost_=p['cost'];lp.col_lower_=p['lower'];lp.col_upper_=p['upper'];lp.row_lower_=p['row_lower'];lp.row_upper_=p['row_upper'];lp.a_matrix_.format_=highspy.MatrixFormat.kColwise;lp.a_matrix_.start_=A.indptr;lp.a_matrix_.index_=A.indices;lp.a_matrix_.value_=A.data
    h.passModel(lp);begin=time.perf_counter();h.run();elapsed=time.perf_counter()-begin
    if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal: raise ValueError('Perfect foresight not optimal: '+str(h.getModelStatus()))
    sol=h.getSolution();x=np.asarray(sol.col_value);ax=A@x
    residual=max(float(np.maximum(p['lower']-x,0).max()),float(np.maximum(x-p['upper'],0).max()),float(np.maximum(p['row_lower']-ax,0).max()),float(np.maximum(ax-p['row_upper'],0).max()))
    if residual>1e-4: raise ValueError('Primal replay failed')
    values=x.reshape(end-start,p['width']);nb=p['nb'];ns=p['ns'];c=values[:,nb:nb+ns];d=values[:,nb+ns:nb+2*ns];soc=values[:,nb+2*ns:nb+3*ns];spill=values[:,nb+3*ns:];prev=np.vstack([initial,soc[:-1]])
    water=float(abs(soc-prev*p['phi']-c*p['eta_c']+d/p['eta_d']-p['inflow']+spill).max())
    if water>1e-4 or np.max(abs(soc[-1]-terminal))>1e-4: raise ValueError('Inventory replay failed')
    return dict(values=values,prices=np.asarray(sol.row_dual).reshape(end-start,p['rowwidth'])[:,:m['nz']],objective=float(h.getObjectiveValue()),maximum_primal_residual=residual,maximum_inventory_residual=water,simultaneous_storage_hours=int(np.count_nonzero((c>1e-6)&(d>1e-6))),solver_seconds=elapsed,preparation_seconds=prep,variables=A.shape[1],rows=A.shape[0],nonzeros=A.nnz)


def native_check(n,m,start,end,initial,terminal,objective):
    p=n.copy(snapshots=n.snapshots[start:end]);p.remove('GlobalConstraint',p.global_constraints.index)
    p.storage_units.cyclic_state_of_charge=False;p.storage_units.state_of_charge_initial=pd.Series(initial,index=p.storage_units.index)
    for z in m['zones']:p.add('Bus','zone:'+z,carrier='AC',v_nom=380)
    p.generators.bus=p.generators.bus.map(m['buszone']).map(lambda z:'zone:'+z);p.storage_units.bus=p.storage_units.bus.map(m['buszone']).map(lambda z:'zone:'+z)
    p.generators_t.marginal_cost=pd.DataFrame(m['native_cost'][start:end],index=p.snapshots,columns=p.generators.index)
    p.remove('Load',p.loads.index)
    for i,z in enumerate(m['zones']):p.add('Load','load:'+z,bus='zone:'+z,p_set=pd.Series(m['load'][start:end,i],index=p.snapshots))
    dist={}
    for z,ws in m['weights'].items():
        dist[z]=[]
        for bus,w in ws.items():
            name='redistribute:'+z+':'+bus;dist[z].append((name,w));p.add('Link',name,bus0='zone:'+z,bus1=bus,p_nom=1e6,p_min_pu=-1,efficiency=1)
    def extra(net,snapshots):
        v=net.model['Link-p']
        for z,ids in dist.items():
            total=v.sel(name=[name for name,_ in ids]).sum('name')
            for name,w in ids:net.model.add_constraints(v.sel(name=name)==w*total,name='gsk:'+name)
        net.model.add_constraints(net.model['StorageUnit-state_of_charge'].sel(snapshot=snapshots[-1])==pd.Series(terminal,index=p.storage_units.index).rename_axis('name').to_xarray(),name='fixed-final')
    status,condition=p.optimize(solver_name='highs',solver_options={'threads':1,'output_flag':False,'time_limit':180},extra_functionality=extra)
    if status!='ok' or condition!='optimal':raise ValueError('Native perfect foresight failed')
    difference=float(p.objective-objective)
    if abs(difference)>max(.05,abs(objective)*1e-8):raise ValueError('Native objective mismatch')
    return dict(native_objective_eur=float(p.objective),difference_eur=difference)


def run(args):
    n,reference,domain,states,audit,original,correction=setup()
    with np.load(Path(__file__).resolve().parents[1]/'data/pypsa-eur/submonthly-coordination/stabilised-001/candidate-006/annual-state.npz') as f: initial=f['inventories_mwh'].reshape(60,160)[0].copy()
    np.testing.assert_array_equal(n.storage_units.index.values, np.array(domain['storage_ids']))
    initial=np.maximum(initial,0);terminal=initial.copy()
    investments=json.loads(Path(args.investments).read_text()) if args.investments else []
    records=[];provenance={'source':digest(SOURCE),'producer':digest(__file__),'investments':investments,'capacity_audit':audit,'hours':args.hours,'start_hour':args.start_hour,'initial_reference':'retained candidate-006 start inventory; no intermediate fixed boundaries','initial_inventory_mwh':initial.tolist(),'dependencies':{name:digest(Path(__file__).with_name(name)) for name in ['european_reservoir_clearing_2025.py','european_physical_bids_2025.py','irena_linear_dispatch_capacity.py','synthetic_bids_2025.py','derive_physical_zonal_constraints.py']}}
    weather=pypsa.Network(SOURCE).get_switchable_as_dense('Generator','p_max_pu').copy()
    provenance['package_versions']={'python':__import__('platform').python_version(),'pypsa':pypsa.__version__,'numpy':np.__version__,'scipy':__import__('scipy').__version__,'highs':highspy.Highs().version()}
    provenance['boundary_sha256']=digest(Path(__file__).resolve().parents[1]/'data/pypsa-eur/submonthly-coordination/stabilised-001/candidate-006/annual-state.npz')
    (args.output/'manifest.json').write_text(json.dumps(provenance,indent=2,allow_nan=False)+'\n')
    cases=[('baseline',[])]+([('investment',investments)] if investments else [])
    for label,items in cases:
        case,m=compile_case(n,reference,items,weather);extra=len(case.storage_units)-len(initial);i=np.r_[initial,np.zeros(extra)];t=np.r_[terminal,np.zeros(extra)]
        result=solve(case,m,args.start_hour,args.start_hour+args.hours,i,t,args.time_limit)
        if args.native: result['native_check']=native_check(case,m,args.start_hour,args.start_hour+args.hours,i,t,result['objective'])
        np.savez_compressed(args.output/(label+'.npz'),**{k:v for k,v in result.items() if isinstance(v,np.ndarray)})
        result={k:v for k,v in result.items() if not isinstance(v,np.ndarray)};result['case']=label;result['witness_sha256']=digest(args.output/(label+'.npz'));records.append(result)
        print(json.dumps(result),flush=True)
    summary={'provenance':provenance,'cases':records,'operating_cost_change_eur':records[1]['objective']-records[0]['objective'] if len(records)==2 else None,'status':'numerically_verified_window' if args.native else 'primal_replayed_dispatch','limitations':['Perfect foresight, fixed original GSK, N-0 physical constraints; not actual EUPHEMIA','Observed bidding-zone and prices, annual and investment acceptance gates remain open','Continuous LP allows simultaneous charge/discharge; count reported, not hidden','Global constraints from source excluded as in synthetic-bid research; no emissions cap','No lifecycle-emissions result: offer aggregation and complete factor coverage require a separate audit','New line is controllable lossless transmission, not a passive AC circuit','Hydro expansion retains inflow; renewable additions reuse original spatial/weather profiles']}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.WARNING)
    parser=argparse.ArgumentParser();parser.add_argument('--hours',type=int,default=48);parser.add_argument('--start-hour',type=int,default=0);parser.add_argument('--investments');parser.add_argument('--native',action='store_true');parser.add_argument('--time-limit',type=float,default=180);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.hours<1 or args.start_hour<0 or args.start_hour+args.hours>8760 or not np.isfinite(args.time_limit) or args.time_limit<=0:parser.error('Invalid horizon/time budget')
    resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
    signal.alarm(int(2*(args.time_limit+180)+300))
    args.output.mkdir(parents=True,exist_ok=True)
    if (args.output/'summary.json').exists() or any(args.output.glob('*.npz')):parser.error('Use a fresh output root; never overwrite witnesses')
    with (args.output/'driver.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        status=args.output/'status.json'
        status.write_text(json.dumps({'status':'running','pid':__import__('os').getpid()})+'\n')
        try:
            run(args)
        except Exception as exc:
            status.write_text(json.dumps({'status':'failed','error':str(exc)})+'\n')
            raise
        status.write_text(json.dumps({'status':'completed','summary_sha256':digest(args.output/'summary.json')})+'\n')
