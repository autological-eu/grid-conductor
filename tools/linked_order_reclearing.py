"""Bounded root-rejection heuristic with a retained unrestricted cost bound.

Supporting-price failure does not justify claiming a global EUPHEMIA cut.
These root cuts are explicitly heuristic. A successful, checked incumbent and
the ORIGINAL allocation relaxation bound give a conservative cost interval;
later heuristic-cut bounds must never replace that lower bound.
"""
import time
import numpy as np
from scipy.sparse import coo_matrix,vstack
from linked_profile_orders import clear


def reclear(lp,max_rounds=8,time_limit=10,wall_limit=120):
    began=time.perf_counter();work=lp.copy();history=[];initial_bound=None;rejected=set()
    roots={j for j,r in enumerate(lp['orders']) if not r.get('parents')}
    for iteration in range(max_rounds):
        if time.perf_counter()-began>=wall_limit:break
        try:result=clear(work,time_limit=min(time_limit,max(.01,(wall_limit-(time.perf_counter()-began))/3)))
        except (RuntimeError,AssertionError) as error:
            return dict(status='solver_or_certificate_failure',error=str(error),history=history,seconds=time.perf_counter()-began,initial_allocation_lower_bound_eur=initial_bound,result=None)
        mip=result['mip'];price=result['price_search'];cost=result['conditional_pricing']['objective_eur']
        if initial_bound is None:initial_bound=mip.get('bound_eur',mip['objective_eur'])
        record=dict(iteration=iteration,allocation=mip,conditional_pricing=result['conditional_pricing'],price_search=price,objective_eur=cost,price_conditions_passed=result['conditional_surplus_passed'],rejected_roots=[])
        history.append(record)
        if result['conditional_surplus_passed']:
            gap=max(0.,cost-initial_bound)
            return dict(status='price_checked_incumbent',history=history,seconds=time.perf_counter()-began,initial_allocation_lower_bound_eur=initial_bound,incumbent_eur=cost,conservative_cost_gap_eur=gap,conservative_cost_gap_fraction=gap/max(abs(cost),1.),global_optimality_claim=gap<.05,result=result)
        if not price['status'].startswith('Infeasible'):
            return dict(status='unresolved_pricing_failure',history=history,seconds=time.perf_counter()-began,initial_allocation_lower_bound_eur=initial_bound,result=None)
        bad_roots=set()
        for check in result['surplus']:
            if check['passes']:continue
            j=next(j for j,r in enumerate(lp['orders']) if r['id']==check['order'])
            while lp['parents'][j]:j=lp['parents'][j][0]
            if j in roots and j in lp['binary_orders'] and j not in rejected:bad_roots.add(j)
        if not bad_roots:
            return dict(status='no_supported_root_cut',history=history,seconds=time.perf_counter()-began,initial_allocation_lower_bound_eur=initial_bound,result=None)
        rejected|=bad_roots
        record['rejected_roots']=[lp['orders'][j]['id'] for j in sorted(bad_roots)]
        cols=[lp['binary_orders'][j] for j in sorted(bad_roots)]
        cuts=coo_matrix((np.ones(len(cols)),(np.arange(len(cols)),cols)),shape=(len(cols),len(lp['c']))).tocsc()
        work=work|dict(A=vstack([work['A'],cuts],format='csc'),row_lower=np.r_[work['row_lower'],np.full(len(cols),-np.inf)],row_upper=np.r_[work['row_upper'],np.zeros(len(cols))])
    return dict(status='round_or_wall_budget_exhausted',history=history,seconds=time.perf_counter()-began,initial_allocation_lower_bound_eur=initial_bound,result=None)
