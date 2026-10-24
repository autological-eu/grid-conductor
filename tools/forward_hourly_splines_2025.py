"""Calendar-hour fits; exact mean economic curves for next-month LP inference.

Only parameters, training availability and local clock labels enter projection.
Prices, generation targets and target-month MW never enter the learned profile.
The average is of cubic functions, not of nonlinear raw spline parameters.
"""
import numpy as np
import pandas as pd
from scipy.sparse import hstack
from supply_knot_splines_2025 import KnotCost, coefficients
from spline_europe_2025 import ZERO_TECH
from intraday_offer_bids_2025 import TIMEZONES
from sigmoid_month_pairs_2025 import certify


def month_hours(month):
    if month not in range(1, 13):
        raise ValueError('2025 month required; no December-to-January wrap')
    clock = pd.date_range('2025-01-01', periods=8760, freq='h', tz='UTC')
    return np.flatnonzero(clock.month == month)


def clock_slots(groups, hours):
    utc = pd.Timestamp('2025-01-01', tz='UTC') + pd.to_timedelta(hours, unit='h')
    cache = {}
    for g in groups:
        country = g['zone'][:2]
        if country not in cache:
            local = utc.tz_convert(TIMEZONES[country])
            cache[country] = np.asarray(local.dayofweek * 24 + local.hour)
    return np.column_stack([cache[g['zone'][:2]] for g in groups])


def polynomials(theta, zero):
    """Economic markup coefficients, local z = u - interval*.2; EUR/MWh."""
    shape = theta.shape[:-1]
    flat = theta.reshape(-1, 6)
    a, b, c, d, _, _ = coefficients(.001 + 20*np.logaddexp(0, flat[:, 1:]))
    center = ((a[:, 2]*.1 + b[:, 2])*.1 + c[:, 2])*.1 + d[:, 2]
    d = d + (80*np.tanh(flat[:, 0]/4) - center)[:, None]
    result = np.stack([a, b, c, d], axis=-1).reshape(*shape, 5, 4)
    result[..., np.asarray(zero, dtype=bool), :, :] = 0
    return result


def project(theta, availability, slots, zero, neutral):
    """Equal-weight supported training hours; unsupported slot -> own-month mean.

    Entirely absent resources use a declared neutral prior, never future targets.
    Return support counts so fallback coverage is visible.
    """
    if theta.shape[:2] != availability.shape or slots.shape != availability.shape:
        raise ValueError('Projection dimensions do not match training hours')
    if not np.isfinite(theta).all():
        raise ValueError('Nonfinite curve parameters')
    curves = polynomials(theta, zero)
    prior = polynomials(neutral[None], zero)[0]
    count, ng = len(theta), theta.shape[1]
    profile = np.zeros((168, ng, 5, 4))
    support = np.zeros((168, ng), dtype=int)
    for g in range(ng):
        active = availability[:, g] > 0
        fallback = curves[active, g].mean(axis=0) if active.any() else prior[g]
        for slot in range(168):
            selected = active & (slots[:, g] == slot)
            support[slot, g] = selected.sum()
            profile[slot, g] = curves[selected, g].mean(axis=0) if selected.any() else fallback
    return profile, support


def interval_bids(poly, bins=20):
    """Exact interval-average prices for a fixed-knot cubic; no quadrature."""
    edges = np.linspace(0, 1, bins+1)
    i = np.minimum((edges/.2).astype(int), 4)
    z = edges - i*.2
    a, b, c, d = np.moveaxis(poly, -1, 0)
    spans = a*.2**4/4 + b*.2**3/3 + c*.2**2/2 + d*.2
    prefix = np.concatenate([np.zeros((*spans.shape[:-1], 1)), np.cumsum(spans, axis=-1)], axis=-1)
    integral = prefix[..., i] + a[..., i]*z**4/4 + b[..., i]*z**3/3 + c[..., i]*z**2/2 + d[..., i]*z
    return np.diff(integral, axis=-1)*bins


class CachedKnotCost(KnotCost):
    """Algebraically identical objective, cached fixed-parameter polynomial data."""
    def __post_init__(self):
        super().__post_init__()
        self.abcd = coefficients(self.increments)
        a, b, c, d, _, _ = self.abcd
        self.center = ((a[:, 2]*.1+b[:, 2])*.1+c[:, 2])*.1+d[:, 2]
        self.prefix = np.c_[np.zeros(self.ng), np.cumsum(a*.2**4/4+b*.2**3/3+c*.2**2/2+d*.2, axis=1)]

    def evaluate(self, x):
        q = x[:self.ng]
        u = q/self.capacity
        v = np.clip(u, 0, 1)
        i = np.minimum((v/.2).astype(int), 4)
        z, r = v-i*.2, np.arange(self.ng)
        a, b, c, d, y, slopes = self.abcd
        aa, bb, cc, dd = [p[r, i] for p in [a,b,c,d]]
        low, high = np.minimum(u, 0), np.maximum(u-1, 0)
        price = ((aa*z+bb)*z+cc)*z+dd + low*slopes[:,0]+high*slopes[:,-1]-self.center
        integral = self.prefix[r,i]+aa*z**4/4+bb*z**3/3+cc*z**2/2+dd*z
        integral += .5*low**2*slopes[:,0]+high*y[:,-1]+.5*high**2*slopes[:,-1]-u*self.center
        slope = np.where(u<0, slopes[:,0], np.where(u>1, slopes[:,-1], (3*aa*z+2*bb)*z+cc))
        price[self.zero_bid], integral[self.zero_bid], slope[self.zero_bid] = 0,0,0
        grad = np.r_[self.source+self.shift+price+self.generation_regularizer*u, self.network_regularizer*x[self.ng:]]
        hess = np.r_[(slope+self.generation_regularizer)/self.capacity, np.full(self.extra_count,self.network_regularizer)]
        value = float((q*(self.source+self.shift)+self.capacity*integral+.5*self.generation_regularizer*q*u).sum()+.5*self.network_regularizer*(x[self.ng:]**2).sum())
        if not np.isfinite(value) or not np.isfinite(grad).all() or not (hess>0).all():
            raise ValueError('Invalid cached monotone cost')
        return value, grad, hess


def clear_lp(sealed, data, A, emergency, hours, bids, bins=20):
    """Original LP and original certificate gates; bids are markups only."""
    from nve_hydro_diagnostics import solver
    from run_regional_water_candidate_2025 import guarded_hour
    count = len(sealed['groups'])
    ng = count*bins + emergency.shape[1]
    matrix = hstack([A[:,np.repeat(np.arange(count),bins)], emergency, A[:,count:]],format='csc')
    zero = np.array([g['technology'] in ZERO_TECH for g in sealed['groups']])
    source = data['source_cost'][hours].copy()
    source[:,zero] = 0
    cost = np.c_[(source[:,:,None]+bids).reshape(len(hours),-1),data['emergency_cost'][hours]]
    av = np.c_[np.repeat(data['capacity'][hours]/bins,bins,axis=1),data['emergency_available'][hours]]
    model = {k:data[k][hours] for k in ['load','island_rhs','link_min','link_max']}
    model.update(A=matrix,cost=cost,availability=av,ng=ng,nl=sealed['nl'],nz=sealed['nz'],zones=sealed['zones'],ratings=data['ratings'],islands=[None]*data['island_rhs'].shape[1])
    h = solver(model)
    h.setOptionValue('primal_feasibility_tolerance',1e-8)
    x, y, obj = np.zeros((len(hours),matrix.shape[1])),np.zeros((len(hours),matrix.shape[0])),np.zeros(len(hours))
    for t,hour in enumerate(hours):
        record,value = guarded_hour(h,model,t,data['flow'][hour])
        if value is None:
            h = solver(model)
            h.setOptionValue('primal_feasibility_tolerance',1e-8)
            record,value = guarded_hour(h,model,t,data['flow'][hour])
        if value is None:
            raise RuntimeError(f'LP failed at {hour}: {record}')
        x[t],y[t],obj[t] = value,h.getSolution().row_dual,record['objective_eur']
    if np.maximum(x[:,count*bins:ng],0).sum()>1e-6:
        raise ValueError('Artificial emergency generation')
    certificate = certify(matrix,cost,av,data,hours,x,y,obj,ng,sealed['nl'],sealed['nz'])
    return dict(values=x,row_duals=y,objectives=obj,hours=hours,quantities=x[:,:count*bins].reshape(len(hours),count,bins).sum(axis=2)),certificate
