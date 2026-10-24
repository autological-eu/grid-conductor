"""Price-blind supply/demand analogues; one coherent European donor per hour."""
import numpy as np
from independent_hourly_transport_2025 import economic_nodes,raw_from_nodes
from spline_europe_2025 import ZERO_TECH


def features(source,data):
    groups=source['groups'];zone=np.array([g['zone_id'] for g in groups]);nz=len(source['zones'])
    load=data['load'][:1416]/1000;capacity=data['capacity'][:1416]/1000
    cost=data['source_cost'][:1416];jan=slice(0,744)
    peak=np.maximum(abs(load[jan]).max(axis=0),.05)
    load_scale=np.maximum.reduce([load[jan].std(axis=0),.1*peak,np.full(nz,.05)])
    cap_scale=np.maximum.reduce([capacity[jan].std(axis=0),.1*capacity[jan].mean(axis=0),
                                 .01*peak[zone],np.full(len(groups),.001)])
    counts=np.bincount(zone,minlength=nz)
    weights_cap=1/np.sqrt(3*nz*counts[zone])
    supported=capacity[jan]>0
    thermal=np.array([g['technology'] not in ZERO_TECH for g in groups])&supported.any(axis=0)
    ids=np.flatnonzero(thermal);mean=np.zeros(len(ids));std=mean.copy()
    for k,g in enumerate(ids):
        values=cost[jan,g][supported[:,g]];mean[k]=values.mean();std[k]=values.std()
    cost_scale=np.maximum(std,10.)
    cost_values=np.where(capacity[:,ids]>0,cost[:,ids],mean[None])
    cost_zone=zone[ids];cost_counts=np.bincount(cost_zone,minlength=nz)
    ncost_zones=int((cost_counts>0).sum())
    if ncost_zones==0:raise ValueError('No supported source-cost features')
    cost_weights=1/np.sqrt(3*ncost_zones*cost_counts[cost_zone])
    matrix=np.c_[load/load_scale/np.sqrt(3*nz),capacity/cap_scale*weights_cap,
                 (cost_values-mean)/cost_scale*cost_weights]
    if not np.isfinite(matrix).all():raise ValueError('Nonfinite physical matching features')
    return matrix,dict(load_scale_gw=load_scale.tolist(),availability_scale_gw=cap_scale.tolist(),
        source_cost_groups=ids.tolist(),source_cost_mean=mean.tolist(),source_cost_scale=cost_scale.tolist(),
        feature_columns=matrix.shape[1],cost_zones=ncost_zones,
        feature_zone_ids=np.r_[np.arange(nz),zone,cost_zone].tolist())


def squared_distances(a,b):
    # Direct differences avoid cancellation for near-identical physical profiles.
    return np.stack([((a-row)**2).sum(axis=1) for row in b],axis=1)


def match(matrix,method):
    if matrix.shape[0]!=1416:raise ValueError('Every744 January and672 February hour is required')
    jan=matrix[:744];feb=matrix[744:]
    if method in ['nearest_day','three_days']:
        donor=jan.reshape(31,24,-1).reshape(31,-1)/np.sqrt(24)
        target=feb.reshape(28,24,-1).reshape(28,-1)/np.sqrt(24)
        distance=squared_distances(target,donor)
        k=1 if method=='nearest_day' else 3
        selected=np.argsort(distance,axis=1,kind='stable')[:,:k]
        nearest=distance[np.arange(28),selected[:,0]]
        chosen=distance[np.arange(28)[:,None],selected]
        weights=np.ones_like(chosen) if k==1 else 1/np.maximum(chosen,1e-12)
        weights/=weights.sum(axis=1,keepdims=True)
        hours=(selected[:,None,:]*24+np.arange(24)[None,:,None]).reshape(672,k)
        weights=np.repeat(weights,24,axis=0)
        train=squared_distances(donor,donor);np.fill_diagonal(train,np.inf)
        reference=train.min(axis=1)
    elif method=='nearest_hour':
        hours=np.empty((672,1),dtype=int);nearest=np.zeros(672);reference=[]
        for clock in range(24):
            indices=np.arange(clock,744,24);targets=np.arange(clock,672,24)
            distance=squared_distances(feb[targets],jan[indices])
            selected=np.argmin(distance,axis=1)
            hours[targets,0]=indices[selected];nearest[targets]=distance[np.arange(28),selected]
            train=squared_distances(jan[indices],jan[indices]);np.fill_diagonal(train,np.inf)
            reference.extend(train.min(axis=1).tolist())
        weights=np.ones((672,1));reference=np.asarray(reference)
    else:raise ValueError('Unregistered analogue method')
    threshold=float(np.quantile(np.sqrt(reference),.95))
    return hours,weights,dict(method=method,nearest_distance=np.sqrt(nearest).tolist(),
        january_nearest_other_p95=threshold,target_fraction_above_january_p95=float((np.sqrt(nearest)>threshold).mean()),
        unique_donor_days=int(len(np.unique(hours//24))))


def transfer(theta,capacity,donor_hours,weights,neutral):
    if theta.shape[:2]!=capacity[:744].shape:raise ValueError('Source hour/group mismatch')
    ng=theta.shape[1]
    if donor_hours.ndim==2:
        donor_hours=np.broadcast_to(donor_hours[:,None,:],(672,ng,donor_hours.shape[-1]))
        weights=np.broadcast_to(weights[:,None,:],donor_hours.shape)
    group=np.arange(ng)[None,:,None]
    selected=economic_nodes(theta)[donor_hours,group]
    supported=capacity[donor_hours,group]>0
    actual_weights=weights*supported
    total=actual_weights.sum(axis=2)
    fallback=economic_nodes(neutral)
    mean=np.divide((selected*actual_weights[:,:,:,None]).sum(axis=2),total[:,:,None],
                   out=np.broadcast_to(fallback,(672,*fallback.shape)).copy(),where=total[:,:,None]>0)
    return raw_from_nodes(mean),dict(neutral_fallback_hour_groups=int((total==0).sum()))


def match_neighbor_days(matrix,feature_zones,edges,group_zones,nz):
    """Own-zone half / neighbors half; one day per zone, same clock thereafter."""
    fz=np.asarray(feature_zones);gz=np.asarray(group_zones)
    donors=np.empty((672,len(gz),1),dtype=int)
    distances=[];thresholds=[];novel=[]
    for zone in range(nz):
        neighbors=sorted({int(j if i==zone else i) for i,j in edges if zone in [i,j]})
        weight=np.zeros(len(fz));weight[fz==zone]=nz*(.5 if neighbors else 1.)
        if neighbors:weight[np.isin(fz,neighbors)]=.5*nz/len(neighbors)
        ids=np.flatnonzero(weight)
        daily=(matrix[:,ids]*np.sqrt(weight[ids])).reshape(59,24,-1).reshape(59,-1)/np.sqrt(24)
        difference=squared_distances(daily[31:],daily[:31]);selected=np.argmin(difference,axis=1)
        hours=(selected[:,None]*24+np.arange(24)[None]).reshape(672)
        donors[:,gz==zone,0]=hours[:,None]
        best=np.sqrt(difference[np.arange(28),selected])
        training=squared_distances(daily[:31],daily[:31]);np.fill_diagonal(training,np.inf)
        threshold=float(np.quantile(np.sqrt(training.min(axis=1)),.95))
        distances.append(best);thresholds.append(threshold);novel.append(best>threshold)
    return donors,np.ones_like(donors,dtype=float),dict(method='neighbor_zone_day',
        nearest_distance=np.array(distances).T.tolist(),january_nearest_other_p95=thresholds,
        target_fraction_above_january_p95=float(np.asarray(novel).mean()),
        unique_donor_days=int(len(np.unique(donors//24))))
