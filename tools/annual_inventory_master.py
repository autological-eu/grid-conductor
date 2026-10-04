"""Sparse initial annual cut master; proposals are not feasible dispatch results."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy import sparse
from storage_coordinator import solve_master, bounded_proposal, feasible_proposal
from annual_inventory_workspace import validate_warm
from storage_master_dual import master_dual
from monthly_dispatch import digest, save


def solve_cut_master(bounds, equality, rhs, inequality, limit, floors, cuts, warm=None):
    nx=len(bounds); nb=len(floors)
    if nb<1 or not np.isfinite(floors).all():raise ValueError('Invalid objective floors')
    rows=[sparse.hstack([sparse.csr_matrix(inequality),sparse.csr_matrix((len(limit),nb))],format='csr')]
    values=list(limit)
    for month,gradient,intercept in cuts:
        gradient=np.asarray(gradient,dtype=float)
        if not 0<=month<nb or gradient.shape!=(nx,) or not np.isfinite(gradient).all() or not np.isfinite(intercept):
            raise ValueError('Invalid objective cut')
        theta=sparse.csr_matrix(([-1.],([0],[month])),shape=(1,nb))
        rows.append(sparse.hstack([sparse.csr_matrix(gradient.reshape(1,-1)),theta],format='csr'))
        values.append(-float(intercept))
    A=sparse.vstack(rows,format='csr'); b=np.asarray(values)
    E=sparse.hstack([sparse.csr_matrix(equality),sparse.csr_matrix((len(rhs),nb))],format='csr')
    cost=np.r_[np.zeros(nx),np.ones(nb)]
    all_bounds=list(bounds)+[(float(v),None) for v in floors]
    result=solve_master(cost,A_eq=E,b_eq=rhs,A_ub=A,b_ub=b,bounds=all_bounds)
    if not result.success:raise RuntimeError('Initial cut master failed; no dispatch proposal accepted')
    eq=float(np.max(abs(E@result.x-rhs),initial=0.))
    ub=float(max(0.,np.max(A@result.x-b,initial=0.)))
    bound=float(max([0.]+[lo-v for v,(lo,hi) in zip(result.x,all_bounds) if lo is not None]+[v-hi for v,(lo,hi) in zip(result.x,all_bounds) if hi is not None]))
    accepted=max(eq,ub,bound)<=1e-7
    diagnostic=master_dual(cost,A,b,all_bounds,result,nx)
    if accepted and diagnostic['lower_bound_eur']>result.fun+1e-7:raise ValueError('Master dual exceeds master primal')
    proposal=result.x[:nx].copy() if accepted else None
    repaired=False
    if not accepted and warm is not None:
        # Repair inventory only. Do not change the unrestricted objective or dual.
        warm=validate_warm(warm,bounds,sparse.csr_matrix(equality),rhs)
        if np.max(sparse.csr_matrix(inequality)@warm-limit,initial=0.)>1e-7:
            raise ValueError('Warm proposal anchor violates reachability')
        candidate=bounded_proposal(result.x[:nx],bounds,1e-7)
        candidate=feasible_proposal(candidate,warm,inequality,limit,1e-7)
        proposal=validate_warm(candidate,bounds,sparse.csr_matrix(equality),rhs)
        if np.max(sparse.csr_matrix(inequality)@proposal-limit,initial=0.)>1e-7:
            raise ValueError('Repaired inventory proposal violates reachability')
        repaired=True
    return dict(**diagnostic,master_objective_eur=float(result.fun),proposal_accepted=proposal is not None,
                proposal_repaired=repaired,proposal_mwh=None if proposal is None else proposal.tolist(),
                proposal_equality_residual=None if proposal is None else float(np.max(abs(sparse.csr_matrix(equality)@proposal-rhs),initial=0.)),
                proposal_reachability_violation=None if proposal is None else float(max(0.,np.max(sparse.csr_matrix(inequality)@proposal-limit,initial=0.))),
                max_equality_residual=eq,max_inequality_violation=ub,max_bound_violation=bound)


def audit(folder):
    master=json.loads((folder/'master-workspace.json').read_text())
    witness_path=folder/'warm-audit'/'independent-witness-audit.json'
    verified=json.loads(witness_path.read_text())
    floor_path=folder/'objective-floors.json'; floors=json.loads(floor_path.read_text())
    if verified['input_sha256']!=master['input_sha256'] or floors['input_sha256']!=master['input_sha256']:
        raise ValueError('Source fingerprints differ')
    for name,value in master['workspace_sha256'].items():
        if digest(folder/name)!=value:raise ValueError('Workspace changed')
    if verified['warm_state_sha256']!=master['workspace_sha256']['master-state.npz']:
        raise ValueError('Witness inventory fingerprint differs')
    for name,value in floors['dependencies'].items():
        if digest(Path(__file__).with_name(name))!=value:raise ValueError('Floor implementation changed')
    if [r['month'] for r in floors['rows']]!=list(range(1,13)):raise ValueError('Incomplete floors')
    for row in floors['rows']:
        if digest(folder/f"{row['month']:02d}.npz")!=row['block_sha256']:raise ValueError('Floor source changed')
    cuts=[]
    for row in verified['rows']:
        path=folder/'warm-audit'/f"{row['month']:02d}.json"
        receipt=json.loads(path.read_text())
        if digest(path)!=row['receipt_sha256'] or digest(path.parent/receipt['witness_file'])!=row['witness_sha256']:
            raise ValueError('Verified witness changed')
        cuts.append((row['month']-1,receipt['gradient_eur_per_mwh'],receipt['dual_intercept_eur']))
    with np.load(folder/'master-state.npz',allow_pickle=False) as state:
        result=solve_cut_master(state['bounds'],sparse.load_npz(folder/'master-equality.npz'),state['rhs'],
            sparse.load_npz(folder/'master-inequality.npz'),state['limit'],
            [r['objective_floor_eur'] for r in floors['rows']],cuts,warm=state['warm_state_mwh'])
    upper=verified['annual_feasible_cost_eur']
    if upper is not None and result['lower_bound_eur']>upper+1e-7:raise ValueError('Annual bound inconsistency')
    result.update(input_sha256=master['input_sha256'],verified_cut_months=len(cuts),
        annual_feasible_cost_eur=upper,annual_gap_eur=None if upper is None else upper-result['lower_bound_eur'],
        witness_audit_sha256=digest(witness_path),floor_audit_sha256=digest(floor_path),
        tool_sha256=digest(Path(__file__)),dependencies={name:digest(Path(__file__).with_name(name)) for name in ['storage_coordinator.py','storage_master_dual.py']},
        scope='Initial cut relaxation only; proposal requires monthly feasibility solves. Floating-point bound, not interval certification or convergence.')
    save(folder/'initial-cut-master.json',result)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--folder',type=Path,required=True)
    result=audit(parser.parse_args().folder)
    print(f"Initial cut master: {result['verified_cut_months']} verified cuts; lower bound €{result['lower_bound_eur']:.6f}; annual feasible cost {result['annual_feasible_cost_eur']}")
