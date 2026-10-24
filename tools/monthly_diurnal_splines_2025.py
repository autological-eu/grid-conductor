"""Monthly shared local-hour curves; exact chain-rule aggregation of gradients."""
import numpy as np
from forward_hourly_splines_2025 import clock_slots
from supply_knot_splines_2025 import initial_parameters
from spline_europe_2025 import ZERO_TECH


def labels(groups,hours):
    return clock_slots(groups,hours)%24


def initialize(sealed,data,hours):
    groups=sealed['groups']
    neutral=initial_parameters(len(groups))[:,[0,5,6,7,8,9]]
    theta=np.broadcast_to(neutral,(24,*neutral.shape)).copy()
    active=np.zeros((24,len(groups)),dtype=bool)
    clock=labels(groups,hours)
    for g,group in enumerate(groups):
        if group['technology'] not in ZERO_TECH:
            np.logical_or.at(active[:,g],clock[:,g],data['capacity'][hours,g]>0)
    return theta,active


def expand(theta,clock):
    return theta[clock,np.arange(theta.shape[1])]


def aggregate(hourly_gradient,clock):
    out=np.zeros((24,hourly_gradient.shape[1],6))
    for g in range(hourly_gradient.shape[1]):
        np.add.at(out[:,g],clock[:,g],hourly_gradient[:,g])
    return out


def penalties(theta,initial,active,design):
    delta=theta-initial
    n=max(1,int(active.sum())*6)
    ridge=design['hourly_shrinkage']*float((delta[active]**2).sum())/n
    gradient=2*design['hourly_shrinkage']*delta*active[:,:,None]/n
    pair=active&np.roll(active,-1,axis=0)
    difference=np.roll(delta,-1,axis=0)-delta
    m=max(1,int(pair.sum())*6)
    smooth=design['temporal_penalty']*float((difference[pair]**2).sum())/m
    grad=2*design['temporal_penalty']*difference*pair[:,:,None]/m
    gradient+=np.roll(grad,1,axis=0)-grad
    return ridge+smooth,gradient,dict(monthly_shrinkage=ridge,cyclic_diurnal_penalty=smooth)
