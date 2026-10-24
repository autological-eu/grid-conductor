"""Real48-zone gradient/clock aggregation pilot; no temporal/spatial sampling in fit."""
import json,time
from pathlib import Path
import numpy as np
from run_batched_transport_2025 import setup,OUT
from monthly_diurnal_splines_2025 import initialize,labels,expand,aggregate
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json


def run():
    OUT.mkdir(exist_ok=True)
    state,m,network,design=setup();s,d,_,_,_=state
    shared,active=initialize(s,d,np.arange(744))
    rng=np.random.default_rng(5401)
    shared+=.03*rng.normal(size=shared.shape)*active[:,:,None]
    hours=np.array([15,111,567,759,815,900]);clock=labels(s['groups'],hours)
    theta=expand(shared,clock);r=m.solve(theta,hours,tolerance=1e-11)
    gp=rng.normal(size=r['prices'].shape)/40
    gp[:,~np.isfinite(d['observed_prices']).all(axis=0)]=0
    gq=rng.normal(size=r['quantities_gw'].shape)/100
    gradient,info=m.backward(theta,r,gq,gp)
    if info['unidentified_rhs_max']>1e-8:raise ValueError('Observed pilot price sensitivity is unidentified')
    shared_gradient=aggregate(gradient,clock)
    rows=[]
    for seed in [12,19,37]:
        direction=np.random.default_rng(seed).normal(size=shared.shape)*active[:,:,None]
        wanted=float((direction*shared_gradient).sum());sweep=[]
        for eps in [1e-5,3e-6]:
            values=[]
            for sign in [-1,1]:
                rr=m.solve(expand(shared+sign*eps*direction,clock),hours,p0=r['prices'],tolerance=1e-11)
                values.append(float((rr['prices']*gp).sum()+(rr['quantities_gw']*gq).sum()))
            finite=(values[1]-values[0])/(2*eps)
            error=abs(finite-wanted)/max(1,abs(finite),abs(wanted));sweep.append(dict(epsilon=eps,adjoint=wanted,finite=finite,scaled_discrepancy=error))
        if any(v['scaled_discrepancy']>.001 for v in sweep):
            atomic_json(OUT/'failed-pilot.json',dict(seed=seed,sweep=sweep));raise ValueError('Gradient pilot failed')
        rows.append(dict(seed=seed,sweep=sweep))
    sources=[Path(__file__),ROOT/'tools/batched_transport_dispatch_2025.py',ROOT/'tools/compile_transport_corridors_2025.py',ROOT/'config/batched-transport-dispatch-2025.json']
    record=dict(status='passed',hours=hours.tolist(),zones=m.nz,corridors=len(m.edges),certificate=r['certificate'],
        seconds=r['seconds'],gradient_identification=info,gradients=rows,sources={str(p.relative_to(ROOT)):digest(p) for p in sources})
    atomic_json(OUT/'pilot.json',record);print(json.dumps(record,indent=2))


if __name__=='__main__':run()
