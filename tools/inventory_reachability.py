"""Necessary/exact single-asset boundary reachability with controllable water spill.

This projects inventory equations and hourly charge/discharge/inventory bounds,
not the network or economic objective. It never substitutes for dispatch.
"""
import numpy as np

def envelope(capacity,retention,charge_energy,discharge_energy,inflow):
    arrays=[np.asarray(v,dtype=float) for v in [retention,charge_energy,discharge_energy,inflow]]
    if not np.isfinite(capacity) or capacity<0 or not len(arrays[0]) or any(v.ndim!=1 or len(v)!=len(arrays[0]) or not np.isfinite(v).all() for v in arrays):raise ValueError('Invalid reachability dimensions/values')
    a=1.;gain=0.;drain=0.;cap=None
    for decay,charge,discharge,water in zip(retention,charge_energy,discharge_energy,inflow):
        if not 0<decay<=1 or min(charge,discharge,water)<0:raise ValueError('Unsupported reachability inputs')
        a*=decay;gain=decay*gain+charge+water;drain=decay*drain+discharge
        cap=capacity if cap is None else min(capacity,decay*cap+charge+water)
    return a,gain,drain,cap
