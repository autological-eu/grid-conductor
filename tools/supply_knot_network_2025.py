"""One normalized technology bid per bidding zone, original LP constraints."""
import numpy as np
from scipy.sparse import hstack
from sigmoid_month_pairs_2025 import load as source_load,certify
from spline_europe_2025 import problem as old_problem,backward,ZERO_TECH
from differentiable_spline_clearing import solve,initial_parameters as old_neutral
from supply_knot_splines_2025 import KnotCost


def load():
    source,data,oldA=source_load();original=source['groups'];keys=sorted({(g['zone'],g['technology']) for g in original})
    mapping=np.array([keys.index((g['zone'],g['technology'])) for g in original]);groups=[];first=[]
    capacity=np.zeros((8760,len(keys)));weighted=capacity.copy()
    K=source['design']['segments']
    for j,key in enumerate(keys):
        ids=np.flatnonzero(mapping==j);g=original[ids[0]].copy();g['parameter']=j;groups.append(g);first.append(int(ids[0])*K)
        for k in ids:
            if (oldA[:,int(k)*K]-oldA[:,first[-1]]).nnz:raise ValueError('Cannot aggregate distinct physical locations')
            capacity[:,j]+=data['capacity'][:,k];weighted[:,j]+=data['capacity'][:,k]*data['source_cost'][:,k]
    source_cost=np.divide(weighted,capacity,out=np.zeros_like(weighted),where=capacity>0)
    adapted=data.copy();adapted.update(capacity=capacity,source_cost=source_cost)
    sealed=source.copy();sealed.update(groups=groups,parameters=[list(k) for k in keys],original_groups=original,mapping=mapping.tolist())
    A=hstack([oldA[:,first],oldA[:,source['ng']:]],format='csc')
    emergency=oldA[:,len(original)*K:source['ng']]
    np.testing.assert_allclose(capacity.sum(axis=1),data['capacity'].sum(axis=1),atol=1e-7,rtol=0)
    return sealed,adapted,A,emergency,data['capacity']


def cost_for(sealed,data,theta,hour,ids,extra=0,regularizer=.01):
    groups=sealed['groups'];zero=np.array([groups[j]['technology'] in ZERO_TECH for j in ids]);source=data['source_cost'][hour,ids].copy();source[zero]=0
    return KnotCost(data['capacity'][hour,ids]/1000,source,np.array(ids),data['features'][hour,[groups[j]['zone_id'] for j in ids]],zero,theta,extra,generation_regularizer=regularizer)


def clear_hour(sealed,data,A,theta,hour,x0):
    p=old_problem(sealed,data,A,old_neutral(len(theta)),hour,x0)
    ids=p['active'][p['active']<len(sealed['groups'])]
    p['cost']=cost_for(sealed,data,theta,hour,ids,len(p['active'])-len(ids))
    r=solve(p['cost'],p['E'],p['b'],p['G'],p['h'],x0=p['x0'])
    full=np.zeros(A.shape[1]);full[p['active']]=r['x'];full[p['fixed']]=p['fixed_values']
    if abs(p['equality']@r['x']-p['full_b']).max(initial=0)*1000>1e-4:raise ValueError('Original equality replay failed')
    nu=np.zeros(len(p['full_b']));nu[p['equality_rows']]=r['nu']
    r.update(full_x=full,prices=-nu[:sealed['nz']],problem=p);return r


def generation(sealed,data,source_capacity,values,hours):
    out=data['fixed_generation'][hours].copy();mapping=sealed['mapping']
    for j,g in enumerate(sealed['original_groups']):
        c=mapping[j];share=np.divide(source_capacity[hours,j],data['capacity'][hours,c],out=np.zeros(len(hours)),where=data['capacity'][hours,c]>0)
        out[:,g['country_id'],sealed['technologies'].index(g['technology'])]+=values[:,c]*share
    return out


def clear_lp(sealed,data,A,emergency,theta,hours,bins):
    import time
    from nve_hydro_diagnostics import solver
    from run_regional_water_candidate_2025 import guarded_hour
    began=time.perf_counter();count=len(sealed['groups']);ng=count*bins+emergency.shape[1]
    matrix=hstack([A[:,np.repeat(np.arange(count),bins)],emergency,A[:,count:]],format='csc')
    costs=[]
    for hour in hours:
        active=np.flatnonzero(data['capacity'][hour]>0);c=np.zeros((count,bins))
        c[active]=cost_for(sealed,data,theta,int(hour),active,regularizer=0).interval_bids(bins)
        costs.append(c.ravel())
    cost=np.c_[np.array(costs),data['emergency_cost'][hours]]
    av=np.c_[np.repeat(data['capacity'][hours]/bins,bins,axis=1),data['emergency_available'][hours]]
    m={k:data[k][hours] for k in ['load','island_rhs','link_min','link_max']}
    m.update(A=matrix,cost=cost,availability=av,ng=ng,nl=sealed['nl'],nz=sealed['nz'],zones=sealed['zones'],ratings=data['ratings'],islands=[None]*data['island_rhs'].shape[1])
    h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
    x=np.zeros((len(hours),matrix.shape[1]));y=np.zeros((len(hours),matrix.shape[0]));objectives=np.zeros(len(hours))
    for t,hour in enumerate(hours):
        r,value=guarded_hour(h,m,t,data['flow'][hour])
        if value is None:
            h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8);r,value=guarded_hour(h,m,t,data['flow'][hour])
        if value is None:raise RuntimeError(f'LP failed at {hour}: {r}')
        x[t]=value;y[t]=h.getSolution().row_dual;objectives[t]=r['objective_eur']
    if np.maximum(x[:,count*bins:ng],0).sum()>1e-6:raise ValueError('Artificial emergency dispatch')
    checks=certify(matrix,cost,av,data,hours,x,y,objectives,ng,sealed['nl'],sealed['nz'])
    q=x[:,:count*bins].reshape(len(hours),count,bins).sum(axis=2)
    return dict(values=x,row_duals=y,objectives=objectives,hours=hours,quantities=q),dict(seconds=time.perf_counter()-began,certificate=checks)
