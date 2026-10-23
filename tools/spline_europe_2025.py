"""European physical-input adapter for smooth spline clearing and adjoints."""
import numpy as np
from scipy.linalg import qr
from scipy.sparse import csc_matrix, vstack, eye
from sigmoid_month_pairs_2025 import load as source_load
from differentiable_spline_clearing import BidCost, solve, adjoint, initial_parameters

ZERO_TECH = {'onshore_wind','offshore_wind','solar','ror'}


def load():
    sealed,data,oldA=source_load();groups=sealed['groups'];G=len(groups);K=sealed['design']['segments']
    columns=np.r_[np.arange(G)*K,np.arange(sealed['ng'],oldA.shape[1])]
    A=oldA[:,columns].tocsc()
    return sealed,data,A


def problem(sealed,data,A,theta,hour,x0=None,regularizer=.01):
    groups=sealed['groups'];G=len(groups);nz=sealed['nz'];ne=nz+data['island_rhs'].shape[1]
    lower=np.r_[np.zeros(G),data['link_min'][hour]/1000,np.full(nz,-np.inf)]
    upper=np.r_[data['capacity'][hour]/1000,data['link_max'][hour]/1000,np.full(nz,np.inf)]
    fixed=np.isfinite(lower)&np.isfinite(upper)&(abs(upper-lower)<1e-14)
    active=np.flatnonzero(~fixed);fixed_ids=np.flatnonzero(fixed);fixed_values=lower[fixed]
    a=A[:,active];offset=np.asarray(A[:,fixed_ids]@fixed_values).ravel()
    equality=a[:ne].tocsc();b=np.r_[data['load'][hour],data['island_rhs'][hour]]/1000-offset[:ne]
    # Keep balance-price rows first when removing algebraically redundant islands.
    scaled=equality.T.toarray();scaled[:,:nz]*=1e6
    _,R,piv=qr(scaled,mode='economic',pivoting=True)
    rank=int((abs(np.diag(R))>1e-9).sum());rows=np.sort(piv[:rank])
    if not set(range(nz)).issubset(rows):raise ValueError('A zonal price equality is unidentified')
    E=equality[rows];bb=b[rows]
    branch=a[ne:].tocsc();hup=(data['ratings']-data['flow'][hour])/1000-offset[ne:]
    hlo=(data['ratings']+data['flow'][hour])/1000+offset[ne:]
    ub=np.flatnonzero(np.isfinite(upper[active]));lb=np.flatnonzero(np.isfinite(lower[active]))
    ident=eye(len(active),format='csc')
    GG=vstack([branch,-branch,ident[ub],-ident[lb]],format='csc')
    hh=np.r_[hup,hlo,upper[active][ub],-lower[active][lb]]
    responsive=np.asarray(abs(GG).sum(axis=1)).ravel()>0
    if (hh[~responsive]<-1e-9).any():raise ValueError('Infeasible fixed physical row')
    GG=GG[responsive];hh=hh[responsive]
    ids=active[active<G];ng=len(ids)
    zero=np.array([groups[j]['technology'] in ZERO_TECH for j in ids])
    source=data['source_cost'][hour,ids].copy();source[zero]=0
    cost=BidCost(data['capacity'][hour,ids]/1000,source,np.array([groups[j]['parameter'] for j in ids]),
                 data['features'][hour,[groups[j]['zone_id'] for j in ids]],zero,theta,len(active)-ng,
                 generation_regularizer=regularizer)
    init=None if x0 is None else x0[active]
    return dict(cost=cost,E=E,b=bb,G=GG,h=hh,active=active,fixed=fixed_ids,fixed_values=fixed_values,
                equality=equality,full_b=b,equality_rows=rows,hour=int(hour),x0=init)


def clear_hour(sealed,data,A,theta,hour,x0=None,regularizer=.01):
    p=problem(sealed,data,A,theta,hour,x0,regularizer)
    r=solve(p['cost'],p['E'],p['b'],p['G'],p['h'],x0=p['x0'])
    full=np.zeros(A.shape[1]);full[p['active']]=r['x'];full[p['fixed']]=p['fixed_values']
    error=float(abs(p['equality']@r['x']-p['full_b']).max(initial=0))*1000
    if error>1e-4:raise ValueError('Dropped equality was not redundant')
    nu=np.zeros(len(p['full_b']));nu[p['equality_rows']]=r['nu']
    r.update(full_x=full,prices=-nu[:sealed['nz']],problem=p)
    return r


def backward(result,full_dispatch_gradient,price_gradient):
    p=result['problem'];gp=np.zeros(len(p['full_b']));gp[:len(price_gradient)]=price_gradient
    return adjoint(p['cost'],p['E'],p['G'],result,full_dispatch_gradient[p['active']],gp[p['equality_rows']])


def quantities(sealed,data,values,hours):
    out=data['fixed_generation'][hours].copy()
    for j,g in enumerate(sealed['groups']):
        out[:,g['country_id'],sealed['technologies'].index(g['technology'])]+=values[:,j]*1000
    return out
