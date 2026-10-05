"""Original-unit finite-box master support including equality multipliers.

Floating-point LP support, not outward-rounded interval certification.
"""
import math
import numpy as np
from scipy import sparse


def support(cost,A,b,E,d,bounds,z,y,shared_variables):
    cost=np.asarray(cost,dtype=float);A=sparse.csr_matrix(A);E=sparse.csr_matrix(E)
    b=np.asarray(b,dtype=float);d=np.asarray(d,dtype=float);z=np.asarray(z,dtype=float);y=np.asarray(y,dtype=float)
    if A.shape!=(len(b),len(cost)) or E.shape!=(len(d),len(cost)) or len(bounds)!=len(cost) or z.shape!=b.shape or y.shape!=d.shape or not all(np.isfinite(v).all() for v in [cost,b,d,z,y]) or (z>0).any():
        raise ValueError('Finite correctly sized original-unit master multipliers required')
    if not 0<shared_variables<len(cost):raise ValueError('Valid inventory/objective split required')
    reduced=cost-np.asarray(A.T@z+E.T@y).ravel();terms=[]
    for value,(lo,hi) in zip(reduced,bounds):
        endpoint=lo if value>=0 else hi
        if value!=0 and (endpoint is None or not np.isfinite(endpoint)):
            raise ValueError('Unbounded master reduced-cost direction')
        terms.append(0. if value==0 else float(value)*float(endpoint))
    return dict(lower_bound_eur=math.fsum(float(a)*float(v) for a,v in zip(z,b))+math.fsum(float(a)*float(v) for a,v in zip(y,d))+math.fsum(terms),
                minimum_theta_reduced_cost=float(np.min(reduced[shared_variables:])),
                scope='Original-unit floating-point finite-box dual support including equalities; not interval certification')


def restore(cost,A,b,E,d,bounds,result,shared_variables):
    cost=np.asarray(cost,dtype=float);A=sparse.csr_matrix(A);E=sparse.csr_matrix(E)
    scale=np.array([min(100.,max(1.,hi-lo)) if lo is not None and hi is not None and np.isfinite(hi-lo) else 1e6 for lo,hi in bounds])
    def row_scales(matrix):
        return np.maximum(1.,np.asarray(abs(matrix.multiply(scale)).max(axis=1).toarray()).ravel()) if matrix.shape[0] else np.empty(0)
    objective=max(1.,float(np.max(abs(cost*scale))))
    z=np.minimum(np.asarray(result.ineqlin.marginals)*objective/row_scales(A),0.)
    y=np.asarray(result.eqlin.marginals)*objective/row_scales(E)
    # Numerical support must price all unbounded epigraph directions safely.
    # Equality columns for epigraphs are zero in this model.
    if E[:,shared_variables:].nnz:raise ValueError('Unsupported objective coupling in master equalities')
    for _ in range(4):
        priced=np.asarray(A.T@z).ravel();reduced=cost-priced
        if np.all(reduced[shared_variables:]>=0):break
        ratio=min(float(cost[j]/priced[j]) for j in range(shared_variables,len(cost)) if reduced[j]<0)
        z*=ratio*(1.-8*np.finfo(float).eps)
    return support(cost,A,b,E,d,bounds,z,y,shared_variables),z,y
