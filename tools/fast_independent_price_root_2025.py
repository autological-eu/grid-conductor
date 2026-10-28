"""Compiled independent zonal price roots for fixed-exchange diagnostics."""
import math
import numpy as np

try:
    from numba import njit,prange
except ImportError:
    njit=prange=None


if njit is not None:
    @njit(cache=True)
    def _softclip(x,width,tau):
        return min(max(x,0.),width)+tau*(math.log1p(math.exp(-abs(x/tau)))-math.log1p(math.exp(-abs((x-width)/tau))))

    @njit(cache=True,parallel=True)
    def _roots(anchors,capacity,groups,counts,zero,target,valid,thermal_tau,renewable_tau):
        tcount,zcount=target.shape
        price=np.zeros((tcount,zcount))
        for flat in prange(tcount*zcount):
            t=flat//zcount;z=flat%zcount
            if not valid[t,z]:continue
            lo=-1000.;hi=3000.;demand=target[t,z]
            for _ in range(48):
                mid=(lo+hi)/2.;supply=0.
                for k in range(counts[z]):
                    g=groups[z,k];cap=capacity[t,g]
                    if zero[g]:
                        supply+=cap/.01*_softclip(mid,.01,renewable_tau)
                    else:
                        for n in range(5):
                            a=anchors[t,g,n];b=anchors[t,g,n+1]
                            supply+=cap/(5*(b-a))*_softclip(mid-a,b-a,thermal_tau)
                if supply<demand:lo=mid
                else:hi=mid
            price[t,z]=(lo+hi)/2.
        return price


def solve(market,offers,target,valid):
    if njit is None:raise ImportError('numba is required for the fast price root')
    lists=[np.flatnonzero(market.zone==z) for z in range(market.nz)]
    groups=np.full((market.nz,max(map(len,lists))),-1,dtype=np.int64)
    for z,ids in enumerate(lists):groups[z,:len(ids)]=ids
    price=_roots(np.ascontiguousarray(offers['anchors']),
                 np.ascontiguousarray(offers['capacity']),groups,
                 np.array(list(map(len,lists)),dtype=np.int64),
                 np.ascontiguousarray(market.zero),np.ascontiguousarray(target),
                 np.ascontiguousarray(valid),market.thermal_tau,market.renewable_tau)
    q,_=market.supply(price,offers)
    residual=q@market.Z-target
    certified=valid&(abs(residual)<1e-6)
    return price,q,certified,residual
