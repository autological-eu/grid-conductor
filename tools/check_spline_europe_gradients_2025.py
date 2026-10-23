"""Additional European directional-adjoint and numerical-smoothing checks."""
import json
import resource
import numpy as np
from sigmoid_month_pairs_2025 import ROOT,write,digest
from differentiable_spline_clearing import initial_parameters
from spline_europe_2025 import load,clear_hour,backward
from run_differentiable_spline_2025 import source_guesses


def run():
    folder=ROOT/'data/bidding-zone-network-2025/differentiable-spline-gradient-v1';folder.mkdir(exist_ok=False)
    sealed,data,A=load();theta=initial_parameters(len(sealed['parameters']));initial=source_guesses(sealed,1)
    rng=np.random.default_rng(5021);hour=348;r=clear_hour(sealed,data,A,theta,hour,initial[hour])
    gx=rng.normal(size=A.shape[1])*.01;gp=rng.normal(size=sealed['nz'])*.01
    gradient=backward(r,gx,gp);rows=[]
    for kind in ['midpoints','shapes','joint']:
        d=rng.normal(size=theta.shape)
        if kind=='midpoints':d[:,5:]=0
        if kind=='shapes':d[:,:5]=0
        d/=np.linalg.norm(d);eps=1e-4
        def objective(v):
            rr=clear_hour(sealed,data,A,v,hour,initial[hour]);return float(gx@rr['full_x']+gp@rr['prices'])
        finite=(objective(theta+eps*d)-objective(theta-eps*d))/(2*eps);implicit=float((gradient*d).sum())
        error=abs(finite-implicit);passed=error<=max(5e-4,.01*abs(finite))
        rows.append(dict(direction=kind,implicit=implicit,finite_difference=finite,absolute_error=error,passed=passed))
        write(folder/'progress.json',rows)
        if not passed:raise ValueError('Directional European gradient failed')
    smoothing=[]
    for hour in [12,348,504]:
        first=clear_hour(sealed,data,A,theta,hour,initial[hour]);second=clear_hour(sealed,data,A,theta,hour,initial[hour],regularizer=.001)
        smoothing.append(dict(hour=hour,max_price_difference_eur_mwh=float(abs(first['prices']-second['prices']).max()),
                              max_source_group_dispatch_difference_mw=float(abs(first['full_x'][:len(sealed['groups'])]-second['full_x'][:len(sealed['groups'])]).max()*1000)))
    write(folder/'summary.json',dict(status='three_directional_checks_passed',gradient_checks=rows,regularizer_sensitivity=smoothing,
          dependencies={name:digest(ROOT/'tools'/name) for name in ['differentiable_spline_clearing.py','spline_europe_2025.py','check_spline_europe_gradients_2025.py']}))


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,)*2);run()
