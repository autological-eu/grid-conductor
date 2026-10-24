"""Same-hour cold/warm timing, objectives, prices and implicit gradients."""
import json
from pathlib import Path
import time
import numpy as np
import differentiable_spline_clearing as smooth
import hourly_spline_reconstruction_2025 as base
import hourly_spline_numerical_recovery_2025 as recovery
import condensed_spline_kkt_2025 as fast
from run_forward_hourly_splines_2025 import initialize, cached_cost, safe_warm, ROOT
from supply_knot_splines_2025 import initial_parameters
from spline_europe_2025 import problem, backward
from sigmoid_month_pairs_2025 import digest
from run_differentiable_spline_2025 import atomic_json

OUT=ROOT/'data/bidding-zone-network-2025/spline-performance-jan-feb-v1'


def run():
    OUT.mkdir(exist_ok=True)
    s,d,A,_,_=initialize()
    theta=initial_parameters(len(s['groups']))
    rng=np.random.default_rng(817)
    rows=[]
    for hour in [15,111,567,759,1000,1300]:
        p=problem(s,d,A,np.zeros((len(theta),11)),hour)
        ids=p['active'][p['active']<len(theta)]
        c=cached_cost(s,d,theta,hour,ids,len(p['active'])-len(ids))
        c.features[:]=0;c.features[:,0]=1;c.__post_init__()
        p['cost']=c
        gx=rng.normal(size=A.shape[1])/100
        gp=rng.normal(size=s['nz'])/40
        outputs={}
        before=fast.STATS.copy()
        for name,factor in [('original',fast.original_factor),('condensed',fast.factor_kkt)]:
            for module in [smooth,base,recovery]:module.factor_kkt=factor
            began=time.perf_counter();r=safe_warm(c,p,None);seconds=time.perf_counter()-began
            r['problem']=p
            began=time.perf_counter();grad=backward(r,gx,gp);adjoint_seconds=time.perf_counter()-began
            began=time.perf_counter();warm=safe_warm(c,p,r);warm_seconds=time.perf_counter()-began
            outputs[name]=dict(r=r,gradient=grad,cold_seconds=seconds,warm_seconds=warm_seconds,adjoint_seconds=adjoint_seconds)
        old,new=outputs['original'],outputs['condensed']
        difference=float(abs(old['r']['nu']-new['r']['nu']).max())
        gradient_error=float(np.linalg.norm(old['gradient']-new['gradient'])/max(1,np.linalg.norm(old['gradient'])))
        if difference>.001 or gradient_error>.001:raise ValueError(f'Backend mismatch at {hour}: {difference,gradient_error}')
        row=dict(hour=hour,timings={k:{m:v[m] for m in ['cold_seconds','warm_seconds','adjoint_seconds']} for k,v in outputs.items()},
            max_price_difference_eur_mwh=difference,max_dispatch_difference_mw=float(abs(old['r']['x']-new['r']['x']).max()*1000),
            gradient_scaled_discrepancy=gradient_error,certificate=new['r']['certificate'],linear_stats={k:fast.STATS[k]-before[k] for k in fast.STATS})
        if hour in [15,567,1000]:
            direction=rng.normal(size=theta.shape)
            direction[:,1:5]=0
            direction[[g['technology'] in base.ZERO_TECH for g in s['groups']]]=0
            wanted=float((new['gradient']*direction).sum())
            values=[]
            for sign in [-1,1]:
                cc=cached_cost(s,d,theta+sign*1e-4*direction,hour,ids,len(p['active'])-len(ids))
                cc.features[:]=0;cc.features[:,0]=1;cc.__post_init__()
                rr=safe_warm(cc,p,new['r'])
                full=np.zeros(A.shape[1]);full[p['active']],full[p['fixed']]=rr['x'],p['fixed_values']
                nu=np.zeros(len(p['full_b']));nu[p['equality_rows']]=rr['nu']
                values.append(float(full@gx-nu[:s['nz']]@gp))
            finite=(values[1]-values[0])/2e-4
            err=abs(finite-wanted)/max(1,abs(finite),abs(wanted))
            if err>.001:raise ValueError(f'Finite-difference check failed at {hour}: {err}')
            row['finite_difference']=dict(adjoint=wanted,finite=finite,scaled_discrepancy=err)
        rows.append(row)
        print(json.dumps(row),flush=True)
    paths=[Path(__file__),ROOT/'tools/condensed_spline_kkt_2025.py']
    record=dict(status='passed',sources={str(p.relative_to(ROOT)):digest(p) for p in paths},hours=rows)
    atomic_json(OUT/'gradient-pilot.json',record)


if __name__=='__main__':run()
