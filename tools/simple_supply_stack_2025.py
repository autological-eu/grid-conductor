"""Fresh fixed-hydro supply-stack diagnostic, with explicit island transport.

No storage policy, GSK, AC Kirchhoff rows, commercial NTC or fitted power prices.
Summed cross-zone passive ratings are optimistic model-derived envelopes only.
"""
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
import highspy

def prepare(n,cost,fixed):
    n.determine_network_topology();labels=n.buses.bidding_zone.replace({'ES-IB-MA':'ES'})
    busnode=n.buses.sub_network.astype(str)+':'+labels
    nodes=list(dict.fromkeys(busnode.tolist()));areas=list(dict.fromkeys(labels.tolist()))
    idx={z:j for j,z in enumerate(nodes)};nc=len(nodes);T=len(n.snapshots)
    demand=np.zeros((T,nc));hydro=np.zeros_like(demand)
    loads=n.get_switchable_as_dense('Load','p_set')
    for name,row in n.loads.iterrows():demand[:,idx[busnode[row.bus]]]+=loads[name].values
    for bus in fixed:hydro[:,idx[busnode[bus]]]+=fixed[bus].values
    available=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    groups={}
    for j,(_,row) in enumerate(n.generators.iterrows()):
        key=(busnode[row.bus],cost[:,j].tobytes(),row.carrier=='emergency');groups.setdefault(key,[]).append(j)
    entries=list(groups.items());offer_nodes=np.array([idx[k[0]] for k,ids in entries],int)
    c=np.column_stack([cost[:,ids[0]] for k,ids in entries]);av=np.column_stack([available[:,ids].sum(axis=1) for k,ids in entries])
    members=[dict(node=k[0],carriers=sorted(set(n.generators.iloc[ids].carrier)),generators=n.generators.index[ids].tolist()) for k,ids in entries]
    edges=[];lower=[];upper=[];ng=len(entries)
    for j,(name,row) in enumerate(n.links.iterrows()):
        lo=n.get_switchable_as_dense('Link','p_min_pu').iloc[:,j].values*row.p_nom
        hi=n.get_switchable_as_dense('Link','p_max_pu').iloc[:,j].values*row.p_nom
        eta=float(row.efficiency)
        if not 0<eta<=1:raise ValueError('Unsupported link efficiency')
        if (lo<0).any() and eta!=1:raise ValueError('Lossy signed reverse flow requires a directional formulation')
        edges.append(dict(id=str(name),a=idx[busnode[row.bus0]],b=idx[busnode[row.bus1]],efficiency=eta,source='retained_controllable_link'))
        lower.append(lo);upper.append(hi)
    pairs={}
    for component in ['Line','Transformer']:
        for name,row in n.df(component).iterrows():
            a,b=idx[busnode[row.bus0]],idx[busnode[row.bus1]]
            if a==b:continue
            if n.buses.loc[row.bus0,'sub_network']!=n.buses.loc[row.bus1,'sub_network']:raise ValueError('Passive branch crosses electrical islands')
            rating=float(row.s_nom*row.s_max_pu)
            if not np.isfinite(rating) or rating<=0:raise ValueError('Invalid branch rating')
            pair=tuple(sorted([a,b]));entry=pairs.setdefault(pair,dict(limit_mw=0.,branches=[]))
            entry['limit_mw']+=rating;entry['branches'].append(component+':'+str(name))
    for (a,b),row in sorted(pairs.items()):
        edges.append(dict(id=nodes[a]+'--'+nodes[b],a=a,b=b,efficiency=1.,source='summed_cross_zone_N0_ratings',**row))
        lower.append(np.full(T,-row['limit_mw']));upper.append(np.full(T,row['limit_mw']))
    rr=offer_nodes.tolist();cc=list(range(ng));vv=[1.]*ng
    for j,e in enumerate(edges):rr.extend([e['a'],e['b']]);cc.extend([ng+j,ng+j]);vv.extend([-1.,e['efficiency']])
    A=coo_matrix((vv,(rr,cc)),shape=(nc,ng+len(edges))).tocsc()
    # Never select the target island by observed price agreement.
    primary={}
    for area in areas:
        ids=[idx[node] for node in nodes if node.split(':',1)[1]==area]
        primary[area]=max(ids,key=lambda j:(float(demand[:,j].sum()),-j))
    return dict(nodes=nodes,areas=areas,primary=primary,busnode=busnode.to_dict(),members=members,edges=edges,A=A,
        cost=c,availability=av,demand=demand,fixed=hydro,load=demand-hydro,offer_nodes=offer_nodes,
        emergency=np.array([k[2] for k,ids in entries]),lower=np.column_stack(lower),upper=np.column_stack(upper),ng=ng)

def merit_order(cost,availability,load):
    """Right-hand supply-stack marginal bid; export-required hours stay unresolved."""
    order=np.argsort(cost,axis=1,kind='stable');c=np.take_along_axis(cost,order,axis=1);av=np.take_along_axis(availability,order,axis=1)
    cumulative=np.cumsum(av,axis=1);before=cumulative-av
    quantity=np.minimum(np.maximum(load[:,None]-before,0),av)
    dispatch=np.zeros_like(quantity);np.put_along_axis(dispatch,order,quantity,axis=1)
    valid=(load>=0)&(load<cumulative[:,-1]-1e-7)
    marginal=(cumulative>load[:,None]+1e-7)&(av>0)
    indices=np.argmax(marginal,axis=1);prices=c[np.arange(len(load)),indices].astype(float)
    prices[~valid]=np.nan;dispatch[~valid]=np.nan
    return dispatch,prices,valid

def transport_solver(m):
    h=highspy.Highs()
    for k,v in [('output_flag',False),('threads',1),('solver','simplex'),('primal_feasibility_tolerance',1e-8)]:h.setOptionValue(k,v)
    A=m['A'];ng=m['ng'];lp=highspy.HighsLp();lp.num_col_=A.shape[1];lp.num_row_=A.shape[0]
    lp.col_cost_=np.r_[m['cost'][0],np.zeros(len(m['edges']))];lp.col_lower_=np.r_[np.zeros(ng),m['lower'][0]];lp.col_upper_=np.r_[m['availability'][0],m['upper'][0]]
    lp.row_lower_=m['load'][0];lp.row_upper_=m['load'][0];lp.a_matrix_.format_=highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_=A.indptr;lp.a_matrix_.index_=A.indices;lp.a_matrix_.value_=A.data;h.passModel(lp);return h

def clear(h,m,t):
    ng=m['ng'];cols=np.arange(m['A'].shape[1],dtype=np.int32);rows=np.arange(len(m['nodes']),dtype=np.int32)
    lo=np.r_[np.zeros(ng),m['lower'][t]];hi=np.r_[m['availability'][t],m['upper'][t]]
    h.changeColsBounds(len(cols),cols,lo,hi);h.changeColsCost(ng,cols[:ng],m['cost'][t]);h.changeRowsBounds(len(rows),rows,m['load'][t],m['load'][t])
    h.setOptionValue('time_limit',h.getRunTime()+10.);h.run()
    if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:h.clearSolver();h.setOptionValue('time_limit',h.getRunTime()+10.);h.run()
    status=h.modelStatusToString(h.getModelStatus())
    if status!='Optimal':return dict(status=status),None,None
    sol=h.getSolution();x=np.array(sol.col_value);error=max(float(abs(m['A']@x-m['load'][t]).max()),float(np.maximum(lo-x,0).max()),float(np.maximum(x-hi,0).max()))
    if error>1e-4:return dict(status='Optimal_rejected_balance_or_bound',residual_mw=error),None,None
    return dict(status=status,objective_eur=float(h.getObjectiveValue()),residual_mw=error),x,np.array(sol.row_dual)
