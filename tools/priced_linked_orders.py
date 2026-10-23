"""Check actual dual-price certificates first; search alternatives only if needed.

Same0.05EUR economic tolerance as the original prototype. An auxiliary pricing
LP failure cannot invalidate prices which already satisfy KKT and family checks.
Root rejection remains heuristic; retain the ORIGINAL unrestricted cost bound.
"""
import time
import numpy as np
from scipy.sparse import coo_matrix,vstack
from linked_profile_orders import optimize,price_feasibility,surplus_groups


def check_prices(lp,x,y):
    A=lp['A'];ax=A@x;lower=lp['lower'].copy();upper=lp['upper'].copy()
    lower[lp['integers']]=np.rint(x[lp['integers']]);upper[lp['integers']]=lower[lp['integers']]
    small=(lower>upper)&(lower-upper<=1e-7);upper[small]=lower[small]
    rc=lp['c']-A.T@y;rl=np.isfinite(lp['row_lower']);rh=np.isfinite(lp['row_upper']);cl=np.isfinite(lower);cu=np.isfinite(upper)
    assert np.maximum(y[~rl],0).max(initial=0)<1e-5 and np.maximum(-y[~rh],0).max(initial=0)<1e-5
    assert np.maximum(rc[~cl],0).max(initial=0)<1e-5 and np.maximum(-rc[~cu],0).max(initial=0)<1e-5
    dual=float(np.maximum(y[rl],0)@lp['row_lower'][rl]+np.minimum(y[rh],0)@lp['row_upper'][rh]+np.maximum(rc[cl],0)@lower[cl]+np.minimum(rc[cu],0)@upper[cu])
    gap=abs(dual-float(lp['c']@x));comp=max(float(abs(np.maximum(y[rl],0)*(ax[rl]-lp['row_lower'][rl])).max(initial=0)),float(abs(np.minimum(y[rh],0)*(ax[rh]-lp['row_upper'][rh])).max(initial=0)),float(abs(np.maximum(rc[cl],0)*(x[cl]-lower[cl])).max(initial=0)),float(abs(np.minimum(rc[cu],0)*(x[cu]-upper[cu])).max(initial=0)))
    assert gap<.05 and comp<.05,(gap,comp)
    T,n,nr=lp['T'],lp['n'],lp['nr'];ratios=x[T*n:T*n+len(lp['orders'])];own=[]
    for j,order in enumerate(lp['orders']):
        revenue=float(np.asarray(lp['A'][:T*nr,T*n+j].T@y[:T*nr]).item());own.append(float(ratios[j]*(revenue-order['price']*lp['profiles'][j].sum())))
    checks=[dict(order=lp['orders'][j]['id'],accepted_ratio=float(ratios[j]),own_surplus_eur=own[j],subtree_surplus_eur=sum(own[k] for k in descendants),passes=bool(sum(own[k] for k in descendants)>=-.05)) for j,descendants in surplus_groups(lp,ratios)]
    return checks,dict(duality_gap_eur=gap,complementarity_eur=comp),ratios


def clear(lp,time_limit=10):
    started=time.perf_counter();x,_,allocation=optimize(lp,time_limit=time_limit);fixed,y,pricing=optimize(lp,fixed=x,time_limit=time_limit)
    assert abs(allocation['objective_eur']-pricing['objective_eur'])<.05
    checks,certificate,ratios=check_prices(lp,fixed,y)
    search=dict(status='fixed_integer_duals_verified',seconds=0.,certificate=certificate)
    if not all(v['passes'] for v in checks):
        alternative,search=price_feasibility(lp,fixed,time_limit)
        if alternative is not None:y=alternative;checks,certificate,ratios=check_prices(lp,fixed,y);search['certificate']=certificate
    return dict(values=fixed,row_duals=y,ratios=ratios,mip=allocation,conditional_pricing=pricing,price_search=search,surplus=checks,conditional_surplus_passed=all(v['passes'] for v in checks),seconds=time.perf_counter()-started)


def reclear(lp,max_rounds=8,time_limit=10,wall_limit=120):
    started=time.perf_counter();work=lp.copy();history=[];initial_bound=None;rejected=set();roots={j for j,r in enumerate(lp['orders']) if not r.get('parents')}
    for iteration in range(max_rounds):
        if time.perf_counter()-started>=wall_limit:break
        try:r=clear(work,time_limit=min(time_limit,max(.01,(wall_limit-(time.perf_counter()-started))/3)))
        except (RuntimeError,AssertionError) as error:return dict(status='solver_or_certificate_failure',error=str(error),history=history,seconds=time.perf_counter()-started,initial_allocation_lower_bound_eur=initial_bound,result=None)
        cost=r['conditional_pricing']['objective_eur']
        if initial_bound is None:initial_bound=r['mip'].get('bound_eur',r['mip']['objective_eur'])
        record=dict(iteration=iteration,allocation=r['mip'],conditional_pricing=r['conditional_pricing'],price_search=r['price_search'],objective_eur=cost,price_conditions_passed=r['conditional_surplus_passed'],rejected_roots=[]);history.append(record)
        if r['conditional_surplus_passed']:
            gap=max(0.,cost-initial_bound)
            return dict(status='price_checked_incumbent',history=history,seconds=time.perf_counter()-started,initial_allocation_lower_bound_eur=initial_bound,incumbent_eur=cost,conservative_cost_gap_eur=gap,conservative_cost_gap_fraction=gap/max(abs(cost),1.),global_optimality_claim=gap<.05,result=r)
        if not r['price_search']['status'].startswith('Infeasible'):return dict(status='unresolved_pricing_failure',history=history,seconds=time.perf_counter()-started,initial_allocation_lower_bound_eur=initial_bound,result=None)
        bad=set()
        for check in r['surplus']:
            if check['passes']:continue
            j=next(j for j,order in enumerate(lp['orders']) if order['id']==check['order'])
            while lp['parents'][j]:j=lp['parents'][j][0]
            if j in roots and j in lp['binary_orders'] and j not in rejected:bad.add(j)
        if not bad:return dict(status='no_supported_root_cut',history=history,seconds=time.perf_counter()-started,initial_allocation_lower_bound_eur=initial_bound,result=None)
        rejected|=bad;record['rejected_roots']=[lp['orders'][j]['id'] for j in sorted(bad)];cols=[lp['binary_orders'][j] for j in sorted(bad)]
        cuts=coo_matrix((np.ones(len(cols)),(np.arange(len(cols)),cols)),shape=(len(cols),len(lp['c']))).tocsc()
        work=work|dict(A=vstack([work['A'],cuts],format='csc'),row_lower=np.r_[work['row_lower'],np.full(len(cols),-np.inf)],row_upper=np.r_[work['row_upper'],np.zeros(len(cols))])
    return dict(status='round_or_wall_budget_exhausted',history=history,seconds=time.perf_counter()-started,initial_allocation_lower_bound_eur=initial_bound,result=None)
