"""One clearing balance per market zone, with separate physical island balances."""
import numpy as np
import pandas as pd
import highspy
from scipy.sparse import coo_matrix,block_diag,eye
from european_physical_bids_2025 import compile_model
from european_reservoir_clearing_2025 import aggregate_offers

def compile_global(n,cost,fixed,level):
    country=n.buses.country.copy()
    labels=n.buses.bidding_zone.replace({'ES-IB-MA':'ES'}) if level=='bidding_zone' else country.replace({'LU':'DE'})
    n.buses.country=labels;m=compile_model(n);n.buses.country=country
    before=m['zones'];names=list(dict.fromkeys(z.split(':',1)[1] for z in before));oldnz=m['nz'];nz=len(names);ng,nl=m['ng'],m['nl']
    capacity=n.generators.loc[n.generators.carrier!='emergency'].groupby('bus').p_nom.sum().reindex(n.buses.index,fill_value=0.)
    weights={}
    for z in names:
        buses=n.buses.index[labels==z];v=capacity.loc[buses].copy()
        if v.sum()==0:v[:]=1.
        weights[z]=(v/v.sum()).loc[lambda x:x>0].to_dict()
    R=coo_matrix((np.ones(oldnz),(np.array([names.index(z.split(':',1)[1]) for z in before]),np.arange(oldnz))),shape=(nz,oldnz)).tocsc()
    rr=[];cc=[];vv=[]
    for i,area in enumerate(before):
        z=area.split(':',1)[1];bs=[b for b,a in m['buszone'].items() if a==area]
        rr.append(i);cc.append(names.index(z));vv.append(sum(weights[z].get(b,0.) for b in bs))
    Q=coo_matrix((vv,(rr,cc)),shape=(oldnz,nz)).tocsc()
    # Exact projection of native PTDF/island rows. No synthetic free transfer
    # between islands, and no removal of constraints inside a common market zone.
    m['A']=block_diag((R,eye(m['A'].shape[0]-oldnz)),format='csc')@m['A']@block_diag((eye(ng+nl),Q),format='csc')
    m['load']=(R@m['load'].T).T.copy();m['zones']=names;m['nz']=nz;m['weights']=weights;m['buszone']=labels.to_dict()
    m['islands']=[list(dict.fromkeys(z.split(':',1)[1] for z in keys)) for keys in m['islands']]
    zonal_fixed=fixed.T.groupby(labels).sum().T.reindex(columns=names,fill_value=0.)
    m['load']-=zonal_fixed.values
    demand=n.get_switchable_as_dense('Load','p_set').T.groupby(n.loads.bus).sum().T.reindex(columns=n.buses.index,fill_value=0.)
    actual=fixed-demand;off=actual.copy()
    for z,ws in weights.items():
        total=actual.loc[:,labels.index[labels==z]].sum(axis=1)
        for b,w in ws.items():off[b]-=w*total
    m['island_rhs']=np.column_stack([-off[row.obj.buses_i()].sum(axis=1).values for _,row in n.sub_networks.iterrows()])
    assert np.isfinite(off.values).all() and np.isfinite(m['island_rhs']).all()
    m['cost']=cost.copy();return aggregate_offers(n,m),off

def clear_hour(h,m,t,flow_offset):
    cols=np.arange(m['ng']+m['nl'],dtype=np.int32)
    lo=np.r_[np.zeros(m['ng']),m['link_min'][t]];hi=np.r_[m['availability'][t],m['link_max'][t]]
    h.changeColsBounds(len(cols),cols,lo,hi);h.changeColsCost(m['ng'],np.arange(m['ng'],dtype=np.int32),m['cost'][t])
    rowlo=np.r_[m['load'][t],m['island_rhs'][t],-m['ratings']-flow_offset];rowhi=np.r_[m['load'][t],m['island_rhs'][t],m['ratings']-flow_offset]
    rows=np.arange(len(rowlo),dtype=np.int32);h.changeRowsBounds(len(rows),rows,rowlo,rowhi);h.setOptionValue('time_limit',h.getRunTime()+10.);h.run()
    if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:h.clearSolver();h.setOptionValue('time_limit',h.getRunTime()+10.);h.run()
    status=h.modelStatusToString(h.getModelStatus())
    if status!='Optimal':return dict(status=status),None
    x=np.array(h.getSolution().col_value);ax=m['A']@x
    error=max(float(np.maximum(lo-x[:len(cols)],0).max(initial=0)),float(np.maximum(x[:len(cols)]-hi,0).max(initial=0)),float(np.maximum(rowlo-ax,0).max(initial=0)),float(np.maximum(ax-rowhi,0).max(initial=0)))
    if error>1e-4:raise ValueError('Zonal primal replay failed')
    return dict(status=status,objective_eur=float(h.getObjectiveValue()),maximum_residual_mw=error),x
