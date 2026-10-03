"""Annual shared-inventory workspace. Warm boundaries are not accepted dispatch results."""
import numpy as np
from scipy import sparse
def boundaries(capacity,initial,cyclic,months=12):
 capacity=np.asarray(capacity,dtype=float);initial=np.asarray(initial,dtype=float);cyclic=np.asarray(cyclic,dtype=bool)
 ns=len(capacity)
 if months<1 or capacity.shape!=initial.shape or cyclic.shape!=capacity.shape or not np.isfinite(capacity).all() or not np.isfinite(initial).all() or (capacity<0).any() or (initial<0).any() or (initial>capacity).any():
  raise ValueError('Invalid source inventories/capacities')
 bounds=[(0.,float(v)) for period in range(months+1) for v in capacity]
 rows=[];cols=[];values=[];row=0
 for j,is_cyclic in enumerate(cyclic):
  if is_cyclic:
   rows.extend([row,row]);cols.extend([j,months*ns+j]);values.extend([1.,-1.]);row+=1
  else:bounds[j]=(float(initial[j]),float(initial[j]))
 return bounds,sparse.csr_matrix((values,(rows,cols)),shape=(row,(months+1)*ns)),np.zeros(row)
def validate_warm(state,bounds,equality,rhs,tolerance=1e-7):
 state=np.asarray(state,dtype=float)
 if state.shape!=(len(bounds),) or not np.isfinite(state).all():raise ValueError('Invalid warm inventory dimensions/values')
 if any(v<lo-tolerance or v>hi+tolerance for v,(lo,hi) in zip(state,bounds)):raise ValueError('Warm inventory violates capacity/source bounds')
 if equality.shape[0] and np.max(abs(equality@state-rhs))>tolerance:raise ValueError('Warm inventory violates annual closure')
 return state
