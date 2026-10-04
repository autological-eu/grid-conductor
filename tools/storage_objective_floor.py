"""Conservative zero objective floors for nonnegative source-bounded LP costs.

Avoid an expensive relaxation solve. Reject negative costs or costed variables
whose state-independent source bounds do not establish nonnegativity.
"""
import numpy as np
from check_storage_dual_bounds import implied_bounds


def nonnegative_objective_floor(block):
    cost=np.asarray(block.cost)
    if not np.isfinite(cost).all() or (cost<0).any():
        raise ValueError('Zero floor requires finite nonnegative objective coefficients')
    bounds=implied_bounds(block,np.zeros(block.coupling.shape[1]),state_independent=True)
    for coefficient,(lo,hi) in zip(cost,bounds):
        if coefficient and (lo is None or not np.isfinite(lo) or lo<0):
            raise ValueError('Zero floor requires state-independent nonnegative bounds on every costed variable')
    return 0.
