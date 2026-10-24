"""Full-European independent-hour adjoints and physical export pilot."""
import json
from pathlib import Path
import numpy as np
import run_independent_hourly_transport_2025 as study
from independent_hourly_transport_2025 import initialize,physical_clear
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json


def run():
    study.OUT.mkdir(exist_ok=True);base,(state,market,_,_)=study.setup()
    hours=np.array([15,111,318,567,759,815,900]);s,d,_,_,_=state
    theta,active=initialize(s,d,hours);rng=np.random.default_rng(251)
    theta+=.03*rng.normal(size=theta.shape)*active[:,:,None]
    result=market.solve(theta,hours,tolerance=1e-11)
    gq=rng.normal(size=result['quantities_gw'].shape);gp=rng.normal(size=result['prices'].shape)
    gp[:,~np.isfinite(d['observed_prices']).all(axis=0)]=0
    gradient,identification=market.backward(theta,result,gq,gp)
    assert identification['unidentified_rhs_max']<1e-8
    def loss(pars):
        r=market.solve(pars,hours,p0=result['prices'],tolerance=1e-11)
        return float((r['quantities_gw']*gq).sum()+(r['prices']*gp).sum())
    checks=[]
    for seed in [13,23,47]:
        direction=np.random.default_rng(seed).normal(size=theta.shape)*active[:,:,None]
        exact=float((gradient*direction).sum());sweep=[]
        for eps in [1e-5,3e-6]:
            finite=(loss(theta+eps*direction)-loss(theta-eps*direction))/(2*eps)
            error=abs(finite-exact)/max(1,abs(exact),abs(finite));assert error<.001
            sweep.append(dict(epsilon=eps,exact=exact,finite=finite,scaled_error=error))
        checks.append(dict(seed=seed,sweep=sweep))
    witness,physical=physical_clear(state,market,theta,hours,bins=100)
    base.save(study.OUT/'pilot-physical.npz',**witness)
    paths=[Path(__file__),study.PLAN,ROOT/'tools/independent_hourly_transport_2025.py',
           ROOT/'tools/run_independent_hourly_transport_2025.py',ROOT/'tools/test_independent_hourly_transport_2025.py']
    record=dict(status='passed',hours=hours.tolist(),zones=48,gradient_identification=identification,
                gradients=checks,fast_certificate=result['certificate'],physical=physical,
                physical_witness_sha256=digest(study.OUT/'pilot-physical.npz'),
                sources={str(p.relative_to(ROOT)):digest(p) for p in paths})
    atomic_json(study.OUT/'pilot.json',record);print(json.dumps(record))


if __name__=='__main__':run()
