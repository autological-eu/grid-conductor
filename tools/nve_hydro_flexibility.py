"""Bounded chronological window diagnostic, unchanged water and closing stocks."""
import numpy as np
import pandas as pd
import highspy
from scipy.sparse import coo_matrix
from nve_hydro_diagnostics import offsets,branch_offsets


def solve_window(n,m,hp,mask,water,start,end,case,fraction=.2):
    ids=n.storage_units.query("carrier=='hydro'").index[mask];su=n.storage_units.loc[ids]
    assert np.all(su.standing_loss==0),'Unsupported nonzero standing losses'
    T=end-start;nr=len(ids);nb=m['A'].shape[1];rb=m['A'].shape[0];width=nb+2*nr;rows=rb+nr
    initial=water['initial'] if start==0 else water['inventory'][start-1]
    terminal=water['inventory'][end-1];eta=water['eta'];ref=hp[start:end][:,mask]
    assert 0<=fraction<=1
    pmin=ref*(1-fraction);pmax=np.minimum(ref*(1+fraction),su.p_nom.values)
    demand_offset=offsets(n,m,hp,mask,'hydro_and_demand_buses')-offsets(n,m,hp,mask,'hydro_buses') if case=='hydro_and_demand_buses' else pd.DataFrame(0.,index=n.snapshots,columns=n.buses.index)
    foff=branch_offsets(n,demand_offset)[start:end]
    coeff=np.zeros((len(m['ratings']),nr));cursor=0
    for _,row in n.sub_networks.iterrows():
        sn=row.obj
        if len(sn.buses_i())<2:continue
        sn.calculate_PTDF();H=np.asarray(sn.PTDF);buses=sn.buses_o
        if case!='country':
            for j,b in enumerate(su.bus):
                if b not in buses:continue
                z=m['buszone'][b];vector=np.array([float(x==b)-m['weights'][z].get(x,0.) for x in buses])
                coeff[cursor:cursor+len(H),j]=H@vector
        cursor+=len(H)
    rr=[];cc=[];vv=[];orig=m['A'].tocoo();cost=[];lo=[];hi=[];rowlo=[];rowhi=[]
    for k,t in enumerate(range(start,end)):
        rr.extend((orig.row+k*rows).tolist());cc.extend((orig.col+k*width).tolist());vv.extend(orig.data.tolist())
        cost.extend(np.r_[m['cost'][t],np.zeros(m['nl']+m['nz']+2*nr)])
        lo.extend(np.r_[np.zeros(m['ng']),m['link_min'][t],np.full(m['nz'],-np.inf),pmin[k],np.zeros(nr)])
        hi.extend(np.r_[m['availability'][t],m['link_max'][t],np.full(m['nz'],np.inf),pmax[k],water['capacity']])
        demand=m['load'][t].copy()
        for j,b in enumerate(su.bus):demand[m['zones'].index(m['buszone'][b])]+=ref[k,j]
        rowlo.extend(np.r_[demand,np.zeros(len(m['islands'])),-m['ratings']-foff[k]])
        rowhi.extend(np.r_[demand,np.zeros(len(m['islands'])),m['ratings']-foff[k]])
        for j,b in enumerate(su.bus):
            z=m['zones'].index(m['buszone'][b]);rr.append(k*rows+z);cc.append(k*width+nb+j);vv.append(1.)
            for br,value in enumerate(coeff[:,j]):
                if value:rr.append(k*rows+m['nz']+len(m['islands'])+br);cc.append(k*width+nb+j);vv.append(value)
            row=k*rows+rb+j
            for column,value in [(k*width+nb+j,1/eta[j]),(k*width+nb+nr+j,1.)]:rr.append(row);cc.append(column);vv.append(value)
            rhs=water['inflow'][t,j]-water['spill'][t,j]
            if k:rr.append(row);cc.append((k-1)*width+nb+nr+j);vv.append(-1.)
            else:rhs+=initial[j]
            rowlo.append(rhs);rowhi.append(rhs)
    lo=np.array(lo);hi=np.array(hi);lo[-nr:]=terminal;hi[-nr:]=terminal
    A=coo_matrix((vv,(rr,cc)),shape=(T*rows,T*width)).tocsc();lp=highspy.HighsLp();lp.num_col_=A.shape[1];lp.num_row_=A.shape[0]
    lp.col_cost_=np.array(cost);lp.col_lower_=lo;lp.col_upper_=hi;lp.row_lower_=np.array(rowlo);lp.row_upper_=np.array(rowhi)
    lp.a_matrix_.format_=highspy.MatrixFormat.kColwise;lp.a_matrix_.start_=A.indptr;lp.a_matrix_.index_=A.indices;lp.a_matrix_.value_=A.data
    h=highspy.Highs()
    for key,value in [('threads',1),('output_flag',False),('solver','simplex'),('time_limit',90.),('primal_feasibility_tolerance',1e-8)]:h.setOptionValue(key,value)
    h.passModel(lp);h.run();status=h.modelStatusToString(h.getModelStatus())
    if status!='Optimal':return dict(status=status),None
    x=np.asarray(h.getSolution().col_value);ax=A@x
    residual=max(float(np.maximum(lo-x,0).max()),float(np.maximum(x-hi,0).max()),float(np.maximum(lp.row_lower_-ax,0).max()),float(np.maximum(ax-lp.row_upper_,0).max()))
    if residual>1e-4:raise ValueError('Flexible window primal failed')
    matrix=x.reshape(T,width);power=matrix[:,nb:nb+nr];inventory=matrix[:,nb+nr:]
    previous=np.vstack([initial,inventory[:-1]])
    water_error=float(abs(inventory-previous-water['inflow'][start:end]+power/eta+water['spill'][start:end]).max())
    if water_error>1e-4:raise ValueError('Window water replay failed')
    prices=np.asarray(h.getSolution().row_dual).reshape(T,rows)[:,:m['nz']]
    return dict(status=status,start_hour=start,end_hour_exclusive=end,fraction=fraction,objective_eur=float(h.getObjectiveValue()),maximum_primal_residual_mw=residual,water_residual_mwh=water_error,maximum_per_unit_energy_change_mwh=float(abs(power.sum(axis=0)-ref.sum(axis=0)).max()),closing_stock_residual_mwh=float(abs(inventory[-1]-terminal).max()),solver_seconds=h.getRunTime()),dict(values=matrix[:,:nb],power=power,inventory=inventory,prices=prices)


def native_window(n,m,hp,mask,water,start,end,case,fraction,objective):
    p=n.copy(snapshots=n.snapshots[start:end]);ids=n.storage_units.query("carrier=='hydro'").index[mask];su=n.storage_units.loc[ids]
    for c in ['StorageUnit','Store']:p.remove(c,p.df(c).index)
    for z in m['zones']:p.add('Bus','zone:'+z,carrier='AC',v_nom=380)
    p.generators.bus=p.generators.bus.map(m['buszone']).map(lambda z:'zone:'+z)
    p.generators_t.marginal_cost=pd.DataFrame(m['native_cost'][start:end],index=p.snapshots,columns=n.generators.index)
    p.remove('Load',p.loads.index);ref=hp[start:end][:,mask];demand=m['load'][start:end].copy()
    for j,b in enumerate(su.bus):demand[:,m['zones'].index(m['buszone'][b])]+=ref[:,j]
    for i,z in enumerate(m['zones']):p.add('Load','load:'+z,bus='zone:'+z,p_set=pd.Series(demand[:,i],index=p.snapshots))
    if case=='hydro_and_demand_buses':
        doff=offsets(n,m,hp,mask,case)-offsets(n,m,hp,mask,'hydro_buses')
        for b in n.buses.index:
            if abs(doff[b].iloc[start:end]).max()>1e-10:p.add('Load','fixed-demand-relocation:'+b,bus=b,p_set=pd.Series(-doff[b].iloc[start:end].values,index=p.snapshots))
    initial=water['initial'] if start==0 else water['inventory'][start-1]
    for j,name in enumerate(ids):
        bus='zone:'+m['buszone'][su.loc[name].bus] if case=='country' else su.loc[name].bus
        p.add('StorageUnit',name,bus=bus,carrier='hydro',p_nom=su.loc[name].p_nom,p_min_pu=0.,p_max_pu=pd.Series(np.minimum(ref[:,j]*(1+fraction)/su.loc[name].p_nom,1.),index=p.snapshots),efficiency_dispatch=water['eta'][j],efficiency_store=0.,max_hours=water['capacity'][j]/su.loc[name].p_nom,state_of_charge_initial=initial[j],cyclic_state_of_charge=False,inflow=pd.Series(water['inflow'][start:end,j],index=p.snapshots),marginal_cost=0.)
    distribution={}
    for z,ws in m['weights'].items():
        distribution[z]=[]
        for b,w in ws.items():
            name='redistribute:'+z+':'+b;distribution[z].append((name,w));p.add('Link',name,bus0='zone:'+z,bus1=b,p_nom=1e6,p_min_pu=-1,efficiency=1)
    def extra(net,snapshots):
        v=net.model['Link-p']
        for z,links in distribution.items():
            total=v.sel(name=[name for name,_ in links]).sum('name')
            for name,w in links:net.model.add_constraints(v.sel(name=name)==w*total,name='gsk:'+name)
        dispatch=net.model['StorageUnit-p_dispatch'];state=net.model['StorageUnit-state_of_charge']
        rhs=pd.DataFrame(ref*(1-fraction),index=p.snapshots,columns=ids).rename_axis(index='snapshot',columns='name').to_xarray().to_array('name').transpose('snapshot','name')
        net.model.add_constraints(dispatch>=rhs,name='bounded-hydro-lower')
        for j,name in enumerate(ids):net.model.add_constraints(state.sel(snapshot=p.snapshots[-1],name=name)==float(water['inventory'][end-1,j]),name='terminal:'+name)
        if 'StorageUnit-spill' in net.model.variables:
            assert np.all(water['spill'][start:end]==0.)
            net.model.add_constraints(net.model['StorageUnit-spill']==0.,name='unchanged-zero-spill')
    status,condition=p.optimize(solver_name='highs',solver_options={'threads':1,'output_flag':False,'time_limit':90},extra_functionality=extra)
    if (status,condition)!=('ok','optimal'):raise ValueError('Native chronological window failed')
    diff=float(p.objective-objective)
    if abs(diff)>max(.05,abs(objective)*1e-8):raise ValueError('Native chronological objective mismatch')
    return dict(hours=end-start,status=condition,native_objective_eur=float(p.objective),objective_difference_eur=diff)
