"""Bounded LP transfer check before 8,760-hour replay."""
import json
from scipy.sparse import hstack
import numpy as np

from monthly_lp_spline_inputs_2025 import aligned
from fit_monthly_lp_splines_2025 import OUT as FIT
from clear_monthly_lp_splines_2025 import BINS,sampled_costs
from conditional_monotone_market_2025 import ConditionalMarket
from hour_table_conditioner_2025 import feature_rows
from nve_hydro_diagnostics import solver
from run_regional_water_candidate_2025 import guarded_hour
from solar_country_fit_2025 import write
from generation_mix_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/monthly-lp-splines-pilot-v2'


def run():
    OUT.mkdir(exist_ok=False)
    base,state,market,network,design=aligned()
    schema,data,A,emergency,sourcecap=state
    market.__class__=ConditionalMarket
    market.reference=np.maximum(market.capacity.max(axis=0),.001)
    checkpoint=FIT/'month-01/state-000.npz'
    with np.load(checkpoint) as z:weights=z['weights'];centers=z['centers']
    hours=np.arange(24)
    X,_=feature_rows(schema['groups'],data,hours,market.reference,centers)
    theta=np.einsum('tgf,gfk->tgk',X,weights)
    ng=market.ng;ne=emergency.shape[1]
    bids=sampled_costs(theta,data['source_cost'][hours],data['capacity'][hours]/1000,
                       market.reference,market.zero)
    cost=np.c_[bids.reshape(24,ng*BINS),data['emergency_cost'][hours]]
    available=np.c_[np.repeat(data['capacity'][hours]/BINS,BINS,axis=1),
                    data['emergency_available'][hours]]
    physical=hstack([A[:,np.repeat(np.arange(ng),BINS)],emergency,A[:,ng:]],format='csc')
    problem=dict(A=physical,cost=cost,availability=available,ng=ng*BINS+ne,
        nl=schema['nl'],nz=schema['nz'],load=data['load'][hours],
        island_rhs=data['island_rhs'][hours],link_min=data['link_min'][hours],
        link_max=data['link_max'][hours],ratings=data['ratings'],
        islands=[None]*data['island_rhs'].shape[1])
    high=solver(problem)
    primal=0.;emergency_mwh=0.
    for t,h in enumerate(hours):
        result,values=guarded_hour(high,problem,t,data['flow'][h])
        if values is None:raise ValueError('LP transfer failed at hour '+str(h))
        emergency_mwh+=float(np.maximum(values[ng*BINS:ng*BINS+ne],0).sum())
        lhs=physical@values
        lo=np.r_[problem['load'][t],problem['island_rhs'][t],
                 -problem['ratings']-data['flow'][h]]
        hi=np.r_[problem['load'][t],problem['island_rhs'][t],
                 problem['ratings']-data['flow'][h]]
        primal=max(primal,float(np.maximum(lo-lhs,0).max()),
                   float(np.maximum(lhs-hi,0).max()))
    if emergency_mwh>1e-6 or primal>1e-4:raise ValueError('LP transfer gates failed')
    write(OUT/'summary.json',dict(status='first_24_hours_lp_transfer_passed',
        hours=24,physical_rows=physical.shape[0],generators=problem['ng'],
        emergency_mwh=emergency_mwh,max_primal_mw=primal,
        source_sha256={str(checkpoint.relative_to(ROOT)):digest(checkpoint)},
        limitations=['Neutral initial January coefficients; no monthly fit or annual score established.']))
    print('LP TRANSFER PILOT PASSED',primal,emergency_mwh,flush=True)


if __name__=='__main__':run()
