"""Bounded European equivalence/gradient pilot before all-month fitting."""
import json
import time
import numpy as np
import hourly_spline_reconstruction_2025 as base
from run_forward_hourly_splines_2025 import OUT, PLAN, initialize, neutral_state, provenance, cached_cost, safe_warm
from forward_hourly_splines_2025 import month_hours, polynomials, interval_bids, clear_lp
from spline_europe_2025 import problem, backward
from run_differentiable_spline_2025 import atomic_json


def run():
    OUT.mkdir(exist_ok=True)
    sealed,data,A,emergency,_ = initialize()
    hours=np.array([month_hours(m)[15] for m in range(1,13)])
    shared,active,_=neutral_state(sealed,data,hours)
    rng=np.random.default_rng(31)
    theta=shared+rng.normal(size=shared.shape)*.1*active[:,:,None]
    zero=[g['technology'] in base.ZERO_TECH for g in sealed['groups']]
    began=time.perf_counter()
    w,cert=clear_lp(sealed,data,A,emergency,hours,interval_bids(polynomials(theta,zero)))
    compiled_seconds=time.perf_counter()-began
    began=time.perf_counter()
    old,oldcert=base.lp_clear(sealed,data,A,emergency,theta,hours,20)
    old_seconds=time.perf_counter()-began
    delta=float(abs(w['row_duals'][:,:sealed['nz']]-old['row_duals'][:,:sealed['nz']]).max())
    objective_delta=float(abs(w['objectives']-old['objectives']).max())
    if delta>1e-5 or objective_delta>.05: raise ValueError('Original LP equivalence failed')
    rows=[]
    for t in [0,6,11]:
        hour=int(hours[t])
        p=problem(sealed,data,A,np.zeros((len(theta[t]),11)),hour)
        ids=p['active'][p['active']<len(theta[t])]
        def cost_for(theta):
            c=cached_cost(sealed,data,base.expand(theta),hour,ids,len(p['active'])-len(ids))
            c.features[:]=0
            c.features[:,0]=1
            c.__post_init__()
            return c
        p['cost']=cost_for(theta[t])
        began=time.perf_counter()
        r=safe_warm(p['cost'],p,None)
        seconds=time.perf_counter()-began
        r['problem']=p
        gx=rng.normal(size=A.shape[1])/100
        gp=rng.normal(size=sealed['nz'])/40
        grad=backward(r,gx,gp)[:,base.FIELDS]
        direction=rng.normal(size=grad.shape)*active[t,:,None]
        wanted=float((grad*direction).sum())
        vals=[]
        eps=1e-4
        for sign in [-1,1]:
            cc=cost_for(theta[t]+sign*eps*direction)
            rr=safe_warm(cc,p,r)
            full=np.zeros(A.shape[1])
            full[p['active']],full[p['fixed']]=rr['x'],p['fixed_values']
            nu=np.zeros(len(p['full_b']))
            nu[p['equality_rows']]=rr['nu']
            vals.append(float(full@gx-nu[:sealed['nz']]@gp))
        finite=(vals[1]-vals[0])/(2*eps)
        discrepancy=abs(finite-wanted)/max(1.,abs(finite),abs(wanted))
        if discrepancy>.001: raise ValueError(f'Gradient failed at {hour}: {discrepancy}')
        rows.append(dict(hour=hour,seconds=seconds,certificate=r['certificate'],adjoint=wanted,finite_difference=finite,scaled_discrepancy=discrepancy))
    result=dict(status='passed',provenance=provenance(),hours=hours.tolist(),lp_certificate=cert,original_lp_certificate=oldcert,
        max_price_difference_eur_mwh=delta,max_objective_difference_eur=objective_delta,
        lp_seconds=compiled_seconds,original_lp_seconds=old_seconds,smooth_gradient_pilots=rows)
    atomic_json(OUT/'pilot.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__': run()
