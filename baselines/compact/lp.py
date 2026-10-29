"""Independent HiGHS replay of the retained hourly joint LP."""
from __future__ import annotations

import highspy
import numpy as np


def solver(model, costs):
    """Build the same 799-offer, link, and free zonal-injection LP."""
    A = model['A']
    ng, nl, nz = (model[key] for key in ('ng', 'nl', 'nz'))
    highs = highspy.Highs()
    highs.setOptionValue('output_flag', False)
    highs.setOptionValue('threads', 1)
    highs.setOptionValue('solver', 'simplex')
    highs.setOptionValue('primal_feasibility_tolerance', 1e-8)
    lp = highspy.HighsLp()
    lp.num_col_, lp.num_row_ = A.shape[1], A.shape[0]
    lp.col_cost_ = np.r_[costs[0], np.zeros(nl + nz)]
    lp.col_lower_ = np.r_[np.zeros(ng), model['link_min'][0], np.full(nz, -np.inf)]
    lp.col_upper_ = np.r_[model['availability'][0], model['link_max'][0], np.full(nz, np.inf)]
    lp.row_lower_ = np.r_[model['load'][0], model['island_rhs'][0], -model['ratings'] - model['flow'][0]]
    lp.row_upper_ = np.r_[model['load'][0], model['island_rhs'][0], model['ratings'] - model['flow'][0]]
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_, lp.a_matrix_.index_, lp.a_matrix_.value_ = A.indptr, A.indices, A.data
    highs.passModel(lp)
    return highs


def clear_hour(highs, model, costs, hour):
    """Reclear one UTC hour and independently check every primal row and bound."""
    ng, nl = model['ng'], model['nl']
    columns = np.arange(ng + nl, dtype=np.int32)
    lower = np.r_[np.zeros(ng), model['link_min'][hour]]
    upper = np.r_[model['availability'][hour], model['link_max'][hour]]
    highs.changeColsBounds(len(columns), columns, lower, upper)
    highs.changeColsCost(ng, np.arange(ng, dtype=np.int32), costs[hour])
    row_lower = np.r_[model['load'][hour], model['island_rhs'][hour],
                      -model['ratings'] - model['flow'][hour]]
    row_upper = np.r_[model['load'][hour], model['island_rhs'][hour],
                      model['ratings'] - model['flow'][hour]]
    rows = np.arange(len(row_lower), dtype=np.int32)
    highs.changeRowsBounds(len(rows), rows, row_lower, row_upper)
    highs.setOptionValue('time_limit', highs.getRunTime() + 10.0)
    highs.run()
    if highs.getModelStatus() != highspy.HighsModelStatus.kOptimal:
        highs.clearSolver()
        highs.setOptionValue('time_limit', highs.getRunTime() + 10.0)
        highs.run()
    if highs.getModelStatus() != highspy.HighsModelStatus.kOptimal:
        raise RuntimeError(f'Hour {hour}: {highs.modelStatusToString(highs.getModelStatus())}')
    solution = highs.getSolution()
    values = np.asarray(solution.col_value)
    actual = model['A'] @ values
    residual = max(float(np.maximum(lower - values[:len(columns)], 0).max(initial=0)),
                   float(np.maximum(values[:len(columns)] - upper, 0).max(initial=0)),
                   float(np.maximum(row_lower - actual, 0).max(initial=0)),
                   float(np.maximum(actual - row_upper, 0).max(initial=0)))
    if residual > 1e-4:
        raise ValueError(f'Hour {hour}: primal residual {residual} MW')
    return values, np.asarray(solution.row_dual), float(highs.getObjectiveValue()), residual
