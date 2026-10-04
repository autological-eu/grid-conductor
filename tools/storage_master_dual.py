"""Original-unit master dual bound diagnostic; not interval certification."""
import math
import numpy as np
from scipy import sparse

def master_dual(cost,matrix,rhs,bounds,result,shared_variables):
 c=np.asarray(cost,dtype=float);A=sparse.csr_matrix(matrix);b=np.asarray(rhs)
 scale=np.array([min(100.,max(1.,hi-lo)) if lo is not None and hi is not None and np.isfinite(hi-lo) else 1e6 for lo,hi in bounds])
 rows=np.maximum(1.,np.asarray(abs(A.multiply(scale)).max(axis=1).toarray()).ravel())
 objective=max(1.,float(np.max(abs(c*scale))))
 z=np.minimum(np.asarray(result.ineqlin.marginals)*objective/rows,0.)
 # Inventory columns have finite bounds; theta columns have no upper bounds.
 # Shrink nonpositive multipliers uniformly if theta reduced costs are negative.
 for _ in range(4):
  priced=np.asarray(A.T@z).ravel();reduced=c-priced
  if np.all(reduced[shared_variables:]>=0):break
  ratio=min(float(c[j]/priced[j]) for j in range(shared_variables,len(c)) if reduced[j]<0)
  z*=ratio*(1.-8*np.finfo(float).eps)
 reduced=c-np.asarray(A.T@z).ravel()
 terms=[]
 for value,(lo,hi) in zip(reduced,bounds):
  endpoint=lo if value>=0 else hi
  if value!=0 and (endpoint is None or not np.isfinite(endpoint)):raise ValueError('Master dual has an unbounded reduced-cost direction')
  terms.append(0. if value==0 else float(value)*float(endpoint))
 bound=math.fsum(float(a)*float(v) for a,v in zip(z,b))+math.fsum(terms)
 return dict(lower_bound_eur=bound,minimum_theta_reduced_cost=float(np.min(reduced[shared_variables:])),scope='Floating-point dual diagnostic without master equalities; not interval certification')
