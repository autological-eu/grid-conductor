"""8760 independent-hour synthetic bids; physical N-0 diagnostic, no storage."""
import json,time,csv,logging
from pathlib import Path
import numpy as np
import pandas as pd
pd.set_option('future.infer_string',False)
import pypsa,highspy
from scipy.sparse import coo_matrix,csc_matrix
from synthetic_bids_2025 import SOURCE,HASH,FACTORS
from derive_physical_zonal_constraints import gsk
from hourly_renewable_estimates import digest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def compile_model(n):
    n.determine_network_topology();countries=n.buses.country;capacity=n.generators.loc[n.generators.carrier!='emergency'].groupby('bus').p_nom.sum()
    zones=[];buszone={};weights={};islands=[];branchrows=[];ratings=[]
    for name,row in n.sub_networks.iterrows():
        sn=row.obj;buses=sn.buses_i()
        if row.carrier!='AC':raise ValueError('Unsupported passive island carrier')
        if len(buses)>1:
            sn.calculate_PTDF();buses=sn.buses_o;H=np.asarray(sn.PTDF)
        else:H=np.zeros((0,len(buses)))
        zs,W=gsk(buses,countries,capacity);keys=[str(name)+':'+z for z in zs];offset=len(zones);zones+=keys
        for i,b in enumerate(buses):buszone[b]=keys[zs.index(countries[b])]
        for j,k in enumerate(keys):weights[k]={b:float(W[i,j]) for i,b in enumerate(buses) if W[i,j]>0}
        islands.append(keys)
        for i,(comp,b) in enumerate(sn.branches_i()):
            r=n.df(comp).loc[b];limit=float(r.s_nom*r.s_max_pu)
            if not np.isfinite(limit) or limit<=0:raise ValueError('Invalid rating')
            branchrows.append((dict(zip(keys,(H[i]@W).tolist())),dict(zip(buses,H[i].tolist()))));ratings.append(limit)
    ng=len(n.generators);nl=len(n.links);nz=len(zones);cols=ng+nl+nz
    zi={z:i for i,z in enumerate(zones)};gz=[buszone[b] for b in n.generators.bus]
    ld=n.get_switchable_as_dense('Load','p_set').T.groupby(n.loads.bus.map(buszone)).sum().T.reindex(columns=zones,fill_value=0).values
    if not np.isfinite(ld).all() or (ld<0).any():raise ValueError('Invalid original load')
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    costs=n.get_switchable_as_dense('Generator','marginal_cost').values.copy()
    for j,(_,g) in enumerate(n.generators.iterrows()):
        if g.carrier in FACTORS:
            if not 0<g.efficiency<=1:raise ValueError('Missing efficiency')
            costs[:,j]+=80*FACTORS[g.carrier]/g.efficiency
        elif g.carrier in ['solar','solar-hsat','onwind','offwind-ac','offwind-dc','offwind-float']:costs[:,j]=-5
    if n.generators.p_nom_extendable.any() or n.generators.committable.any() or n.links.p_nom_extendable.any():raise ValueError('Unsupported expansion/commitment')
    if any(not n.pnl(c).get(k,pd.DataFrame()).empty for c,k in [('Line','s_max_pu'),('Transformer','s_max_pu'),('Link','efficiency')]):raise ValueError('Unsupported temporal network parameters')
    if not np.isfinite(av).all() or (av<0).any():raise ValueError('Invalid original availability')
    if np.any(n.get_switchable_as_dense('Generator','p_min_pu').values!=0):raise ValueError('Unsupported nonzero generation minimum')
    lpmin=n.get_switchable_as_dense('Link','p_min_pu').values*n.links.p_nom.values
    lpmax=n.get_switchable_as_dense('Link','p_max_pu').values*n.links.p_nom.values
    efficiency=n.links.efficiency.values
    rr=[];cc=[];vv=[]
    def add(r,c,v):
        if v:rr.append(r);cc.append(c);vv.append(float(v))
    # Variables generation, signed native Link-p, zonal net injection.
    for j,z in enumerate(gz):add(zi[z],j,1)
    for z,i in zi.items():add(i,ng+nl+i,-1)
    for k,keys in enumerate(islands):
        r=nz+k
        for z in keys:add(r,ng+nl+zi[z],1)
        for j,(_,e) in enumerate(n.links.iterrows()):
            if buszone[e.bus0] in keys:add(r,ng+j,-1)
            if buszone[e.bus1] in keys:add(r,ng+j,efficiency[j])
    for k,(Z,H) in enumerate(branchrows):
        r=nz+len(islands)+k
        for z,v in Z.items():add(r,ng+nl+zi[z],v)
        for j,(_,e) in enumerate(n.links.iterrows()):add(r,ng+j,-H.get(e.bus0,0)+efficiency[j]*H.get(e.bus1,0))
    A=coo_matrix((vv,(rr,cc)),shape=(nz+len(islands)+len(branchrows),cols)).tocsc()
    return dict(zones=zones,weights=weights,buszone=buszone,islands=islands,ratings=np.array(ratings),A=A,load=ld,availability=av,cost=costs,link_min=lpmin,link_max=lpmax,ng=ng,nl=nl,nz=nz)

def solver(m):
    ng,nl,nz=m['ng'],m['nl'],m['nz'];A=m['A'];h=highspy.Highs();h.setOptionValue('output_flag',False);h.setOptionValue('threads',1);h.setOptionValue('solver','simplex')
    lp=highspy.HighsLp();lp.num_col_=A.shape[1];lp.num_row_=A.shape[0];lp.col_cost_=np.r_[m['cost'][0],np.zeros(nl+nz)];lp.col_lower_=np.r_[np.zeros(ng),m['link_min'][0],np.full(nz,-np.inf)];lp.col_upper_=np.r_[m['availability'][0],m['link_max'][0],np.full(nz,np.inf)]
    lo=np.r_[m['load'][0],np.zeros(len(m['islands'])),-m['ratings']];hi=np.r_[m['load'][0],np.zeros(len(m['islands'])),m['ratings']]
    lp.row_lower_=lo;lp.row_upper_=hi;lp.a_matrix_.format_=highspy.MatrixFormat.kColwise;lp.a_matrix_.start_=A.indptr;lp.a_matrix_.index_=A.indices;lp.a_matrix_.value_=A.data;h.passModel(lp);return h

def native_check(n,m,t,objective):
    p=n.copy(snapshots=n.snapshots[t:t+1])
    for c in ['StorageUnit','Store']:p.remove(c,p.df(c).index)
    for z in m['zones']:p.add('Bus','zone:'+z,carrier='AC',v_nom=380)
    p.generators.bus=p.generators.bus.map(m['buszone']).map(lambda z:'zone:'+z)
    p.generators.marginal_cost=m['cost'][t];p.generators_t.marginal_cost=pd.DataFrame()
    p.remove('Load',p.loads.index)
    for i,z in enumerate(m['zones']):p.add('Load','load:'+z,bus='zone:'+z,p_set=float(m['load'][t,i]))
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
    if status!='ok' or condition!='optimal':raise ValueError('Native GSK solve failed')
    difference=float(p.objective-objective)
    if abs(difference)>max(.05,abs(objective)*1e-8):raise ValueError('Native objective mismatch')
    return dict(utc=str(n.snapshots[t]),native_objective_eur=float(p.objective),fast_objective_eur=float(objective),difference_eur=difference)

def run():
    logging.getLogger('pypsa').setLevel(logging.WARNING)
    if digest(SOURCE)!=HASH:raise ValueError('Source changed')
    n=pypsa.Network(SOURCE)
    np.testing.assert_array_equal(n.snapshots.values,pd.date_range('2025-01-01',periods=8760,freq='h').values)
    np.testing.assert_allclose(n.snapshot_weightings.generators,1)
    started=time.perf_counter()
    n.determine_network_topology();original_generators=len(n.generators)
    for (_,country),bs in n.buses.groupby(['sub_network','country']):
        n.add('Generator','emergency:'+bs.index[0],bus=bs.index[0],p_nom=1e6,marginal_cost=10000,carrier='emergency')
    m=compile_model(n);h=solver(m);compile_seconds=time.perf_counter()-started
    folder=ROOT/'data/synthetic-europe-physical-2025';folder.mkdir(exist_ok=True)
    prices=[];objectives=[];shortages=[];zone_generation=[];zone_shortage=[];cold_retries=[];max_residual=0.;examples=[];start=time.perf_counter()
    generator_zones=n.generators.bus.map(m['buszone']).values;emergency_mask=n.generators.carrier.values=='emergency'
    selected={348,4692,8364};cols=np.arange(m['ng']+m['nl'],dtype=np.int32);gcols=np.arange(m['ng'],dtype=np.int32);zrows=np.arange(m['nz'],dtype=np.int32)
    for t in range(8760):
        lower=np.r_[np.zeros(m['ng']),m['link_min'][t]];upper=np.r_[m['availability'][t],m['link_max'][t]]
        h.changeColsBounds(len(cols),cols,lower,upper);h.changeColsCost(m['ng'],gcols,m['cost'][t]);h.changeRowsBounds(m['nz'],zrows,m['load'][t],m['load'][t]);h.run()
        if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:
            cold_retries.append(dict(hour=t,warm_status=str(h.getModelStatus())));h.clearSolver();h.run()
        if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:
            (folder/'failure.json').write_text(json.dumps(dict(hour=t,status=str(h.getModelStatus()))));raise ValueError(f'Hourly solve failed at {t}: {h.getModelStatus()}')
        sol=h.getSolution();x=np.array(sol.col_value);flows=m['A']@x
        residual=max(float(abs(flows[:m['nz']]-m['load'][t]).max()),float(abs(flows[m['nz']:m['nz']+len(m['islands'])]).max()),float(np.maximum(abs(flows[m['nz']+len(m['islands']):])-m['ratings'],0).max()),float(np.maximum(lower-x[:len(cols)],0).max()),float(np.maximum(x[:len(cols)]-upper,0).max()))
        if residual>1e-4:raise ValueError('Independent primal residual failed')
        max_residual=max(max_residual,residual);prices.append(sol.row_dual[:m['nz']]);objectives.append(h.getObjectiveValue());shortages.append(float(x[original_generators:m['ng']].sum()))
        zone_generation.append([float(x[:m['ng']][generator_zones==z].sum()) for z in m['zones']]);zone_shortage.append([float(x[:m['ng']][(generator_zones==z)&(emergency_mask)].sum()) for z in m['zones']])
        if t in selected:examples.append((t,x.copy(),objectives[-1]))
        if t%1000==0:print(t,flush=True)
    solve_seconds=time.perf_counter()-start
    np.savez_compressed(folder/'hourly.npz',prices=np.array(prices),objectives=np.array(objectives),zone_generation=np.array(zone_generation),zone_shortage=np.array(zone_shortage))
    checks=[native_check(n,m,t,obj) for t,_,obj in examples]
    out=ROOT/'public/research/european-physical-bids-2025';out.mkdir(exist_ok=True)
    p=np.array(prices);zg=np.array(zone_generation);zs=np.array(zone_shortage)
    areas=[dict(area=z,demand_twh=float(m['load'][:,i].sum()/1e6),primary_generation_twh=float((zg[:,i]-zs[:,i]).sum()/1e6),emergency_supply_twh=float(zs[:,i].sum()/1e6),shortage_hours=int(np.count_nonzero(zs[:,i]>1e-6)),mean_price_eur_mwh=float(p[:,i].mean())) for i,z in enumerate(m['zones'])]
    with (out/'area-summary.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(areas[0]));writer.writeheader();writer.writerows(areas)
    fig,ax=plt.subplots(figsize=(12,6),layout='constrained');ordered=sorted(areas,key=lambda r:r['emergency_supply_twh'],reverse=True);ax.bar([a['area'] for a in ordered],[a['emergency_supply_twh'] for a in ordered]);ax.tick_params(axis='x',rotation=90);ax.set(ylabel='Emergency supply TWh',title='Full-year shortages by country/island area — no storage scheduling');fig.savefig(out/'area-shortages.svg');plt.close(fig)
    de=m['zones'].index('0:DE');observed=np.array([np.nan if v is None else v for v in json.loads((ROOT/'public/research/zone-prices-2025/DE-LU.json').read_text())]);valid=np.isfinite(observed);error=p[valid,de]-observed[valid]
    fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained');axes[0].plot(n.snapshots[:168],p[:168,de],label='Coupled physical synthetic DE');axes[0].plot(n.snapshots[:168],observed[:168],label='Observed DE-LU');axes[0].legend();axes[0].set(ylabel='€/MWh',title='First week: country proxy versus bidding-zone observations');axes[1].hist(error,bins=60);axes[1].set(xlabel='Synthetic DE minus observed DE-LU €/MWh',ylabel='Hours',title='Descriptive full-year price errors; no calibration');fig.savefig(out/'price-comparison.svg');plt.close(fig)
    with (out/'hourly-de.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['utc','synthetic_de_eur_mwh','observed_de_lu_eur_mwh'])
        for t in range(8760):w.writerow([str(n.snapshots[t]),p[t,de],observed[t] if valid[t] else ''])
    summary=dict(status='annual_independent_hour_physical_synthetic_bid_diagnostic',hours=8760,network_sha256=HASH,producer_sha256=digest(__file__),dependency_sha256={name:digest(ROOT/'tools'/name) for name in ['synthetic_bids_2025.py','derive_physical_zonal_constraints.py','hourly_renewable_estimates.py']},observed_price_sha256=digest(ROOT/'public/research/zone-prices-2025/DE-LU.json'),solver_protocol=dict(method='simplex',threads=1,primal_replay_tolerance_mw=1e-4,native_objective_absolute_tolerance_eur=.05,native_objective_relative_tolerance=1e-8),area_summary=areas,zones=m['zones'],passive_branches=len(m['ratings']),controllable_links=m['nl'],generators=original_generators,emergency_supply_bids=m['ng']-original_generators,shortage_hours=int(np.count_nonzero(np.array(shortages)>1e-6)),shortage_mwh=float(sum(shortages)),storage_units_excluded=len(n.storage_units),compile_seconds=compile_seconds,warm_solve_seconds=solve_seconds,total_operating_cost_eur=float(sum(objectives)),maximum_primal_residual_mw=max_residual,cold_basis_retries=cold_retries,native_pypsa_checks=checks,germany_comparison=dict(observed_hours=int(valid.sum()),mae_eur_mwh=float(abs(error).mean()),bias_eur_mwh=float(error.mean()),rmse_eur_mwh=float(np.sqrt((error**2).mean()))),pypsa_version=pypsa.__version__,highs_version=h.version(),limitations=['Independent hourly solves: no storage, reservoir inflows or chronological coupling','Prepared country/island labels are not accepted bidding zones; DE versus DE-LU price comparison is a scope proxy','N-0 static ratings, no contingencies/outages/margins; zero reference','Fixed capacity GSK restricts net local injection; HVDC stays at original endpoints with native signed bounds and efficiencies','Original p_max_pu availability and demand preserved; no dispatch substituted','Synthetic costs: original plus 80 EUR/t operational carbon; wind/solar -5 EUR/MWh; no calibration or real order books','No annual native/fast storage benchmark, commercial JAO validation or investment acceptance claim'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n');print(json.dumps(summary),flush=True)
if __name__=='__main__':run()
