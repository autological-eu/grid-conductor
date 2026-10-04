"""Isolated native HiGHS IPM diagnostic, without simplex crossover.

Preserves LP coefficients and objective. Not enabled in the coordinator; callers
must independently audit primal feasibility and original-unit dual supports.
"""
import math
import numpy as np
from scipy import sparse
from scipy.optimize import OptimizeResult


def solve_native(block, state, time_limit=120.):
    import highspy
    if not np.isfinite(time_limit) or not 0 < time_limit <= 600:
        raise ValueError('Invalid native solver time limit')
    state = np.asarray(state)
    equality = sparse.csr_matrix(block.equality)
    rhs = block.rhs - block.coupling @ state
    inequality = sparse.csr_matrix((0, len(block.cost))) if block.inequality is None else sparse.csr_matrix(block.inequality)
    limit = np.zeros(0) if block.limit is None else block.limit - (0 if block.inequality_coupling is None else block.inequality_coupling @ state)
    matrix = sparse.vstack([equality, inequality], format='csr')
    lp = highspy.HighsLp()
    lp.num_col_ = len(block.cost)
    lp.num_row_ = matrix.shape[0]
    lp.col_cost_ = np.asarray(block.cost)
    lp.col_lower_ = np.array([-highspy.kHighsInf if lo is None else lo for lo, hi in block.bounds])
    lp.col_upper_ = np.array([highspy.kHighsInf if hi is None else hi for lo, hi in block.bounds])
    lp.row_lower_ = np.r_[rhs, np.full(len(limit), -highspy.kHighsInf)]
    lp.row_upper_ = np.r_[rhs, limit]
    lp.a_matrix_.format_ = highspy.MatrixFormat.kRowwise
    lp.a_matrix_.start_ = matrix.indptr
    lp.a_matrix_.index_ = matrix.indices
    lp.a_matrix_.value_ = matrix.data
    solver = highspy.Highs()
    for key, value in [('output_flag', False), ('threads', 1), ('solver', 'ipm'),
                       ('run_crossover', 'off'), ('time_limit', float(time_limit)),
                       ('primal_feasibility_tolerance', 1e-10),
                       ('dual_feasibility_tolerance', 1e-10), ('ipm_optimality_tolerance', 1e-12)]:
        if solver.setOptionValue(key, value) != highspy.HighsStatus.kOk:
            raise RuntimeError(f'Native solver rejected option {key}')
    if solver.passModel(lp) != highspy.HighsStatus.kOk:
        raise RuntimeError('Native solver rejected LP')
    solver.run()
    status = solver.getModelStatus()
    if status == highspy.HighsModelStatus.kInfeasible:
        return None
    if status != highspy.HighsModelStatus.kOptimal:
        raise RuntimeError(f'Native solver did not reach optimal status: {solver.modelStatusToString(status)}')
    solution = solver.getSolution()
    if not solution.value_valid or not solution.dual_valid:
        raise RuntimeError('Native solver has no valid primal/dual arrays')
    x = np.asarray(solution.col_value)
    dual = np.asarray(solution.row_dual)
    reduced = np.asarray(solution.col_dual)
    return OptimizeResult(success=True, x=x, fun=math.fsum(float(c)*float(v) for c,v in zip(block.cost,x)),
                          eqlin=OptimizeResult(marginals=dual[:len(rhs)]),
                          ineqlin=OptimizeResult(marginals=dual[len(rhs):]),
                          lower=OptimizeResult(marginals=np.maximum(reduced, 0.)),
                          upper=OptimizeResult(marginals=np.minimum(reduced, 0.)))
