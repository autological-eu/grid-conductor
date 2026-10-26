"""Match the differentiable offer groups to the accepted annual LP inputs."""
import json
import numpy as np
import solar_anchor_bids_2025 as accepted
import run_independent_hourly_transport_2025 as fast
from generation_mix_2025 import ROOT

SOLAR=ROOT/'data/bidding-zone-network-2025/solar-country-fit-v1/delta.npz'


def aligned():
    base,(state,market,network,design)=fast.setup()
    schema,data,A,emergency,sourcecap=state
    p,original,lp=accepted.model()
    if schema['active_baseline']!='solar-anchor-bids-v1/resource_full':
        raise ValueError('Fast source is not pinned to accepted baseline')
    if schema['zones']!=p['zones'] or A.shape[0]!=lp['A'].shape[0]:
        raise ValueError('Different bidding zones or physical constraint rows')
    grouped=A.tocsc();native=lp['A'].tocsc()
    def signature(matrix,index):
        column=matrix.getcol(index)
        return tuple(column.indices),tuple(np.round(column.data,12))
    source_columns={signature(native,j) for j in range(p['ng'])}
    if any(signature(grouped,j) not in source_columns for j in range(len(schema['groups']))):
        raise ValueError('Grouped physical column absent from accepted LP')
    if (grouped[:,len(schema['groups']):]-native[:,p['ng']:]).nnz:
        raise ValueError('Different link/free network constraint columns')
    for name in ('load','island_rhs','link_min','link_max','flow'):
        left=data[name] if name in data else None
        right=original[name] if name in original else lp[name]
        if left is None or not np.array_equal(left,right):
            raise ValueError('Changed accepted physical input: '+name)
    if not np.array_equal(data['ratings'],original['ratings']):
        raise ValueError('Changed network ratings')
    with np.load(SOLAR) as source:delta=source['delta']
    if delta.shape!=lp['availability'].shape:raise ValueError('Solar delta shape mismatch')
    if np.any(abs(delta[:,original['emergency_mask']])>1e-9):
        raise ValueError('Solar correction touches emergency supply')
    capacity=data['capacity'].copy();component=sourcecap.copy()
    mapping=np.array(schema['mapping'])
    for zone in p['zones']:
        ids=[i for i,g in enumerate(schema['groups'])
             if g['zone']==zone and g['technology']=='solar']
        solar_delta=delta[:,np.asarray(original['offer_zones'])==zone].sum(axis=1)
        if not ids:
            if abs(solar_delta).max()>1e-7:raise ValueError('Unmatched zonal solar correction '+zone)
            continue
        if len(ids)!=1:raise ValueError('Multiple solar groups: explicit split needed')
        group=ids[0];members=np.flatnonzero(mapping==group)
        old=capacity[:,group].copy();new=old+solar_delta
        if new.min() < -1e-5:raise ValueError('Negative corrected solar availability')
        ratio=np.divide(new,old,out=np.ones_like(new),where=old>1e-8)
        if np.any((old<=1e-8)&(abs(solar_delta)>1e-7)):
            raise ValueError('New solar requires missing source allocation')
        component[:,members]*=ratio[:,None]
        capacity[:,group]=new
    np.testing.assert_allclose(capacity.sum(axis=1),
        lp['availability'][:,~original['emergency_mask']].sum(axis=1),atol=1e-5,rtol=0)
    for zone in p['zones']:
        fast_ids=[i for i,g in enumerate(schema['groups']) if g['zone']==zone]
        lp_ids=(np.asarray(original['offer_zones'])==zone)&~original['emergency_mask']
        np.testing.assert_allclose(capacity[:,fast_ids].sum(axis=1),
            lp['availability'][:,lp_ids].sum(axis=1),atol=1e-5,rtol=0)
    np.testing.assert_allclose(np.bincount(mapping,weights=component[100],minlength=len(capacity[100])),
                               capacity[100],atol=1e-5,rtol=0)
    data=data.copy();data['capacity']=capacity;market.capacity=capacity/1000
    return base,(schema,data,A,emergency,component),market,network,design
