"""Equivalent KKT condensation, with residual-checked sparse-LU fallback.

This changes linear algebra only. It does not fit alternative economics, relax
convergence gates, or differentiate a hard LP as if it were globally smooth.
"""
import time
import warnings
import numpy as np
from scipy.linalg import lu_factor, lu_solve, LinAlgWarning
from scipy.sparse import csc_matrix, diags
from differentiable_spline_clearing import factor_kkt as original_factor

STATS = dict(factors=0, fallbacks=0, seconds=0.)


def factor_kkt(hessian,E,G,ratio):
    began=time.perf_counter()
    STATS['factors']+=1
    E,G=csc_matrix(E),csc_matrix(G)
    n,ne=len(hessian),E.shape[0]
    weighted=G.multiply((1/ratio)[:,None])
    W=(G.T@weighted).tocsc()
    W.setdiag(W.diagonal()+hessian)
    coo=W.tocoo()
    # Dense core: only columns coupled by non-bound physical inequalities.
    core=np.unique(np.r_[coo.row[coo.row!=coo.col],coo.col[coo.row!=coo.col]])
    leaf=np.setdiff1d(np.arange(n),core)
    d=W.diagonal()[leaf]
    if (d<=0).any() or len(core)>128:
        STATS['fallbacks']+=1
        return original_factor(hessian,E,G,ratio)
    C=W[core][:,core].toarray()
    Ec=E[:,core].toarray()
    El=E[:,leaf].toarray()
    B=np.block([[C,Ec.T],[Ec,-(El/d)@El.T]])
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',LinAlgWarning)
            factor=lu_factor(B,check_finite=False)
    except Exception:
        STATS['fallbacks']+=1
        return original_factor(hessian,E,G,ratio)
    fallback=None
    def raw_solve(rhs):
        r1,r2,r3=rhs[:n],rhs[n:n+ne],rhs[n+ne:]
        rr=r1+G.T@(r3/ratio)
        small=lu_solve(factor,np.r_[rr[core],r2-El@(rr[leaf]/d)],check_finite=False)
        x=np.empty(n)
        x[core]=small[:len(core)]
        nu=small[len(core):]
        x[leaf]=(rr[leaf]-El.T@nu)/d
        lam=(G@x-r3)/ratio
        return np.r_[x,nu,lam]
    def residual(rhs,value):
        x,nu,lam=value[:n],value[n:n+ne],value[n+ne:]
        return rhs-np.r_[hessian*x+E.T@nu+G.T@lam,E@x,G@x-ratio*lam]
    def solve(rhs):
        nonlocal fallback
        if fallback is not None:return fallback(rhs)
        value=raw_solve(rhs)
        tolerance=max(1e-10,1e-10*np.max(abs(rhs)))
        for _ in range(4):
            r=residual(rhs,value)
            if np.isfinite(value).all() and np.max(abs(r))<=tolerance:return value
            value+=raw_solve(r)
        STATS['fallbacks']+=1
        fallback=original_factor(hessian,E,G,ratio)
        return fallback(rhs)
    STATS['seconds']+=time.perf_counter()-began
    return solve


def install():
    """Explicit process-local backend selection; sealed source bytes unchanged."""
    import differentiable_spline_clearing as smooth
    import hourly_spline_reconstruction_2025 as base
    import hourly_spline_numerical_recovery_2025 as recovery
    for module in [smooth,base,recovery]:module.factor_kkt=factor_kkt
