"""Compiled/old KKT gradient equivalence and shared-parameter directional checks."""
import json,time
from pathlib import Path
import numpy as np
import clarabel
import run_forward_hourly_splines_2025 as study
import hourly_spline_reconstruction_2025 as base
import condensed_spline_kkt_2025 as condensed
from clarabel_spline_dispatch_2025 import solve
from monthly_diurnal_splines_2025 import initialize,labels,expand
from spline_europe_2025 import problem,backward
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json

OUT=ROOT/'data/bidding-zone-network-2025/monthly-diurnal-splines-v1'


def run():
    OUT.mkdir(exist_ok=True)
    s,d,A,_,_=study.initialize();condensed.install()
    shared,active=initialize(s,d,np.arange(744))
    rng=np.random.default_rng(828)
    shared+=.05*rng.normal(size=shared.shape)*active[:,:,None]
    rows=[]
    for hour in [15,111,567,759,815,900]:
        clock=labels(s['groups'],np.array([hour]))
        pars=expand(shared,clock)[0]
        p=problem(s,d,A,np.zeros((len(pars),11)),hour)
        ids=p['active'][p['active']<len(pars)]
        def cost(theta):
            c=study.cached_cost(s,d,base.expand(theta),hour,ids,len(p['active'])-len(ids))
            c.features[:]=0;c.features[:,0]=1;c.__post_init__();return c
        p['cost']=cost(pars)
        gx=rng.normal(size=A.shape[1])/100
        # The fitted loss observes generation and market prices, not latent
        # internal network-flow allocations. Retain the failed arbitrary-flow
        # pilot separately; do not assert general flow-sensitivity accuracy.
        gx[len(s['groups']):]=0
        gp=rng.normal(size=s['nz'])/40
        gp[~np.isfinite(d['observed_prices']).all(axis=0)]=0
        output={}
        for name,solver in [('condensed',study.safe_warm),('compiled',solve)]:
            began=time.perf_counter();r=solver(p['cost'],p,None);seconds=time.perf_counter()-began
            r['problem']=p;g=backward(r,gx,gp)
            output[name]=dict(r=r,g=g,seconds=seconds)
        old,new=output['condensed'],output['compiled']
        price_delta=float(abs(old['r']['nu']-new['r']['nu']).max())
        gradient_delta=float(np.linalg.norm(old['g']-new['g'])/max(1.,np.linalg.norm(old['g'])))
        if price_delta>.001 or gradient_delta>.001:raise ValueError(f'Backend pilot failed at {hour}: {price_delta,gradient_delta}')
        row=dict(hour=hour,original_seconds=old['seconds'],compiled_seconds=new['seconds'],max_price_difference=price_delta,
            scaled_gradient_discrepancy=gradient_delta,compiled_certificate=new['r']['certificate'])
        if hour in [15,567,815]:
            shared_direction=rng.normal(size=shared.shape)*active[:,:,None]
            direction=expand(shared_direction,clock)[0]
            wanted=float((new['g'][:,base.FIELDS]*direction).sum())
            sweep=[]
            for eps in [1e-4,3e-5,1e-5]:
                values=[]
                for sign in [-1,1]:
                    c=cost(pars+sign*eps*direction)
                    rr=solve(c,p,new['r']);full=np.zeros(A.shape[1])
                    full[p['active']],full[p['fixed']]=rr['x'],p['fixed_values']
                    nu=np.zeros(len(p['full_b']));nu[p['equality_rows']]=rr['nu']
                    values.append(float(full@gx-nu[:s['nz']]@gp))
                finite=(values[1]-values[0])/(2*eps)
                error=abs(finite-wanted)/max(1,abs(finite),abs(wanted))
                sweep.append(dict(epsilon=eps,adjoint=wanted,finite=finite,scaled_discrepancy=error))
            row['finite_difference_sweep']=sweep
            # Require agreement at both smaller steps, not one cherry-picked
            # perturbation across a dispatch active-set transition.
            if any(v['scaled_discrepancy']>.001 for v in sweep[1:]):
                atomic_json(OUT/'failed-gradient-pilot.json',row)
                raise ValueError(f'Shared finite difference failed at {hour}: {sweep}')
        rows.append(row);print(json.dumps(row),flush=True)
    paths=[Path(__file__),ROOT/'tools/clarabel_spline_dispatch_2025.py',ROOT/'tools/monthly_diurnal_splines_2025.py']
    atomic_json(OUT/'pilot.json',dict(status='passed',clarabel_version=clarabel.__version__,hours=rows,sources={str(p.relative_to(ROOT)):digest(p) for p in paths}))


if __name__=='__main__':run()
