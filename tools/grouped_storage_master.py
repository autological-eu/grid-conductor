"""Inventory master with explicit grouped objective epigraphs.

A monthly support constrains the sum of its sub-block objectives. It must never
be assigned separately to every sub-block. Candidate inventory feasibility still
requires local LP witnesses; this relaxation only supplies a numerical bound.
"""
import numpy as np
from scipy import sparse
from storage_coordinator import solve_master,bounded_proposal,feasible_proposal
from storage_master_dual import master_dual
from annual_inventory_workspace import validate_warm
from grouped_master_dual import restore


def cut_rows(nx,nb,cuts):
    rows=[];limits=[]
    for indices,gradient,intercept in cuts:
        indices=list(indices);gradient=np.asarray(gradient,dtype=float)
        if not indices or len(set(indices))!=len(indices) or any(not isinstance(i,(int,np.integer)) or not 0<=i<nb for i in indices) or gradient.shape!=(nx,) or not np.isfinite(gradient).all() or not np.isfinite(intercept):
            raise ValueError('Finite correctly sized cut and unique objective group required')
        theta=sparse.csr_matrix((-np.ones(len(indices)),(np.zeros(len(indices),dtype=int),indices)),shape=(1,nb))
        rows.append(sparse.hstack([sparse.csr_matrix(gradient.reshape(1,-1)),theta],format='csr'));limits.append(-float(intercept))
    return (sparse.vstack(rows,format='csr') if rows else sparse.csr_matrix((0,nx+nb))),np.asarray(limits)


def solve(bounds,equality,rhs,inequality,limit,floors,cuts,warm,include_equalities=False,witness_path=None):
    nx=len(bounds);nb=len(floors);floors=np.asarray(floors,dtype=float)
    if nx<1 or nb<1 or not np.isfinite(floors).all():raise ValueError('Valid shared inventory/objective domain required')
    equality=sparse.csr_matrix(equality);inequality=sparse.csr_matrix(inequality)
    rhs=np.asarray(rhs,dtype=float);limit=np.asarray(limit,dtype=float)
    if equality.shape!=(len(rhs),nx) or inequality.shape!=(len(limit),nx) or not np.isfinite(rhs).all() or not np.isfinite(limit).all():
        raise ValueError('Inventory constraint dimensions or values invalid')
    warm=validate_warm(warm,bounds,equality,rhs)
    if np.max(inequality@warm-limit,initial=0.)>1e-7:raise ValueError('Verified anchor violates necessary inventory constraints')
    objective_rows,objective_limits=cut_rows(nx,nb,cuts)
    A=sparse.vstack([sparse.hstack([inequality,sparse.csr_matrix((len(limit),nb))]),objective_rows],format='csr')
    b=np.r_[limit,objective_limits];E=sparse.hstack([equality,sparse.csr_matrix((len(rhs),nb))],format='csr')
    cost=np.r_[np.zeros(nx),np.ones(nb)];all_bounds=list(bounds)+[(float(f),None) for f in floors]
    result=solve_master(cost,A_eq=E,b_eq=rhs,A_ub=A,b_ub=b,bounds=all_bounds)
    if not result.success:raise RuntimeError('Grouped relaxation did not solve')
    if include_equalities:
        diagnostic,z,y=restore(cost,A,b,E,rhs,all_bounds,result,nx)
    else:diagnostic=master_dual(cost,A,b,all_bounds,result,nx)
    diagnostic.pop('scope',None)
    if diagnostic['lower_bound_eur']>float(result.fun)+1e-7:raise ValueError('Master support exceeds master primal')
    # Roundoff-only proposal repair never changes the unrestricted objective or
    # its dual support. A repaired boundary vector is not a dispatch witness.
    candidate=bounded_proposal(result.x[:nx],bounds,1e-7)
    candidate=feasible_proposal(candidate,warm,inequality,limit,1e-7)
    candidate=validate_warm(candidate,bounds,equality,rhs)
    if np.max(inequality@candidate-limit,initial=0.)>1e-7:raise ValueError('Candidate violates inventory envelope')
    if witness_path is not None:
        from pathlib import Path
        path=Path(witness_path)
        if not include_equalities or path.exists():raise ValueError('New full-equality master witness path required')
        arrays=dict(cost=cost,inequality_rhs=b,equality_rhs=np.asarray(rhs),
                    bounds=np.asarray([(float('-inf') if lo is None else lo,float('inf') if hi is None else hi) for lo,hi in all_bounds]),
                    inequality_duals=z,equality_duals=y,primal=result.x,shared_variables=np.asarray(nx))
        for name,matrix in [('inequality',A),('equality',E)]:
            arrays.update({name+'_data':matrix.data,name+'_indices':matrix.indices,name+'_indptr':matrix.indptr,name+'_shape':np.asarray(matrix.shape)})
        np.savez_compressed(path,**arrays)
    return dict(**diagnostic,master_objective_eur=float(result.fun),proposal_mwh=candidate.tolist(),
                proposal_equality_residual=float(np.max(abs(equality@candidate-rhs),initial=0.)),
                proposal_inventory_violation=float(max(0.,np.max(inequality@candidate-limit,initial=0.))),
                original_master_equality_residual=float(np.max(abs(E@result.x-rhs),initial=0.)),
                original_master_inequality_violation=float(max(0.,np.max(A@result.x-b,initial=0.))),
                scope='Grouped objective relaxation and envelope-feasible proposal only; requires local dispatch witnesses and convergence verification.')
