"""Annual physical LP replay of month-local-hour learned monotone supply bids."""
import fcntl
import json
import os
import resource
from pathlib import Path

import numpy as np
from scipy.sparse import hstack

from monthly_lp_spline_inputs_2025 import aligned
from fit_monthly_lp_splines_2025 import OUT as FIT
from conditional_monotone_market_2025 import ConditionalMarket,basis
from hour_table_conditioner_2025 import feature_rows
from forward_hourly_splines_2025 import month_hours
from joint_network_clear_2025 import clear_or_reject
from generation_mix_2025 import ROOT,digest
from solar_country_fit_2025 import write

OUT=ROOT/'data/bidding-zone-network-2025/monthly-lp-splines-lp-v1'
BINS=8


def sampled_costs(theta,source_cost,available_gw,reference_gw,zero):
    """Eight interval-average marginal bids; inputs are [hour, offer]."""
    ng=theta.shape[1]
    slopes=.05+20*np.logaddexp(0,theta[...,1:])
    base=source_cost+theta[...,0]
    umax=np.divide(available_gw,reference_gw[None,:],
        out=np.zeros_like(base),where=reference_gw[None,:]>0)
    result=np.empty((*base.shape,BINS))
    for segment in range(BINS):
        u0=umax*segment/BINS;u1=umax*(segment+1)/BINS;mid=(u0+u1)/2
        bids=[base+(slopes*basis(u)).sum(axis=-1) for u in (u0,mid,u1)]
        result[:,:,segment]=(bids[0]+4*bids[1]+bids[2])/6
    result[:,zero,:]=0
    return result


def offer_costs(schema,data,market):
    ng=market.ng
    allcost=np.zeros((8760,ng*BINS+len(data['emergency_cost'][0])))
    for month in range(1,13):
        folder=FIT/f'month-{month:02d}'
        receipt=json.loads((folder/'complete.json').read_text())
        if receipt['points']!=101:raise ValueError('Incomplete monthly fit')
        with np.load(folder/'state-100.npz') as z:
            if digest(folder/'state-100.npz')!=receipt['final_state_sha256']:
                raise ValueError('Changed monthly coefficients')
            weights=z['weights'];centers=z['centers']
        hours=month_hours(month)
        for start in range(0,len(hours),168):
            h=hours[start:start+168]
            X,_=feature_rows(schema['groups'],data,h,market.reference,centers)
            theta=np.einsum('tgf,gfk->tgk',X,weights)
            sampled=sampled_costs(theta,data['source_cost'][h],data['capacity'][h]/1000,
                                  market.reference,market.zero)
            allcost[np.ix_(h,np.arange(ng*BINS))]=sampled.reshape(len(h),ng*BINS)
    allcost[:,ng*BINS:]=data['emergency_cost']
    if not np.isfinite(allcost).all():raise ValueError('Nonfinite sampled bids')
    return allcost


def run():
    OUT.mkdir(exist_ok=True)
    lock=(OUT/'job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (OUT/'annual.npz').exists() or (OUT/'failure.json').exists():
        raise ValueError('Inspect prior annual solve before any restart')
    fit=json.loads((FIT/'complete.json').read_text())
    if fit['status']!='twelve_monthly_fits_completed':raise ValueError('Monthly fits incomplete')
    base,state,market,network,design=aligned()
    schema,data,A,emergency,sourcecap=state
    market.__class__=ConditionalMarket
    market.reference=np.maximum(market.capacity.max(axis=0),.001)
    ng=market.ng;ne=emergency.shape[1]
    physical=hstack([A[:,np.repeat(np.arange(ng),BINS)],emergency,A[:,ng:]],format='csc')
    cost=offer_costs(schema,data,market)
    availability=np.c_[np.repeat(data['capacity']/BINS,BINS,axis=1),
                       data['emergency_available']]
    sources=json.loads((FIT/'sources.json').read_text())
    for relative,sha in sources.items():assert digest(ROOT/relative)==sha,relative
    for month in range(1,13):
        path=FIT/f'month-{month:02d}/state-100.npz'
        sources[str(path.relative_to(ROOT))]=digest(path)
    sources[str(Path(__file__).relative_to(ROOT))]=digest(__file__)
    write(OUT/'inputs.json',dict(status='sampled_conditional_spline_bids_on_accepted_physical_lp',
        bins=BINS,source_sha256=sources,market_rows=physical.shape[0],
        generators=ng,emergency_generators=ne,load_hours=8760,
        caveat='Eight linear segments approximate the learned nonlinear bid; no forward-month validation.'))
    model=dict(A=physical,cost=cost,availability=availability,ng=ng*BINS+ne,
        nl=schema['nl'],nz=schema['nz'],load=data['load'],island_rhs=data['island_rhs'],
        link_min=data['link_min'],link_max=data['link_max'],ratings=data['ratings'],
        islands=[None]*data['island_rhs'].shape[1])
    x,y,obj,info=clear_or_reject(model,data['flow'],cost,OUT/'annual.npz')
    if x is None:
        write(OUT/'failure.json',dict(status='annual_lp_failed_original_gates',market=info,
                                      inputs_sha256=digest(OUT/'inputs.json')))
        return
    emergency_mwh=float(np.maximum(x[:,ng*BINS:ng*BINS+ne],0).sum())
    if emergency_mwh>1e-6:
        write(OUT/'failure.json',dict(status='no_emergency_gate_failed',market=info,
            emergency_mwh=emergency_mwh,witness_sha256=digest(OUT/'annual.npz'),
            inputs_sha256=digest(OUT/'inputs.json')))
        return
    with np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz') as z:observed=z['prices']
    known=np.isfinite(observed).all(axis=0)
    if known.sum()!=41:raise ValueError('Changed hourly price coverage')
    price_mae=float(abs(y[:,:schema['nz']][:,known]-observed[:,known]).mean())
    write(OUT/'summary.json',dict(status='annual_monthly_spline_lp_completed_pending_independent_audit',
        model='month-local-hour monotone spline bids, eight-segment physical LP',
        market=info,price_mae=price_mae,emergency_mwh=emergency_mwh,
        witness_sha256=digest(OUT/'annual.npz'),inputs_sha256=digest(OUT/'inputs.json'),
        limitations=['Same-year monthly fit is an in-sample reconstruction.',
            'Eight LP segments approximate the continuous trained spline.',
            'Original fixed hydro and renewable source availability remain.']))
    print('YEAR',price_mae,info['clearing_seconds'],flush=True)


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
    run()
