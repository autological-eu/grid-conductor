"""Replay saved monthly primal/dual witnesses without re-running dispatch.

A verified prefix is not an annual solution. Annual feasibility additionally
requires twelve matching witnesses, complete chronology and cyclic closure.
No annual optimum or empirical validation is inferred from these checks.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from scipy import sparse
from scipy.optimize import OptimizeResult
from monthly_dispatch import digest, save
from disk_storage_blocks import load_block
from check_storage_dual_bounds import objective_support
from annual_inventory_workspace import validate_warm

NATIVE_DEPENDENCIES = ('native_storage_solver.py', 'sparse_primal_correction.py', 'check_storage_dual_bounds.py')


def replay(block, state, arrays, receipt):
    sizes = {'primal':len(block.cost), 'equality_duals':block.equality.shape[0],
             'inequality_duals':0 if block.inequality is None else block.inequality.shape[0],
             'lower_marginals':len(block.cost), 'upper_marginals':len(block.cost)}
    for name, size in sizes.items():
        if arrays[name].shape != (size,) or not np.isfinite(arrays[name]).all():
            raise ValueError(f'Invalid witness array: {name}')
    x = arrays['primal']
    eq = float(np.max(abs(block.equality @ x + block.coupling @ state - block.rhs), initial=0.))
    ub = 0. if block.inequality is None else float(max(0., np.max(block.inequality @ x +
         (0 if block.inequality_coupling is None else block.inequality_coupling @ state) - block.limit, initial=0.)))
    lo = np.array([-np.inf if value is None else value for value, high in block.bounds])
    hi = np.array([np.inf if value is None else value for low, value in block.bounds])
    bound = float(max(0., np.max(lo-x, initial=0.), np.max(x-hi, initial=0.)))
    if max(eq, ub, bound) > 1e-7:
        raise ValueError('Saved primal fails original-unit feasibility gates')
    cost = math.fsum(float(c)*float(v) for c,v in zip(block.cost,x))
    if cost != receipt['cost_eur']:
        raise ValueError('Saved primal cost differs from receipt')
    result = OptimizeResult(x=x, fun=cost,
        eqlin=OptimizeResult(marginals=arrays['equality_duals']),
        ineqlin=OptimizeResult(marginals=arrays['inequality_duals']),
        lower=OptimizeResult(marginals=arrays['lower_marginals']),
        upper=OptimizeResult(marginals=arrays['upper_marginals']))
    gradient, intercept = objective_support(block, state, result)
    lower = float(intercept + gradient @ state)
    if not np.isfinite(lower) or not np.isfinite(gradient).all() or lower > cost + 1e-7:
        raise ValueError('Replayed dual support exceeds feasible primal cost')
    if not np.array_equal(gradient, np.asarray(receipt['gradient_eur_per_mwh'])):
        raise ValueError('Saved duals do not reproduce the cut gradient')
    if lower != receipt['dual_support_eur'] or intercept != receipt['dual_intercept_eur']:
        raise ValueError('Saved duals do not reproduce the support value/intercept')
    return dict(cost_eur=cost, dual_support_eur=lower, local_gap_eur=cost-lower,
                max_equality_residual=eq, max_inequality_violation=ub, max_bound_violation=bound)


def audit(folder, source, through):
    master = json.loads((folder/'master-workspace.json').read_text())
    if digest(source) != master['input_sha256']:
        raise ValueError('Prepared network differs from workspace source')
    for name,value in master['workspace_sha256'].items():
        if digest(folder/name) != value:
            raise ValueError('Master workspace fingerprint mismatch')
    with np.load(folder/'master-state.npz', allow_pickle=False) as data:
        state = validate_warm(data['warm_state_mwh'], data['bounds'],
                              sparse.load_npz(folder/'master-equality.npz'), data['rhs'])
        reachability = sparse.load_npz(folder/'master-inequality.npz') @ state - data['limit']
        if np.max(reachability,initial=0.) > 1e-7:
            raise ValueError('Warm state fails reachability')
    rows=[]
    for month in range(1,through+1):
        path = folder/'warm-audit'/f'{month:02d}.json'
        if not path.exists():
            break
        receipt=json.loads(path.read_text())
        metadata=json.loads((folder/f'{month:02d}.json').read_text())
        block_path=folder/f'{month:02d}.npz'
        expected = dict(input_sha256=master['input_sha256'], block_sha256=digest(block_path),
                        warm_state_sha256=master['workspace_sha256']['master-state.npz'])
        if any(receipt.get(name)!=value for name,value in expected.items()) or metadata['block_sha256']!=expected['block_sha256'] or metadata['input_sha256']!=expected['input_sha256']:
            raise ValueError('Monthly witness/source fingerprint mismatch')
        if receipt.get('month')!=month or metadata['month']!=month:
            raise ValueError('Monthly identity mismatch')
        if receipt.get('audit_tool_sha256')!=digest(Path(__file__).with_name('audit_annual_warm_state.py')):
            raise ValueError('Witness producer fingerprint mismatch')
        if set(receipt.get('dependencies',{}))!=set(NATIVE_DEPENDENCIES):
            raise ValueError('Missing native dependency fingerprints')
        for name in NATIVE_DEPENDENCIES:
            if receipt['dependencies'][name]!=digest(Path(__file__).with_name(name)):
                raise ValueError('Native witness dependency fingerprint mismatch')
        if receipt.get('witness_file')!=f'{month:02d}-witness.npz':
            raise ValueError('Unexpected witness filename')
        witness=path.parent/receipt['witness_file']
        if digest(witness)!=receipt['witness_sha256']:
            raise ValueError('Monthly witness content hash mismatch')
        block=load_block(block_path)
        with np.load(witness,allow_pickle=False) as saved:
            arrays={name:saved[name] for name in ['primal','equality_duals','inequality_duals','lower_marginals','upper_marginals']}
        checked=replay(block,state,arrays,receipt)
        rows.append(dict(month=month,receipt_sha256=digest(path),witness_sha256=digest(witness),**checked))
        del block,arrays
    annual = len(rows)==12
    if annual:
        # Also audit source preparation provenance and all 8,760 chronological hours.
        from audit_annual_coordination_preparation import audit as audit_preparation
        audit_preparation(argparse.Namespace(input=source,output=folder,year=2025))
    result=dict(status='annual_fixed_inventory_feasible' if annual else 'verified_monthly_prefix_only',
                verified_months=len(rows),rows=rows,input_sha256=master['input_sha256'],
                warm_state_sha256=master['workspace_sha256']['master-state.npz'],
                annual_feasible_cost_eur=math.fsum(row['cost_eur'] for row in rows) if annual else None,
                scope='Fixed warm inventories only; no annual optimisation gap, optimum, native/fast parity or empirical validation')
    save(folder/'warm-audit'/'independent-witness-audit.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,required=True)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--through',type=int,default=12)
    args=parser.parse_args()
    if not 1<=args.through<=12:parser.error('Invalid month count')
    result=audit(args.folder,args.input,args.through)
    print(f"Independent witness audit: {result['verified_months']}/12 months, {result['status']}")
