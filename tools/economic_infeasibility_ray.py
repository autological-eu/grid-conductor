"""Diagnose original-cost LP infeasibility; evaluate rays only with zero cost."""
import numpy as np
from scipy import sparse


def native_ray(block,state,seconds=120.):
    import highspy
    if not 0<seconds<=120:raise ValueError('Bounded economic-model ray diagnosis required')
    ne=block.equality.shape[0];A=sparse.vstack([block.equality,block.inequality],format='csr')
    rhs=block.rhs-block.coupling@state;limit=block.limit-block.inequality_coupling@state
    lp=highspy.HighsLp();lp.num_col_=len(block.cost);lp.num_row_=A.shape[0]
    lp.col_cost_=block.cost.copy()
    lp.col_lower_=np.array([-highspy.kHighsInf if lo is None else lo for lo,hi in block.bounds])
    lp.col_upper_=np.array([highspy.kHighsInf if hi is None else hi for lo,hi in block.bounds])
    lp.row_lower_=np.r_[rhs,np.full(len(limit),-highspy.kHighsInf)];lp.row_upper_=np.r_[rhs,limit]
    lp.a_matrix_.format_=highspy.MatrixFormat.kRowwise;lp.a_matrix_.start_=A.indptr;lp.a_matrix_.index_=A.indices;lp.a_matrix_.value_=A.data
    solver=highspy.Highs()
    for key,value in [('output_flag',False),('threads',1),('solver','ipm'),('run_crossover','off'),('time_limit',float(seconds)),
            ('primal_feasibility_tolerance',1e-10),('dual_feasibility_tolerance',1e-10),('ipm_optimality_tolerance',1e-12)]:
        if solver.setOptionValue(key,value)!=highspy.HighsStatus.kOk:raise ValueError('Economic-model ray option rejected')
    if solver.passModel(lp)!=highspy.HighsStatus.kOk:raise ValueError('Economic-model ray LP rejected')
    solver.run();termination=solver.modelStatusToString(solver.getModelStatus())
    if solver.getModelStatus()!=highspy.HighsModelStatus.kInfeasible:
        raise ValueError('No native infeasibility diagnosis: '+termination)
    # IPM without crossover has no simplex ray/basis. Request ray recovery with
    # simplex on the retained original-cost model, not an elastic objective.
    if solver.setOptionValue('solver','simplex')!=highspy.HighsStatus.kOk:
        raise ValueError('Native ray recovery mode rejected')
    status,available,ray=solver.getDualRay()
    if status!=highspy.HighsStatus.kOk or not available:raise ValueError('Native infeasible status supplied no dual ray')
    return np.asarray(ray,dtype=float),termination
