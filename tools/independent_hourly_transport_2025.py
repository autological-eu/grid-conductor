"""Independent calendar-hour bids and exact economic-function averaging."""
import time
import numpy as np
from scipy.sparse import hstack
from forward_hourly_splines_2025 import clock_slots
from spline_europe_2025 import ZERO_TECH
from supply_knot_splines_2025 import initial_parameters
from hourly_spline_reconstruction_2025 import penalties
from transport_curve_physical_transfer_2025 import bids_from_anchors
from sigmoid_month_pairs_2025 import certify


def initialize(source, data, hours):
    neutral = initial_parameters(len(source['groups']))[:, [0,5,6,7,8,9]]
    theta = np.broadcast_to(neutral, (len(hours), *neutral.shape)).copy()
    zero = np.array([g['technology'] in ZERO_TECH for g in source['groups']])
    active = (data['capacity'][hours] > 0) & ~zero[None]
    return theta, active


def economic_nodes(theta):
    increments = .001+20*np.logaddexp(0, theta[..., 1:])
    nodes = np.concatenate([np.zeros((*increments.shape[:-1],1)),
                            np.cumsum(increments, axis=-1)], axis=-1)
    return nodes - ((nodes[...,2]+nodes[...,3])/2)[...,None] + 80*np.tanh(theta[...,0,None]/4)


def raw_from_nodes(nodes):
    increments = np.diff(nodes, axis=-1)
    center = (nodes[...,2]+nodes[...,3])/2
    if (increments <= .001).any() or (abs(center) >= 80).any():
        raise ValueError('Economic mean is outside the declared raw family')
    raw = np.empty_like(nodes)
    raw[...,0] = 4*np.arctanh(center/80)
    raw[...,1:] = np.log(np.expm1((increments-.001)/20))
    return raw


def project(theta, availability, slots, neutral):
    """Average actual economic functions, never raw nonlinear coefficients.

    Equal weight for supported training hours in each weekday/hour slot.
    Unsupported slots use own-month supported mean; absent groups neutral.
    No future-month observations, capacity or source costs enter this operation.
    """
    if theta.shape[:2] != availability.shape or slots.shape != availability.shape:
        raise ValueError('Training hour/group dimensions differ')
    nodes = economic_nodes(theta)
    prior = economic_nodes(neutral)
    profile = np.zeros((168, theta.shape[1],6))
    support = np.zeros((168, theta.shape[1]), dtype=int)
    for g in range(theta.shape[1]):
        active = availability[:,g] > 0
        fallback = nodes[active,g].mean(axis=0) if active.any() else prior[g]
        for slot in range(168):
            selected = active & (slots[:,g] == slot)
            support[slot,g] = selected.sum()
            profile[slot,g] = nodes[selected,g].mean(axis=0) if selected.any() else fallback
    return raw_from_nodes(profile), support


def transferred(profile, groups, hours):
    return profile[clock_slots(groups,hours), np.arange(len(groups))]


def physical_clear(state, market, parameters, hours, bins=100, progress=None):
    """Explicit actual-hour parameters, original physical network; hard PWL LP."""
    from nve_hydro_diagnostics import solver
    from run_regional_water_candidate_2025 import guarded_hour
    source, data, original, _, _ = state
    if parameters.shape != (len(hours), len(source['groups']),6):
        raise ValueError('One explicit parameter row per actual hour/group required')
    started = time.perf_counter(); count = len(source['groups']); ng = count*bins
    matrix = hstack([original[:, np.repeat(np.arange(count),bins)], original[:,count:]], format='csc')
    cost = bids_from_anchors(market.offers(parameters,hours)['anchors'],bins).reshape(len(hours),ng)
    available = np.repeat(data['capacity'][hours]/bins,bins,axis=1)
    model = {k:data[k][hours] for k in ['load','island_rhs','link_min','link_max']}
    model.update(A=matrix,cost=cost,availability=available,ng=ng,nl=source['nl'],nz=source['nz'],
                 zones=source['zones'],ratings=data['ratings'],islands=[None]*data['island_rhs'].shape[1])
    backend = solver(model);backend.setOptionValue('primal_feasibility_tolerance',1e-8)
    x = np.zeros((len(hours),matrix.shape[1])); y = np.zeros((len(hours),matrix.shape[0])); obj = np.zeros(len(hours))
    for t,hour in enumerate(hours):
        if progress is not None and t%168==0:progress(t,len(hours))
        result,value = guarded_hour(backend,model,t,data['flow'][hour])
        if value is None:
            backend = solver(model);backend.setOptionValue('primal_feasibility_tolerance',1e-8)
            result,value = guarded_hour(backend,model,t,data['flow'][hour])
        if value is None:raise RuntimeError(f'Physical transfer failed at {hour}: {result}')
        x[t]=value;y[t]=backend.getSolution().row_dual;obj[t]=result['objective_eur']
    checks = certify(matrix,cost,available,data,hours,x,y,obj,ng,source['nl'],source['nz'])
    q = x[:,:ng].reshape(len(hours),count,bins).sum(axis=2)/1000
    return dict(hours=hours,values=x,row_duals=y,objectives=obj,quantities_gw=q,prices=y[:,:48]),dict(
        seconds=time.perf_counter()-started,bins=bins,certificate=checks,emergency_mwh=0)
