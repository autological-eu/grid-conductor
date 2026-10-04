"""Exact positive row scaling experiment; original-unit audit remains mandatory."""
import numpy as np
from scipy import sparse
from storage_coordinator import Block

def condition_rows(block):
 def scale(matrix,coupling,rhs):
  if matrix is None:return None,None,None
  matrix=sparse.csr_matrix(matrix);coupling=sparse.csr_matrix(coupling)
  maxima=np.asarray(abs(matrix).max(axis=1).toarray()).ravel()
  maxima=np.maximum(maxima,np.asarray(abs(coupling).max(axis=1).toarray()).ravel())
  weights=1./np.maximum(1.,maxima)
  diagonal=sparse.diags(weights)
  return diagonal@matrix,diagonal@coupling,weights*np.asarray(rhs)
 eq,coupling,rhs=scale(block.equality,block.coupling,block.rhs)
 if block.inequality is None:ub,v,limit=None,None,None
 else:
  v=block.inequality_coupling
  if v is None:v=sparse.csr_matrix((block.inequality.shape[0],block.coupling.shape[1]))
  ub,v,limit=scale(block.inequality,v,block.limit)
 return Block(block.cost.copy(),list(block.bounds),eq,rhs,coupling,ub,limit,v)
