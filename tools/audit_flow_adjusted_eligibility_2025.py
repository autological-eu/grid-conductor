"""Partition excluded hours and bound missing A09 exchanges without imputation."""
import json
import numpy as np

from flow_adjusted_zonal_clearing_2025 import DEST,observed_exchanges
from run_batched_transport_2025 import setup


def net_import_intervals(net,edge_flow,edges,lower,upper):
    """Missing signed corridor flow spans model bounds; observed flow stays exact."""
    low=net.copy();high=net.copy();unknown=~np.isfinite(edge_flow)
    for k,(i,j) in enumerate(edges):
        mask=unknown[:,k]
        low[mask,i]-=upper[mask,k];high[mask,i]-=lower[mask,k]
        low[mask,j]+=lower[mask,k];high[mask,j]+=upper[mask,k]
    return low,high


def main():
    state,market,_,_=setup();s,d,*_=state
    net,covered,_,edge_flow=observed_exchanges(s['zones'],market.edges,return_edges=True)
    with np.load(DEST/'witness.npz') as old:
        if not np.array_equal(covered,old['covered']) or not np.allclose(net,old['net_import_gw'],atol=0,rtol=0):
            raise ValueError('Source exchange replay changed')
    cap=market.capacity@market.Z;demand=market.load
    target=demand-net
    missing=~covered;negative=covered&(target<0);excess=covered&(target>cap)
    feasible=covered&~negative&~excess
    lo,hi=net_import_intervals(net,edge_flow,market.edges,market.lower,market.upper)
    # Some modeled physical ceilings need not bound commercial schedules.
    known=np.isfinite(edge_flow)
    conflicts=known&((edge_flow<market.lower-1e-8)|(edge_flow>market.upper+1e-8))
    overshoot=np.where(known,np.maximum(np.maximum(market.lower-edge_flow,edge_flow-market.upper),0),0)
    corridor_conflicts=sorted((dict(corridor=s['zones'][i]+'–'+s['zones'][j],
                                   observed_hours=int(known[:,k].sum()),
                                   outside_model_bounds=int(conflicts[:,k].sum()),
                                   max_excess_gw=float(overshoot[:,k].max()))
                              for k,(i,j) in enumerate(market.edges)),
                              key=lambda x:x['outside_model_bounds'],reverse=True)
    target_low=demand-hi;target_high=demand-lo
    possible=missing&(target_high>=0)&(target_low<=cap)
    impossible=missing&~possible
    per_zone=[]
    for j,z in enumerate(s['zones']):
        per_zone.append(dict(zone=z,missing_flow_hours=int(missing[:,j].sum()),
            missing_with_possible_supply_balance=int(possible[:,j].sum()),
            missing_without_possible_supply_balance=int(impossible[:,j].sum()),
            covered_negative_target=int(negative[:,j].sum()),
            covered_above_supply_capacity=int(excess[:,j].sum()),
            eligible=int(feasible[:,j].sum())))
    result=dict(status='replayed',total_zone_hours=int(target.size),
        missing_flow_zone_hours=int(missing.sum()),
        missing_with_possible_supply_balance=int(possible.sum()),
        missing_without_possible_supply_balance=int(impossible.sum()),
        covered_negative_target=int(negative.sum()),
        covered_above_supply_capacity=int(excess.sum()),
        eligible=int(feasible.sum()),
        observed_corridor_quarter_hour_aggregate_cells=int(known.sum()),
        observed_corridor_cells_outside_model_physical_bounds=int(conflicts.sum()),
        maximum_observed_bound_excess_gw=float(overshoot.max()),
        top_conflict_corridors=corridor_conflicts[:12],
        median_missing_import_interval_width_gw=float(np.median((hi-lo)[missing])),
        per_zone=per_zone,
        caveat='Intervals use model physical corridor ceilings as diagnostic bounds, not verified A09 market limits. Possible balance is not a cleared price or network feasibility certificate.')
    if sum(result[k] for k in ('missing_flow_zone_hours','covered_negative_target','covered_above_supply_capacity','eligible'))!=target.size:
        raise ValueError('Eligibility partition does not close')
    (DEST/'eligibility-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('per_zone','top_conflict_corridors')},indent=2))
    print('TOP_CONFLICTS',json.dumps(corridor_conflicts[:12]))


if __name__=='__main__':main()
