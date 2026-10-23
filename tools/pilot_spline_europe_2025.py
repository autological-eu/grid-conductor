"""Bounded European training-hour feasibility, timing and gradient pilot."""
import json
import resource
import time
from pathlib import Path
import numpy as np
from sigmoid_month_pairs_2025 import ROOT,OUT as SOURCE,digest,write
from differentiable_spline_clearing import initial_parameters
from spline_europe_2025 import load,clear_hour,backward


def run():
    began=time.perf_counter();sealed,data,A=load();theta=initial_parameters(len(sealed['parameters']))
    folder=ROOT/'data/bidding-zone-network-2025/differentiable-spline-pilot-v1';folder.mkdir(exist_ok=False)
    record=json.loads((SOURCE/'summary.json').read_text())['pairs'][0]['witnesses']['train_control']
    assert digest(ROOT/record['path'])==record['sha256']
    with np.load(ROOT/record['path']) as z:
        ref=z['values'];hours=z['hours'];K=sealed['design']['segments'];G=len(sealed['groups'])
        initial=np.c_[ref[:,:G*K].reshape(len(hours),G,K).sum(axis=2),ref[:,sealed['ng']:]]/1000
    rows=[]
    for hour in [12,348,504]:
        t=int(np.flatnonzero(hours==hour)[0]);r=clear_hour(sealed,data,A,theta,hour,initial[t]);p=r['problem']
        row=dict(hour=hour,seconds=r['seconds'],iterations=r['iterations'],certificate=r['certificate'],min_price=float(r['prices'].min()),max_price=float(r['prices'].max()))
        rows.append(row);write(folder/'progress.json',rows);print('pilot',row,flush=True)
        if hour==348:
            gx=np.zeros(A.shape[1]);gp=np.zeros(sealed['nz']);gp[sealed['zones'].index('DE-LU')]=.02
            for j,g in enumerate(sealed['groups']):
                if g['country']=='DE' and g['family']=='Gas':gx[j]=.1
            grad=backward(r,gx,gp)
            chosen=np.unravel_index(np.argmax(abs(grad)),grad.shape);eps=1e-4
            plus=theta.copy();minus=theta.copy();plus[chosen]+=eps;minus[chosen]-=eps
            def objective(state):
                rr=clear_hour(sealed,data,A,state,hour,initial[t]);return float(gx@rr['full_x']+gp@rr['prices'])
            finite=(objective(plus)-objective(minus))/(2*eps)
            row['gradient']=dict(parameter=list(map(int,chosen)),implicit=float(grad[chosen]),finite_difference=float(finite),absolute_error=abs(float(grad[chosen])-finite))
            if abs(grad[chosen]-finite)>max(5e-4,.01*abs(finite)):
                write(folder/'failure.json',row);raise ValueError('European gradient check failed')
    write(folder/'summary.json',dict(status='three_training_hours_and_european_gradient_passed',rows=rows,seconds=time.perf_counter()-began,
          sources={str(p.relative_to(ROOT)):digest(p) for p in [SOURCE/'inputs.json',SOURCE/'inputs.npz',SOURCE/'network.npz']},
          dependencies={name:digest(ROOT/'tools'/name) for name in ['differentiable_spline_clearing.py','spline_europe_2025.py','pilot_spline_europe_2025.py']}))


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,)*2);run()
