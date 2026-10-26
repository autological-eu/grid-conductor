"""Sample fast learned bids onto the accepted LP's existing offer columns.

No generator column, capacity, dispatch constraint, or fixed hydro schedule is
changed here. Mixed renewable offer pools retain their accepted bid because a
single LP column cannot express different member bids without splitting it.
"""
import json
import numpy as np

from generation_mix_2025 import CARRIER, ROOT, digest
from spline_europe_2025 import ZERO_TECH
from monthly_lp_spline_inputs_2025 import aligned
from hour_table_conditioner_2025 import feature_rows
from forward_hourly_splines_2025 import month_hours

LAYOUT=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json'
OFFERS=ROOT/'data/bidding-zone-network-2025/supply-bid-review-v2/offers.json'
OFFER_AUDIT=OFFERS.with_name('audit.json')
OFFER_SUMMARY=OFFERS.with_name('summary.json')


def offer_groups(schema, accepted, lp):
    layout=json.loads(LAYOUT.read_text())
    audit=json.loads(OFFER_AUDIT.read_text())
    if audit['status']!='passed' or audit['summary_sha256']!=digest(OFFER_SUMMARY):
        raise ValueError('Cached offer inventory is not independently audited')
    rows=json.loads(OFFERS.read_text())
    if len(rows)!=len(layout['members']):raise ValueError('Cached offer inventory differs from source layout')
    if any(row['column']!=j or row['fraction']!=layout['fractions'][j]
           or row['zone']!=str(accepted['offer_zones'][j]) for j,row in enumerate(rows)):
        raise ValueError('Cached offer metadata differs from accepted LP')
    groups={(g['zone'],g['technology']):i for i,g in enumerate(schema['groups'])}
    mapping={};mixed=[]
    for j,row in enumerate(rows):
        kinds={CARRIER[c] for c in row['source_carriers']}
        if kinds=={'emergency'}:
            if not accepted['emergency_mask'][j]:raise ValueError('Emergency mask mismatch')
            continue
        if len(kinds)!=1:
            mixed.append(j)
            continue
        kind=next(iter(kinds));key=(str(accepted['offer_zones'][j]),kind)
        if key not in groups:raise ValueError(f'LP offer {j} has no fast group {key}')
        mapping[j]=groups[key]
    if any(not {CARRIER[c] for c in rows[j]['source_carriers']}.issubset(
            {'onshore_wind','offshore_wind','solar','ror','geothermal'}) for j in mixed):
        raise ValueError('Nonrenewable mixed offer must be split explicitly')
    for j in range(len(layout['members']),lp['ng']):
        key=(str(accepted['offer_zones'][j]),'oil')
        if key not in groups:raise ValueError(f'Unmapped added oil offer {j}')
        mapping[j]=groups[key]
    grouped={g:[] for g in range(len(schema['groups']))}
    for j,g in mapping.items():grouped[g].append(j)
    return grouped,mixed


def sampled_anchors(anchors, output_fraction):
    """Piecewise-linear monotone marginal curve, clipped to [0,1]."""
    u=np.clip(output_fraction,0,1)*5
    left=np.minimum(u.astype(int),4)
    low=np.take_along_axis(anchors,left[...,None],axis=-1)[...,0]
    high=np.take_along_axis(anchors,(left+1)[...,None],axis=-1)[...,0]
    return low+(u-left)*(high-low)


def costs_for_hours(schema,data,market,lp,weights,centers,hours,grouped,reference=None):
    reference=np.maximum(market.capacity.max(axis=0),.001) if reference is None else reference
    X,_=feature_rows(schema['groups'],data,hours,reference,centers)
    theta=np.einsum('tgf,gfk->tgk',X,weights)
    anchors=market.offers(theta,hours)['anchors']
    costs=lp['cost'][hours].copy()
    for g,ids in grouped.items():
        if not ids or schema['groups'][g]['technology'] in ZERO_TECH | {'geothermal'}:
            continue
        # Stable within-hour economic order; fuel costs can change that order.
        original=lp['cost'][np.ix_(hours,ids)]
        order=np.argsort(original,axis=1,kind='stable')
        available=np.take_along_axis(lp['availability'][np.ix_(hours,ids)],order,axis=1)
        np.testing.assert_allclose(available.sum(axis=1),data['capacity'][hours,g],atol=1e-5,rtol=0)
        midpoint=np.cumsum(available,axis=1)-available/2
        fraction=np.divide(midpoint,data['capacity'][hours,g,None],
            out=np.zeros_like(midpoint),where=data['capacity'][hours,g,None]>0)
        curve=np.broadcast_to(anchors[:,g,None,:],(*fraction.shape,6))
        sampled=sampled_anchors(curve,fraction)
        costs[np.arange(len(hours))[:,None],np.asarray(ids)[order]]=sampled
    return costs


def transferred_costs(schema,data,market,accepted,lp,fit_root):
    grouped,mixed=offer_groups(schema,accepted,lp)
    # Keep the accepted 799-column LP; the fast market is only a bid fitter.
    costs=lp['cost'].copy()
    reference=np.maximum(market.capacity.max(axis=0),.001)
    for month in range(1,13):
        folder=fit_root/f'month-{month:02d}'
        receipt=json.loads((folder/'complete.json').read_text())
        if receipt['points']!=101:raise ValueError('Incomplete monthly fit')
        checkpoint=folder/'state-100.npz'
        if digest(checkpoint)!=receipt['final_state_sha256']:
            raise ValueError('Changed fitted monthly checkpoint')
        with np.load(checkpoint) as state:
            weights=state['weights'];centers=state['centers']
        hours=month_hours(month)
        for start in range(0,len(hours),168):
            h=hours[start:start+168]
            costs[h]=costs_for_hours(schema,data,market,lp,weights,centers,h,grouped,reference)
    if not np.isfinite(costs).all():raise ValueError('Nonfinite LP bids')
    return costs,dict(mapped_offers=sum(map(len,grouped.values())),mixed_renewable_offers=mixed,
                      retained_accepted_bid_technologies=sorted(ZERO_TECH | {'geothermal'}),
                      accepted_offer_columns=lp['ng'])
