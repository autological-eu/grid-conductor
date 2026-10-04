"""Bounded Benders coordination of continuous LP blocks.

Local variables retain hourly chronology. Shared variables represent inventories
at block boundaries. Phase-I LPs generate feasibility cuts; objective duals
produce lower bounds. No annual-optimum claim without a certified gap.
"""
from dataclasses import dataclass
import numpy as np
from scipy import sparse
from scipy.optimize import linprog

def solve_master(cost, **kwargs):
    """Solve an equivalent centered/scaled LP and restore original units."""
    cost=np.asarray(cost,dtype=float)
    bounds=kwargs.pop('bounds')
    shift=np.array([lo if lo is not None and np.isfinite(lo) else 0. for lo,hi in bounds])
    scale=np.array([min(100.,max(1.,hi-lo)) if lo is not None and hi is not None and np.isfinite(hi-lo) else 1e6 for lo,hi in bounds])
    transformed=[(None if lo is None else (lo-v)/w,None if hi is None else (hi-v)/w) for (lo,hi),v,w in zip(bounds,shift,scale)]
    for matrix_key,rhs_key in [('A_ub','b_ub'),('A_eq','b_eq')]:
        if kwargs.get(matrix_key) is None:continue
        matrix=sparse.csr_matrix(kwargs[matrix_key]);rhs=np.asarray(kwargs[rhs_key])-matrix@shift
        matrix=matrix.multiply(scale).tocsr()
        row_scale=np.maximum(1.,np.asarray(abs(matrix).max(axis=1).toarray()).ravel())
        kwargs[matrix_key]=matrix.multiply((1/row_scale)[:,None]).tocsr()
        kwargs[rhs_key]=rhs/row_scale
    scaled_cost=cost*scale;objective_scale=max(1.,np.max(abs(scaled_cost)))
    tolerances={'primal_feasibility_tolerance':1e-10,'dual_feasibility_tolerance':1e-10}
    result=linprog(scaled_cost/objective_scale,**kwargs,bounds=transformed,method='highs',options=tolerances)
    if result.status in (2,3,4):
        result=linprog(scaled_cost/objective_scale,**kwargs,bounds=transformed,method='highs-ds',options={**tolerances,'presolve':False})
    if result.success:
        result.x=shift+scale*result.x
        result.fun=float(cost@result.x)
    return result

def bounded_proposal(state,bounds,tolerance):
    """Correct candidate roundoff only; never alter master objective/bounds."""
    state=np.asarray(state,dtype=float).copy()
    for i,(lo,hi) in enumerate(bounds):
        if lo is not None and state[i]<lo:
            if lo-state[i]>tolerance:raise RuntimeError('Inventory proposal exceeds lower bound beyond tolerance')
            state[i]=lo
        if hi is not None and state[i]>hi:
            if state[i]-hi>tolerance:raise RuntimeError('Inventory proposal exceeds upper bound beyond tolerance')
            state[i]=hi
    return state

def feasible_proposal(state,best,matrix,limit,tolerance):
    """Retract only a search proposal toward a checked feasible incumbent.

    The unrestricted master objective/lower bound is never changed.
    """
    A=sparse.csr_matrix(matrix);limit=np.asarray(limit)
    errors=np.asarray(A@state-limit)
    if np.max(errors,initial=0)<=tolerance:return state
    if best is None:raise RuntimeError('No feasible incumbent for proposal repair')
    incumbent=np.asarray(A@best-limit)
    if np.max(incumbent,initial=0)>tolerance:raise RuntimeError('Incumbent violates master inequalities')
    alpha=1.
    for proposed,old in zip(errors,incumbent):
        if proposed>tolerance:
            if old>=-tolerance:alpha=0.;break
            alpha=min(alpha,(-tolerance-old)/(proposed-old))
    candidate=np.asarray(best)+alpha*(np.asarray(state)-best)
    if np.max(A@candidate-limit,initial=0)>tolerance:raise RuntimeError('Repaired proposal violates master inequality')
    return candidate

@dataclass
class Block:
    cost: np.ndarray
    bounds: list
    equality: object
    rhs: np.ndarray
    coupling: object
    inequality: object = None
    limit: object = None
    inequality_coupling: object = None

def solve_block(block, state, phase=False, time_limit=60., first_method='highs', residual_tolerance=None, on_residual_rejection=None,primal_tolerance=1e-10):
    if not np.isfinite(primal_tolerance) or not 1e-10<=primal_tolerance<=1e-7:raise ValueError('Unsupported solver primal tolerance')
    if not np.isfinite(time_limit) or time_limit<=0:raise ValueError('Invalid local solver time limit')
    if first_method not in ('highs','highs-ipm'):raise ValueError('Unsupported first local solver')

    if residual_tolerance is not None and (not np.isfinite(residual_tolerance) or residual_tolerance<=0):raise ValueError('Invalid local residual tolerance')

    A=sparse.csr_matrix(block.equality);B=sparse.csr_matrix(block.coupling)
    U=sparse.csr_matrix((0,len(block.cost))) if block.inequality is None else sparse.csr_matrix(block.inequality)
    V=sparse.csr_matrix((U.shape[0],len(state))) if block.inequality_coupling is None else sparse.csr_matrix(block.inequality_coupling)
    b=np.asarray(block.rhs)-B@state;r=np.zeros(0) if block.limit is None else np.asarray(block.limit)-V@state
    if phase:
        ne,nu=A.shape[0],U.shape[0]
        eq=sparse.hstack([A,sparse.eye(ne),-sparse.eye(ne),sparse.csr_matrix((ne,nu))],format='csr')
        ub=sparse.hstack([U,sparse.csr_matrix((nu,2*ne)),-sparse.eye(nu)],format='csr')
        c=np.r_[np.zeros(len(block.cost)),np.ones(2*ne+nu)]
        bounds=block.bounds+[(0,None)]*(2*ne+nu)
    else:eq,ub,c,bounds=A,U,block.cost,block.bounds
    attempts=[(first_method,True),('highs-ds',False),('highs-ipm',first_method!='highs-ipm')]
    rejected_residual=None
    for method,presolve in attempts:
        options={'time_limit':float(time_limit),'presolve':presolve,'primal_feasibility_tolerance':primal_tolerance,'dual_feasibility_tolerance':1e-10}
        if method=='highs-ipm':options['ipm_optimality_tolerance']=1e-12
        result=linprog(c,A_eq=eq,b_eq=b,A_ub=ub if len(r) else None,b_ub=r if len(r) else None,bounds=bounds,method=method,options=options)
        if residual_tolerance is not None and result.success:
            equality_error=float(np.max(np.abs(eq@result.x-b),initial=0.))
            inequality_error=float(np.max(ub@result.x-r,initial=0.))
            bound_error=max([0.]+[max(0.,lo-x) if lo is not None else 0. for x,(lo,hi) in zip(result.x,bounds)]+[max(0.,x-hi) if hi is not None else 0. for x,(lo,hi) in zip(result.x,bounds)])
            if max(equality_error,inequality_error,bound_error)>residual_tolerance:
                rejected_residual=(method,presolve,equality_error,inequality_error,bound_error)
                if on_residual_rejection is not None:on_residual_rejection(result,dict(method=method,presolve=presolve,equality_residual=equality_error,inequality_violation=inequality_error,bound_violation=bound_error))
                continue
            rejected_residual=None
        if result.status not in (1,2,4):break
    if result.success and rejected_residual is not None:
        raise RuntimeError(f'Local LP residual gate failed after bounded retries: {rejected_residual}')
    if result.status==2 and not phase:return None
    if not result.success:raise RuntimeError(f'Local LP failed: {result.status}: {result.message}')
    gradient=-np.asarray(B.T@result.eqlin.marginals).ravel()
    if len(r):gradient-=np.asarray(V.T@result.ineqlin.marginals).ravel()
    return result,gradient

def coordinate(blocks,bounds,equality=None,rhs=None,max_iterations=200,absolute_gap=1e-5,relative_gap=1e-9,feasibility_tolerance=1e-7,on_iteration=None,initial_state=None,resume=None,on_checkpoint=None,inequality=None,limit=None,on_stage=None,stabilize=True,proposal_fraction=1.,on_failure=None,objective_oracle=None,local_solver=None,master_bound=None,nonnegative_floors=False):
    """Return best feasible state and configured numerical LP-cut bounds, or fail to converge."""
    if not 0<proposal_fraction<=1:raise ValueError('Proposal fraction must be in (0, 1]')
    objective_solver=solve_block if local_solver is None else local_solver
    nx=len(bounds);nb=len(blocks);cuts=[];limits=[];history=[];upper=np.inf;lower=-np.inf;best=None
    theta_bounds=[]
    for block_index,block in enumerate(blocks):
        if nonnegative_floors:
            from storage_objective_floor import nonnegative_objective_floor
            if on_stage is not None:on_stage(dict(stage='source_objective_floor',block=block_index))
            theta_bounds.append((nonnegative_objective_floor(block),None))
            continue
        if on_stage is not None:on_stage(dict(stage='independent_relaxation',block=block_index))
        A=sparse.csr_matrix(block.equality);B=sparse.csr_matrix(block.coupling)
        eq=np.asarray(B.getnnz(axis=1))==0
        U=sparse.csr_matrix((0,len(block.cost))) if block.inequality is None else sparse.csr_matrix(block.inequality)
        V=sparse.csr_matrix((U.shape[0],nx)) if block.inequality_coupling is None else sparse.csr_matrix(block.inequality_coupling)
        keep=np.asarray(V.getnnz(axis=1))==0
        floor_lp=linprog(block.cost,A_eq=A[eq] if eq.any() else None,b_eq=np.asarray(block.rhs)[eq] if eq.any() else None,A_ub=U[keep] if keep.any() else None,b_ub=np.asarray(block.limit)[keep] if keep.any() else None,bounds=block.bounds,method='highs')
        if not floor_lp.success:raise ValueError('A bounded independent block relaxation is required')
        floor=float(floor_lp.fun)
        theta_bounds.append((floor,None))
    E=None if equality is None else sparse.hstack([sparse.csr_matrix(equality),sparse.csr_matrix((len(rhs),nb))],format='csr')
    start_iteration=1
    if resume is not None:
        if master_bound is not None and resume.get('lower_bound_source')!='master_dual':raise ValueError('Cannot reuse primal-derived master bounds')
        if resume['shared_variables']!=nx or resume['blocks']!=nb:raise ValueError('Checkpoint dimensions mismatch')
        cuts=[np.asarray(v,dtype=float) for v in resume['cuts']];limits=resume['limits'];history=resume['history'];upper=np.inf if resume['upper_bound'] is None else resume['upper_bound'];lower=-np.inf if resume['lower_bound'] is None else resume['lower_bound'];best=None if resume['best_state'] is None else np.asarray(resume['best_state']);start_iteration=resume['iteration']+1
    if inequality is not None:
        rows=np.asarray(inequality,dtype=float);values=np.asarray(limit,dtype=float)
        if rows.ndim!=2 or rows.shape!=(len(values),nx) or not np.isfinite(rows).all() or not np.isfinite(values).all():raise ValueError('Invalid master inequality dimensions/values')
        for row,value in zip(rows,values):cuts.append(np.r_[row,np.zeros(nb)]);limits.append(float(value))
    if initial_state is not None and resume is None:
        state=np.asarray(initial_state,dtype=float)
        if len(state)!=nx or any((lo is not None and v<lo-1e-7) or (hi is not None and v>hi+1e-7) for v,(lo,hi) in zip(state,bounds)):raise ValueError('Invalid warm boundary state')
        if equality is not None and np.max(abs(sparse.csr_matrix(equality)@state-rhs))>1e-7:raise ValueError('Warm state violates master equalities')
        cost=0.
        for i,block in enumerate(blocks):
            if on_stage is not None:on_stage(dict(stage='local',block=i))
            local=objective_solver(block,state)
            if local is None:raise ValueError('Warm boundary state is infeasible')
            result,gradient=local
            upper_value,support_value=result.fun,result.fun
            if objective_oracle is not None:upper_value,gradient,support_value=objective_oracle(block,state,result)
            cost+=upper_value
            row=np.r_[gradient,np.zeros(nb)];row[nx+i]=-1;cuts.append(row);limits.append(float(gradient@state-support_value))
        upper=float(cost);best=state.copy()
    for iteration in range(start_iteration,max_iterations+1):
        if on_stage is not None:on_stage(dict(stage='master',iteration=iteration))
        master=solve_master(np.r_[np.zeros(nx),np.ones(nb)],A_ub=sparse.csr_matrix(cuts) if cuts else None,b_ub=limits if cuts else None,A_eq=E,b_eq=rhs,bounds=bounds+theta_bounds)
        if not master.success:raise RuntimeError(f'Master LP failed: {master.status}: {master.message}')
        state=master.x[:nx]
        bound_value=float(master.fun) if master_bound is None else float(master_bound(np.r_[np.zeros(nx),np.ones(nb)],sparse.csr_matrix(cuts) if cuts else sparse.csr_matrix((0,nx+nb)),np.asarray(limits),bounds+theta_bounds,master,nx))
        if not np.isfinite(bound_value):raise RuntimeError('Nonfinite master bound')
        lower=max(lower,bound_value);cost=0.;feasible=True
        if np.isfinite(upper) and lower>upper+absolute_gap:raise RuntimeError('Invalid lower bound exceeds feasible upper bound')
        threshold=absolute_gap+relative_gap*max(1,abs(upper))
        if np.isfinite(upper) and upper-lower<=threshold:
            return dict(status='converged',state=best,objective=upper,lower_bound=lower,gap=max(0.,upper-lower),iterations=iteration,history=history)
        if stabilize and best is not None and np.isfinite(upper) and iteration%5!=0:
            # Level stabilization chooses a nearby proposal without restricting
            # the unrestricted master used for the global lower bound.
            level=lower+.5*(upper-lower)
            width=np.array([max(1.,hi-lo) if lo is not None and hi is not None and np.isfinite(hi-lo) else 1. for lo,hi in bounds])
            original=sparse.hstack([sparse.csr_matrix(cuts),sparse.csr_matrix((len(cuts),nx))],format='csr') if cuts else sparse.csr_matrix((0,2*nx+nb))
            distance=sparse.vstack([sparse.hstack([sparse.eye(nx),sparse.csr_matrix((nx,nb)),-sparse.eye(nx)]),sparse.hstack([-sparse.eye(nx),sparse.csr_matrix((nx,nb)),-sparse.eye(nx)])],format='csr')
            target=sparse.csr_matrix(np.r_[np.zeros(nx),np.ones(nb),np.zeros(nx)][None,:])
            eq=None if E is None else sparse.hstack([E,sparse.csr_matrix((E.shape[0],nx))],format='csr')
            stabilized=solve_master(np.r_[np.zeros(nx+nb),1/width],A_ub=sparse.vstack([original,distance,target],format='csr'),b_ub=np.r_[limits,best,-best,level],A_eq=eq,b_eq=rhs,bounds=bounds+theta_bounds+[(0,None)]*nx)
            if not stabilized.success:raise RuntimeError(f'Level master failed: {stabilized.message}')
            state=stabilized.x[:nx]

        if best is not None and proposal_fraction<1:
            state=best+proposal_fraction*(state-best)

        # Scaled master tolerances can produce tiny negative inventories.
        # Project only the search proposal; the unrestricted lower bound stays
        # untouched, and local LPs verify the corrected candidate independently.
        state=bounded_proposal(state,bounds,feasibility_tolerance)
        if equality is not None and np.max(abs(sparse.csr_matrix(equality)@state-rhs))>feasibility_tolerance:
            raise RuntimeError('Corrected inventory proposal violates master equality')
        if inequality is not None:
            state=feasible_proposal(state,best,inequality,limit,feasibility_tolerance)
            if equality is not None and np.max(abs(sparse.csr_matrix(equality)@state-rhs))>feasibility_tolerance:raise RuntimeError('Repaired inventory proposal violates master equality')
        for i,block in enumerate(blocks):
            if on_stage is not None:on_stage(dict(stage='local',block=i))
            local=objective_solver(block,state)
            if local is None:
                feasible=False;phase,gradient=solve_block(block,state,phase=True)
                if phase.fun<=feasibility_tolerance:
                    if on_failure is not None:
                        on_failure(dict(reason='inconsistent_local_infeasibility',iteration=iteration,block=i,state_mwh=state.tolist(),phase_violation=float(phase.fun),feasibility_tolerance=feasibility_tolerance))
                    raise RuntimeError(f'Inconsistent local infeasibility and Phase-I result: violation={phase.fun:.12g}, block={i}')
                row=np.r_[gradient,np.zeros(nb)];cuts.append(row);limits.append(float(gradient@state-phase.fun))
            else:
                result,gradient=local
                upper_value,support_value=result.fun,result.fun
                if objective_oracle is not None:upper_value,gradient,support_value=objective_oracle(block,state,result)
                cost+=upper_value
                row=np.r_[gradient,np.zeros(nb)];row[nx+i]=-1;cuts.append(row);limits.append(float(gradient@state-support_value))
        if feasible and cost<upper:upper=float(cost);best=state.copy()
        if np.isfinite(upper) and lower>upper+absolute_gap:raise RuntimeError('Invalid lower bound exceeds feasible upper bound')
        gap=upper-lower;history.append(dict(iteration=iteration,lower_bound=float(lower),upper_bound=float(upper),gap=float(gap),candidate_feasible=feasible))
        if on_checkpoint is not None:
            on_checkpoint(dict(schema_version=1,lower_bound_source='master_dual' if master_bound is not None else 'master_primal',shared_variables=nx,blocks=nb,iteration=iteration,cuts=[v.tolist() for v in cuts],limits=limits,history=history,upper_bound=None if not np.isfinite(upper) else upper,lower_bound=None if not np.isfinite(lower) else lower,best_state=None if best is None else best.tolist()))
        if on_iteration is not None:on_iteration(history[-1])
        if np.isfinite(upper) and gap<=absolute_gap+relative_gap*max(1,abs(upper)):
            return dict(status='converged',state=best,objective=upper,lower_bound=lower,gap=max(0.,gap),iterations=iteration,history=history)
    return dict(status='iteration_limit_not_certified',state=best,objective=upper,lower_bound=lower,gap=upper-lower,iterations=max_iterations,history=history)
