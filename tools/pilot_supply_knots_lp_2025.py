"""Training-month European feasibility, gradient and LP-resolution pilot."""
import json
import resource
import time
import numpy as np
from sigmoid_month_pairs_2025 import ROOT,digest,write
from spline_europe_2025 import backward
from supply_knot_network_2025 import load,clear_hour,clear_lp
from run_supply_knots_lp_2025 import warm_parameters,guesses


def run():
    folder=ROOT/'data/bidding-zone-network-2025/supply-knots-lp-pilot-v1';folder.mkdir(exist_ok=False)
    sealed,data,A,emergency,source_capacity=load();theta=warm_parameters(sealed,source_capacity,1,2);initial=guesses(sealed,1);hour=348
    result=clear_hour(sealed,data,A,theta,hour,initial[hour]);rng=np.random.default_rng(143)
    gx=rng.normal(size=A.shape[1])*.01;gp=rng.normal(size=sealed['nz'])*.01
    gradient=backward(result,gx,gp);direction=rng.normal(size=theta.shape);direction[:,:5]=0;direction/=np.linalg.norm(direction);eps=1e-4
    def objective(v):
        r=clear_hour(sealed,data,A,v,hour,initial[hour]);return float(gx@r['full_x']+gp@r['prices'])
    finite=(objective(theta+eps*direction)-objective(theta-eps*direction))/(2*eps);implicit=float((gradient*direction).sum());error=abs(finite-implicit)
    if error>max(5e-4,.01*abs(finite)):raise ValueError(f'European knot gradient failed: {implicit,finite}')
    rows=[];previous=None
    hours=np.arange(336,360)
    for bins in [5,20,40]:
        w,info=clear_lp(sealed,data,A,emergency,theta,hours,bins);prices=w['row_duals'][:,:sealed['nz']]
        row=dict(bins=bins,**info)
        if previous is not None:row['mean_price_difference_from_previous']=float(abs(prices-previous).mean())
        rows.append(row);previous=prices;write(folder/'progress.json',rows)
    write(folder/'summary.json',dict(status='European_training_hour_gradient_and_72_LP_hours_passed',curve_count=len(theta),
          gradient=dict(implicit=implicit,finite_difference=finite,absolute_error=error),smooth_certificate=result['certificate'],lp_resolution=rows,
          dependencies={name:digest(ROOT/'tools'/name) for name in ['supply_knot_splines_2025.py','supply_knot_network_2025.py','pilot_supply_knots_lp_2025.py']}))


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,)*2);run()
