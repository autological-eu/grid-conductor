"""Compiled quadratic subproblems for the unchanged convex cubic bid objective.

Successive constrained Newton/QP steps, feasible objective line search and true
nonlinear KKT certification. Implicit gradients still use the converged cubic
cost, not the quadratic approximation. No observed price enters clearing.
"""
import time
import numpy as np
from scipy.sparse import diags,vstack


def certificate(cost,p,r):
    x,nu,slack,lam=[r[k] for k in ['x','nu','slack','lam']]
    value,g,_=cost.evaluate(x)
    rd=g+p['E'].T@nu+p['G'].T@lam
    rp=p['E']@x-p['b']
    ri=p['G']@x+slack-p['h']
    primal=max(float(abs(rp).max(initial=0)),float(np.maximum(p['G']@x-p['h'],0).max(initial=0)),float(abs(ri).max(initial=0)))
    gap=float(slack@lam)
    return value,dict(primal_mw=primal*1000,stationarity_eur_mwh=float(abs(rd).max(initial=0)),complementarity_eur=gap*1000)


def passed(cert):
    return cert['primal_mw']<=2e-7 and cert['stationarity_eur_mwh']<=2e-9 and cert['complementarity_eur']<=1e-5


def solve(cost,p,previous=None,max_iterations=2):
    import clarabel
    began=time.perf_counter()
    E,G,b,h=p['E'],p['G'],p['b'],p['h']
    n,ne=E.shape[1],E.shape[0]
    if previous is None:
        x=np.r_[cost.capacity*.5,np.zeros(cost.extra_count)]
        nu,lam=np.zeros(ne),np.zeros(len(h))
        slack=np.maximum(1.,h-G@x)
    else:x,nu,lam,slack=[previous[k].copy() for k in ['x','nu','lam','slack']]
    matrix=vstack([E,G],format='csc')
    rhs=np.r_[b,h]
    settings=clarabel.DefaultSettings()
    settings.verbose=False
    settings.max_iter=100
    settings.tol_feas=1e-12
    settings.tol_gap_abs=1e-11
    settings.tol_gap_rel=1e-12
    settings.max_threads=1
    cones=[clarabel.ZeroConeT(ne),clarabel.NonnegativeConeT(len(h))]
    qp=None
    qp_iterations=0
    backtracks=0
    for iteration in range(max_iterations):
        r=dict(x=x,nu=nu,lam=lam,slack=slack)
        value,cert=certificate(cost,p,r)
        if passed(cert) and (lam>=0).all():
            return dict(**r,objective=value,certificate=cert,iterations=iteration,qp_iterations=qp_iterations,backtracks=backtracks,seconds=time.perf_counter()-began)
        _,g,H=cost.evaluate(x)
        q=g-H*x
        if qp is None:qp=clarabel.DefaultSolver(diags(H,format='csc'),q,matrix,rhs,cones,settings)
        else:qp.update(P=H,q=q)
        sol=qp.solve()
        qp_iterations+=sol.iterations
        if str(sol.status) not in ['Solved','AlmostSolved']:
            raise RuntimeError('Compiled QP subproblem failed: '+str(sol.status))
        candidate=np.asarray(sol.x)
        newnu=np.asarray(sol.z[:ne])
        newlam=np.asarray(sol.z[ne:])
        newslack=np.asarray(sol.s[ne:])
        direction=candidate-x
        old_primal=max(float(abs(E@x-b).max(initial=0)),float(np.maximum(G@x-h,0).max(initial=0)))
        alpha=1.
        if old_primal<=2e-10:
            wanted=float(g@direction)
            for attempt in range(40):
                if cost.evaluate(x+alpha*direction)[0]<=value+1e-4*alpha*wanted+1e-12*max(1.,abs(value)):break
                alpha*=.5
                backtracks+=1
            else:raise RuntimeError('Nonlinear QP objective line search failed')
        x=x+alpha*direction
        nu=(1-alpha)*nu+alpha*newnu
        lam=(1-alpha)*lam+alpha*newlam
        slack=(1-alpha)*slack+alpha*newslack
        # The compiled solver may return AlmostSolved on the most ill-scaled
        # tiny-capacity offers. Never accept its relaxed certificate. Refine
        # the original nonlinear KKT equations instead of repeating stalled QPs.
        if str(sol.status)=='AlmostSolved':break
    from run_forward_hourly_splines_2025 import safe_warm
    refined=safe_warm(cost,p,dict(x=x,nu=nu,slack=slack,lam=lam))
    refined.update(qp_iterations=qp_iterations,backtracks=backtracks,qp_outer_iterations=iteration+1,
        backend='compiled_qp_with_original_nonlinear_polish',seconds=time.perf_counter()-began)
    return refined
