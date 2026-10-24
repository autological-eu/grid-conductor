"""Exact LP projection: one offer for each zero-priced renewable curve.

Twenty identical zero-price tranches have exactly the same projected feasible
MW interval and cost as one tranche. Expand witnesses back into the original
20-tranche model and certify there. Renewable allocations can remain nonunique.
"""
import time
import numpy as np
from scipy.sparse import csc_matrix,hstack
from spline_europe_2025 import ZERO_TECH
from sigmoid_month_pairs_2025 import certify


def projection(count,zero,bins,extra):
    widths=np.where(zero,1,bins)
    starts=np.r_[0,np.cumsum(widths)]
    rows=[];cols=[];values=[]
    for g in range(count):
        for k in range(bins):
            rows.append(g*bins+k)
            cols.append(starts[g]+(0 if zero[g] else k))
            values.append(1/bins if zero[g] else 1.)
    for j in range(extra):
        rows.append(count*bins+j);cols.append(starts[-1]+j);values.append(1.)
    return csc_matrix((values,(rows,cols)),shape=(count*bins+extra,starts[-1]+extra)),widths


def clear_lp(sealed,data,A,emergency,hours,bids,bins=20):
    from nve_hydro_diagnostics import solver
    from run_regional_water_candidate_2025 import guarded_hour
    began=time.perf_counter()
    count=len(sealed['groups'])
    zero=np.array([g['technology'] in ZERO_TECH for g in sealed['groups']])
    if (abs(bids[:,zero])>1e-12).any():raise ValueError('Only identical zero economic bids may be collapsed')
    original=hstack([A[:,np.repeat(np.arange(count),bins)],emergency,A[:,count:]],format='csc')
    P,widths=projection(count,zero,bins,emergency.shape[1]+A.shape[1]-count)
    compact=(original@P).tocsc()
    groups=np.repeat(np.arange(count),widths)
    indices=np.concatenate([np.array([g*bins]) if zero[g] else g*bins+np.arange(bins) for g in range(count)])
    anchors=data['source_cost'][hours].copy();anchors[:,zero]=0
    economic=(anchors[:,:,None]+bids).reshape(len(hours),-1)
    cost=np.c_[economic[:,indices],data['emergency_cost'][hours]]
    av=np.c_[data['capacity'][hours][:,groups]/widths[groups],data['emergency_available'][hours]]
    ng=len(indices)+emergency.shape[1]
    model={k:data[k][hours] for k in ['load','island_rhs','link_min','link_max']}
    model.update(A=compact,cost=cost,availability=av,ng=ng,nl=sealed['nl'],nz=sealed['nz'],zones=sealed['zones'],ratings=data['ratings'],islands=[None]*data['island_rhs'].shape[1])
    prepared=time.perf_counter()-began
    h=solver(model);h.setOptionValue('primal_feasibility_tolerance',1e-8)
    x=np.zeros((len(hours),compact.shape[1]));y=np.zeros((len(hours),compact.shape[0]));obj=np.zeros(len(hours))
    began=time.perf_counter()
    for t,hour in enumerate(hours):
        record,value=guarded_hour(h,model,t,data['flow'][hour])
        if value is None:
            h=solver(model);h.setOptionValue('primal_feasibility_tolerance',1e-8)
            record,value=guarded_hour(h,model,t,data['flow'][hour])
        if value is None:raise RuntimeError(f'Compact LP failed at {hour}: {record}')
        x[t],y[t],obj[t]=value,h.getSolution().row_dual,record['objective_eur']
    loop_seconds=time.perf_counter()-began
    expanded=(P@x.T).T
    fullcost=np.c_[economic,data['emergency_cost'][hours]]
    fullav=np.c_[np.repeat(data['capacity'][hours]/bins,bins,axis=1),data['emergency_available'][hours]]
    original_ng=count*bins+emergency.shape[1]
    began=time.perf_counter()
    checks=certify(original,fullcost,fullav,data,hours,expanded,y,obj,original_ng,sealed['nl'],sealed['nz'])
    if np.maximum(expanded[:,count*bins:original_ng],0).sum()>1e-6:raise ValueError('Artificial emergency dispatch')
    witness=dict(values=expanded,row_duals=y,objectives=obj,hours=hours,quantities=expanded[:,:count*bins].reshape(len(hours),count,bins).sum(axis=2))
    return witness,dict(certificate=checks,preparation_seconds=prepared,loop_seconds=loop_seconds,certificate_seconds=time.perf_counter()-began,original_columns=original.shape[1],compact_columns=compact.shape[1],collapsed_curves=int(zero.sum()))
