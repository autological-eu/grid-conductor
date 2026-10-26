"""Twenty-four-hour existing-column LP bridge check, no annual solve."""
import json
import numpy as np

from monthly_lp_spline_inputs_2025 import aligned
from monthly_fast_lp_costs_2025 import offer_groups,costs_for_hours
from nve_hydro_diagnostics import solver
from run_regional_water_candidate_2025 import guarded_hour
from solar_anchor_bids_2025 import model
from solar_country_fit_2025 import write
from generation_mix_2025 import ROOT,digest

OUT=ROOT/'data/bidding-zone-network-2025/monthly-fast-lp-pilot-v3'


def run():
    OUT.mkdir(exist_ok=False)
    _,(schema,data,*_),market,_,_=aligned()
    _,accepted,lp=model()
    grouped,mixed=offer_groups(schema,accepted,lp)
    checkpoint=ROOT/'data/bidding-zone-network-2025/monthly-fast-splines-pilot-v3/month-01/state-000.npz'
    with np.load(checkpoint) as state:weights=state['weights'];centers=state['centers']
    hours=np.arange(24)
    cost=costs_for_hours(schema,data,market,lp,weights,centers,hours,grouped)
    local=lp|dict(cost=cost,availability=lp['availability'][hours],load=lp['load'][hours],
        island_rhs=lp['island_rhs'][hours],link_min=lp['link_min'][hours],
        link_max=lp['link_max'][hours])
    engine=solver(local);emergency=0.;primal=0.
    for t,h in enumerate(hours):
        result,x=guarded_hour(engine,local,t,accepted['flow'][h])
        if x is None:raise ValueError(f'LP pilot failed at {h}: {result}')
        emergency+=float(np.maximum(x[:lp['ng']][accepted['emergency_mask']],0).sum())
        lhs=lp['A']@x
        lo=np.r_[local['load'][t],local['island_rhs'][t],-lp['ratings']-accepted['flow'][h]]
        hi=np.r_[local['load'][t],local['island_rhs'][t],lp['ratings']-accepted['flow'][h]]
        primal=max(primal,float(np.maximum(lo-lhs,0).max()),float(np.maximum(lhs-hi,0).max()))
    if emergency>1e-6 or primal>=1e-4:raise ValueError('Original LP gates failed')
    write(OUT/'summary.json',dict(status='24_hour_original_offer_lp_passed',hours=24,
        generator_columns=lp['ng'],mixed_offer_columns=len(mixed),
        emergency_mwh=emergency,max_primal_mw=primal,
        neutral_fit_checkpoint_sha256=digest(checkpoint),
        caveat='Neutral-bid setup pilot; no completed monthly fit or annual claim'))


if __name__=='__main__':run()
