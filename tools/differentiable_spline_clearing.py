"""Monotone cubic marginal bids, convex clearing, and implicit KKT adjoints.

Power uses GW; objectives use kEUR/h, leaving balance multipliers in EUR/MWh.
No finite-difference fitting, LP bid segments, autodiff dependency or price proxy.
"""
from dataclasses import dataclass
import time
import numpy as np
from scipy.interpolate import BSpline
from scipy.special import expit
from scipy.sparse import bmat, csc_matrix, diags
from scipy.sparse.linalg import splu


class CubicISpline:
    """Integrals of quadratic M-splines yield monotone C2 cubic bid functions."""
    def __init__(self):
        self.degree = 2
        self.knots = np.r_[np.zeros(3), [.25, .5, .75], np.ones(3)]
        self.n = len(self.knots)-self.degree-1
        widths = self.knots[self.degree+1:]-self.knots[:self.n]
        self.m = BSpline(self.knots, np.diag((self.degree+1)/widths), self.degree, extrapolate=True)
        self.i = self.m.antiderivative(); self.j = self.i.antiderivative()
        self.i0 = self.i(0); self.i1 = self.i(1)-self.i0
        self.j0 = self.j(0); self.j1 = self.j(1)-self.j0-self.i0
        self.m0 = self.m(0); self.m1 = self.m(1)
        self.center = self.i(.5)-self.i0
        self.linear_weights = 48*widths/(self.degree+1)

    def evaluate(self, u):
        u = np.asarray(u); v = np.clip(u, 0, 1); low = np.minimum(u, 0); high = np.maximum(u-1, 0)
        I = self.i(v)-self.i0 + low[..., None]*self.m0+high[..., None]*self.m1
        J = self.j(v)-self.j0-v[..., None]*self.i0 + .5*low[..., None]**2*self.m0 + high[..., None]*self.i1+.5*high[..., None]**2*self.m1
        M = self.m(v)
        return I-self.center, J-u[..., None]*self.center, M


BASIS = CubicISpline()


def softplus(x): return np.logaddexp(0., x)


def initial_parameters(count):
    out = np.zeros((count, 5+BASIS.n))
    out[:, 5:] = np.log(np.expm1((BASIS.linear_weights-.001)/20))
    return out


@dataclass
class BidCost:
    capacity: np.ndarray
    source: np.ndarray
    parameter: np.ndarray
    features: np.ndarray
    zero_bid: np.ndarray
    theta: np.ndarray
    extra_count: int
    generation_regularizer: float = .01
    network_regularizer: float = 1e-6

    def __post_init__(self):
        if (self.capacity <= 0).any(): raise ValueError('Positive active capacity required')
        self.ng = len(self.capacity)
        pars = self.theta[self.parameter]
        self.z = np.sum(self.features*pars[:, :5], axis=1)/4
        self.shift = 80*np.tanh(self.z)
        self.weights = .001+20*softplus(pars[:, 5:])
        self.weight_derivative = 20*expit(pars[:, 5:])
        self.shift[self.zero_bid] = 0; self.weights[self.zero_bid] = 0

    def evaluate(self, x):
        q = x[:self.ng]; u = q/self.capacity; I, J, M = BASIS.evaluate(u)
        gradient = np.r_[self.source+self.shift+(I*self.weights).sum(axis=1)+self.generation_regularizer*u,
                         self.network_regularizer*x[self.ng:]]
        hessian = np.r_[((M*self.weights).sum(axis=1)+self.generation_regularizer)/self.capacity,
                        np.full(self.extra_count, self.network_regularizer)]
        value = float((q*(self.source+self.shift)+self.capacity*(J*self.weights).sum(axis=1)+.5*self.generation_regularizer*q*u).sum()
                      +.5*self.network_regularizer*(x[self.ng:]**2).sum())
        if not np.isfinite(value) or not np.isfinite(gradient).all() or not (hessian > 0).all():
            raise ValueError('Nonfinite/nonconvex spline cost')
        return value, gradient, hessian

    def parameter_vjp(self, x, adjoint):
        I, _, _ = BASIS.evaluate(x[:self.ng]/self.capacity)
        factors = np.c_[20*(1-np.tanh(self.z)**2)[:, None]*self.features,
                        I*self.weight_derivative]
        factors[self.zero_bid] = 0
        out = np.zeros_like(self.theta)
        np.add.at(out, self.parameter, -adjoint[:self.ng, None]*factors)
        return out


def fraction(v, dv, safety=1.):
    bad = dv < 0
    return min(1., safety*float(np.min(-v[bad]/dv[bad]))) if bad.any() else 1.


def factor_kkt(hessian, E, G, ratio):
    n = len(hessian); ne = E.shape[0]; ni = G.shape[0]
    matrix = bmat([[diags(hessian), E.T, G.T],
                   [E, csc_matrix((ne, ne)), csc_matrix((ne, ni))],
                   [G, csc_matrix((ni, ne)), -diags(ratio)]], format='csc')
    factor = splu(matrix, permc_spec='COLAMD', options={'Equil':True})
    def solve(rhs):
        value = factor.solve(rhs)
        for _ in range(2):
            residual = rhs-matrix@value
            if np.max(abs(residual)) <= max(1e-10, 1e-10*np.max(abs(rhs))): break
            value += factor.solve(residual)
        return value
    return solve


def solve(cost, E, b, G, h, x0=None, max_iterations=90, gap_tolerance=1e-5, stationarity_tolerance=2e-7):
    """Infeasible-start predictor/corrector Newton; reject failed certificates."""
    began = time.perf_counter(); E=csc_matrix(E); G=csc_matrix(G)
    n=cost.ng+cost.extra_count; ne=len(b); ni=len(h)
    x=np.r_[cost.capacity*.5,np.zeros(cost.extra_count)] if x0 is None else np.asarray(x0).copy()
    nu=np.zeros(ne); slack=np.maximum(1.,h-G@x); lam=np.ones(ni)
    for iteration in range(max_iterations):
        value, grad, H = cost.evaluate(x)
        rd=grad+E.T@nu+G.T@lam; rp=E@x-b; ri=G@x+slack-h
        gap=float(slack@lam)
        primal=max(float(abs(rp).max(initial=0)),float(np.maximum(G@x-h,0).max(initial=0)),float(abs(ri).max(initial=0)))
        if primal <= 2e-8 and abs(rd).max(initial=0) <= stationarity_tolerance and gap <= gap_tolerance:
            break
        linear=factor_kkt(H,E,G,slack/lam)
        def direction(complementarity):
            rhs=np.r_[-rd,-rp,complementarity/lam-ri]
            d=linear(rhs); dx=d[:n]; dn=d[n:n+ne]; dl=d[n+ne:]; ds=-ri-G@dx
            return dx,dn,dl,ds
        dx,dn,dl,ds=direction(slack*lam)
        ap=fraction(slack,ds); ad=fraction(lam,dl)
        mu=gap/ni; mu_aff=float((slack+ap*ds)@(lam+ad*dl)/ni)
        sigma=min(1.,max(0.,mu_aff/mu)**3)
        dx,dn,dl,ds=direction(slack*lam+ds*dl-sigma*mu)
        ap=fraction(slack,ds,.995); ad=fraction(lam,dl,.995)
        x+=ap*dx; slack+=ap*ds; nu+=ad*dn; lam+=ad*dl
        if not np.isfinite(x).all() or min(slack.min(),lam.min()) <= 0:
            raise ValueError('Invalid interior-point iterate')
    else:
        raise RuntimeError(f'Spline Newton iteration limit: primal={primal}, stationarity={abs(rd).max()}, gap={gap}')
    # Convex KKT residuals and complementarity establish allocation optimality.
    return dict(x=x,nu=nu,slack=slack,lam=lam,objective=value,iterations=iteration+1,
                certificate=dict(primal_mw=primal*1000,stationarity_eur_mwh=float(abs(rd).max(initial=0)),complementarity_eur=gap*1000),
                seconds=time.perf_counter()-began)


def adjoint(cost, E, G, solution, dispatch_gradient, price_gradient):
    """Differentiate the converged perturbed KKT equations, including balance duals."""
    x=solution['x']; n=len(x); ne=E.shape[0]
    _,_,H=cost.evaluate(x)
    linear=factor_kkt(H,csc_matrix(E),csc_matrix(G),solution['slack']/solution['lam'])
    # price=-nu; the caller supplies gradients with respect to those prices.
    rhs=np.r_[dispatch_gradient,-np.asarray(price_gradient),np.zeros(G.shape[0])]
    a=linear(rhs)
    return cost.parameter_vjp(x,a[:n])
