"""Source-bounded zero-objective infeasibility supports, not economic duals."""
import numpy as np
from scipy import sparse
from scipy.optimize import OptimizeResult
from storage_coordinator import Block
from check_storage_dual_bounds import objective_support


def zero_objective(block):
    return Block(np.zeros(len(block.cost)),block.bounds,block.equality,block.rhs,block.coupling,
                 block.inequality,block.limit,block.inequality_coupling)


def checked_support(block,state,anchor,ray):
    phase=zero_objective(block);ne=phase.equality.shape[0];nu=phase.inequality.shape[0]
    ray=np.asarray(ray,dtype=float)
    if ray.shape!=(ne+nu,) or not np.isfinite(ray).all() or not np.any(ray):raise ValueError('Finite nonzero full row ray required')
    norm=float(np.max(abs(ray)));chosen=[]
    for sign in [1.,-1.]:
        dual=sign*ray/norm;dual[ne:]=np.minimum(dual[ne:],0.)
        result=OptimizeResult(eqlin=OptimizeResult(marginals=dual[:ne]),ineqlin=OptimizeResult(marginals=dual[ne:]),
                 lower=OptimizeResult(marginals=np.zeros(len(block.cost))),upper=OptimizeResult(marginals=np.zeros(len(block.cost))))
        try:gradient,intercept=objective_support(phase,state,result)
        except ValueError:continue
        value=float(intercept+gradient@state);at_anchor=float(intercept+gradient@anchor)
        if np.isfinite(value) and np.isfinite(at_anchor) and np.isfinite(gradient).all() and value>1e-7 and at_anchor<=1e-7:
            chosen.append((value,result,gradient,float(intercept),at_anchor,sign,norm))
    if not chosen:raise ValueError('No positive globally supported ray cut preserving verified anchor')
    return max(chosen,key=lambda item:item[0])


def native_ray(block,state,seconds=120.):
    import highspy
    if not 0<seconds<=600:raise ValueError('Bounded native ray time required')
    ne=block.equality.shape[0];A=sparse.vstack([block.equality,block.inequality],format='csr')
    rhs=block.rhs-block.coupling@state;limit=block.limit-block.inequality_coupling@state
    lp=highspy.HighsLp();lp.num_col_=len(block.cost);lp.num_row_=A.shape[0]
    lp.col_cost_=np.zeros(len(block.cost));lp.col_lower_=np.array([-highspy.kHighsInf if lo is None else lo for lo,hi in block.bounds]);lp.col_upper_=np.array([highspy.kHighsInf if hi is None else hi for lo,hi in block.bounds])
    lp.row_lower_=np.r_[rhs,np.full(len(limit),-highspy.kHighsInf)];lp.row_upper_=np.r_[rhs,limit]
    lp.a_matrix_.format_=highspy.MatrixFormat.kRowwise;lp.a_matrix_.start_=A.indptr;lp.a_matrix_.index_=A.indices;lp.a_matrix_.value_=A.data
    solver=highspy.Highs()
    for key,value in [('output_flag',False),('threads',1),('solver','simplex'),('time_limit',float(seconds)),('primal_feasibility_tolerance',1e-10),('dual_feasibility_tolerance',1e-10)]:
        if solver.setOptionValue(key,value)!=highspy.HighsStatus.kOk:raise ValueError('Native ray option rejected')
    if solver.passModel(lp)!=highspy.HighsStatus.kOk:raise ValueError('Native ray LP rejected')
    solver.run();termination=solver.modelStatusToString(solver.getModelStatus())
    if solver.getModelStatus()!=highspy.HighsModelStatus.kInfeasible:raise ValueError('No native infeasible ray: '+termination)
    status,available,ray=solver.getDualRay()
    if status!=highspy.HighsStatus.kOk or not available:raise ValueError('Native infeasible status supplied no dual ray')
    return np.asarray(ray,dtype=float),termination
