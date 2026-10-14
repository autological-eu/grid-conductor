"""Trace this LP's prices, without inventing a unique marginal generator."""
import numpy as np

INTERIOR_MW=.001
PRICE_TOL=1e-5

def offer_members(n,m,cost):
    groups={}
    for j,(_,row) in enumerate(n.generators.iterrows()):
        key=(m['buszone'][row.bus],cost[:,j].tobytes(),row.carrier=='emergency')
        groups.setdefault(key,[]).append(j)
    assert len(groups)==m['ng'];out=[]
    for k,(key,ids) in enumerate(groups.items()):
        assert key[0]==m['offer_zones'][k]
        np.testing.assert_array_equal(m['cost'][:,k],cost[:,ids[0]])
        out.append(dict(zone=key[0],carriers=sorted(set(n.generators.iloc[ids].carrier)),generators=n.generators.index[ids].tolist()))
    return out

def category(carriers):
    c=set(carriers)
    if c<= {'CCGT','OCGT'}:return 'gas'
    if c<= {'coal','lignite'}:return 'coal_lignite'
    if len(c)==1:return next(iter(c))
    return 'mixed:'+','.join(sorted(c))

def marginal_labels(members,m,values,prices):
    labels=np.full(prices.shape,'no_local_interior_offer',dtype=object)
    interior=(values[:,:m['ng']]>INTERIOR_MW)&(m['availability']-values[:,:m['ng']]>INTERIOR_MW)
    for j,z in enumerate(m['zones']):
        ids=[k for k,r in enumerate(members) if r['zone']==z]
        for t in range(len(values)):
            choices=[category(members[k]['carriers']) for k in ids if interior[t,k] and abs(m['cost'][t,k]-prices[t,j])<=PRICE_TOL]
            unique=sorted(set(choices))
            if unique:labels[t,j]=unique[0] if len(unique)==1 else 'tied:'+ '|'.join(unique)
    return labels.astype(str)

def decompose(m,row_duals):
    nz=m['nz'];ni=len(m['islands']);q=m['ng']+m['nl']
    energy=np.asarray((m['A'][nz:nz+ni,q:].T@row_duals[:,nz:nz+ni].T).T)
    passive=np.asarray((m['A'][nz+ni:,q:].T@row_duals[:,nz+ni:].T).T)
    return energy,passive

def dual_replay(m,values,row_duals,col_duals,objectives,offsets):
    ng,nl,nz=m['ng'],m['nl'],m['nz'];ni=len(m['islands']);T=len(values)
    costs=np.c_[m['cost'],np.zeros((T,nl+nz))]
    lower=np.c_[np.zeros((T,ng)),m['link_min']];upper=np.c_[m['availability'],m['link_max']]
    lo=np.c_[m['load'],m['island_rhs'],-m['ratings']-offsets]
    hi=np.c_[m['load'],m['island_rhs'],m['ratings']-offsets]
    stationarity=float(abs(costs-(m['A'].T@row_duals.T).T-col_duals).max())
    ax=(m['A']@values.T).T;finite=ng+nl
    complementarity=max(float(abs(np.maximum(row_duals,0)*(ax-lo)).max()),
        float(abs(np.minimum(row_duals,0)*(ax-hi)).max()),
        float(abs(np.maximum(col_duals[:,:finite],0)*(values[:,:finite]-lower)).max()),
        float(abs(np.minimum(col_duals[:,:finite],0)*(values[:,:finite]-upper)).max()))
    dual_obj=(np.maximum(row_duals,0)*lo+np.minimum(row_duals,0)*hi).sum(axis=1)
    dual_obj+=(np.maximum(col_duals[:,:finite],0)*lower+np.minimum(col_duals[:,:finite],0)*upper).sum(axis=1)
    gap=float(abs(dual_obj-objectives).max());free=float(abs(col_duals[:,finite:]).max())
    energy,passive=decompose(m,row_duals);price=float(abs(energy+passive-row_duals[:,:nz]).max())
    assert stationarity<1e-5 and free<1e-5 and price<1e-5,(stationarity,free,price)
    assert gap<.05 and complementarity<.05,(gap,complementarity)
    return dict(stationarity_maximum_eur_mwh=stationarity,free_injection_reduced_cost_maximum=free,
        complementarity_maximum_eur=complementarity,duality_gap_maximum_eur=gap,
        price_decomposition_maximum_eur_mwh=price)
