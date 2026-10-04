"""Replay an elastic primal/dual witness before adopting its numerical feasibility cut."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import OptimizeResult
from annual_inventory_phase_one import elastic_block,feasibility_support
from audit_annual_warm_state import receipts
from audit_monthly_dispatch_witnesses import replay
from disk_storage_blocks import load_block
from monthly_dispatch import digest,save


def audit(folder,anchor,month,mode):
    output=folder/('phase-one-boundary' if mode=='boundary' else 'phase-one')
    path=output/f'{month:02d}-witness.json';receipt=json.loads(path.read_text())
    signature=receipts(argparse.Namespace(folder=folder),month)
    if receipt['month']!=month or receipt['mode']!=mode or any(receipt.get(k)!=v for k,v in signature.items()):
        raise ValueError('Feasibility witness identity/source mismatch')
    if receipt['tool_sha256']!=digest(Path(__file__).with_name('annual_inventory_phase_one.py')):
        raise ValueError('Elastic witness producer changed')
    expected={'native_storage_solver.py','check_storage_dual_bounds.py','disk_storage_blocks.py'}
    if set(receipt['dependencies'])!=expected:raise ValueError('Incomplete feasibility witness dependencies')
    for name,value in receipt['dependencies'].items():
        if digest(Path(__file__).with_name(name))!=value:raise ValueError('Feasibility witness dependency changed')
    anchor_path=anchor/'warm-audit'/'independent-witness-audit.json'
    accepted=json.loads(anchor_path.read_text())
    if digest(anchor_path)!=receipt['anchor_audit_sha256'] or accepted['status']!='annual_fixed_inventory_feasible' or accepted['input_sha256']!=signature['input_sha256'] or accepted['warm_state_sha256']!=digest(anchor/'master-state.npz'):
        raise ValueError('Verified feasible anchor changed')
    anchor_row=accepted['rows'][month-1];anchor_receipt_path=anchor/'warm-audit'/f'{month:02d}.json'
    anchor_receipt=json.loads(anchor_receipt_path.read_text())
    if digest(anchor_receipt_path)!=anchor_row['receipt_sha256'] or digest(anchor_receipt_path.parent/anchor_receipt['witness_file'])!=anchor_row['witness_sha256']:
        raise ValueError('Feasible anchor witness changed')
    witness=output/f'{month:02d}-witness.npz'
    if digest(witness)!=receipt['witness_sha256']:raise ValueError('Elastic witness changed')
    with np.load(folder/'master-state.npz',allow_pickle=False) as data:state=data['warm_state_mwh'].copy()
    with np.load(anchor/'master-state.npz',allow_pickle=False) as data:anchor_state=data['warm_state_mwh'].copy()
    block=elastic_block(load_block(folder/f'{month:02d}.npz'),boundary_only=mode=='boundary')
    with np.load(witness,allow_pickle=False) as data:
        arrays={name:data[name].copy() for name in ['primal','equality_duals','inequality_duals','lower_marginals','upper_marginals']}
    checked=replay(block,state,arrays,dict(cost_eur=receipt['phase_one_cost'],gradient_eur_per_mwh=receipt['gradient'],dual_support_eur=receipt['dual_support'],dual_intercept_eur=receipt['intercept']))
    result=OptimizeResult(x=arrays['primal'],eqlin=OptimizeResult(marginals=arrays['equality_duals']),ineqlin=OptimizeResult(marginals=arrays['inequality_duals']),lower=OptimizeResult(marginals=arrays['lower_marginals']),upper=OptimizeResult(marginals=arrays['upper_marginals']))
    support=feasibility_support(block,state,result,anchor_state)
    if support['feasibility_limit']!=receipt['feasibility_limit'] or support['anchor_support']!=receipt['anchor_support']:
        raise ValueError('Feasibility cut/anchor replay mismatch')
    report=dict(status='independently_replayed_numerical_feasibility_cut',month=month,mode=mode,
        input_sha256=signature['input_sha256'],block_sha256=signature['block_sha256'],
        warm_state_sha256=signature['warm_state_sha256'],producer_receipt_sha256=digest(path),
        witness_sha256=digest(witness),anchor_audit_sha256=digest(anchor_path),
        audit_tool_sha256=digest(Path(__file__)),**support,primal_checks=checked)
    save(output/f'{month:02d}-verified-cut.json',report);return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--folder',type=Path,required=True);parser.add_argument('--anchor',type=Path,required=True);parser.add_argument('--month',type=int,required=True);parser.add_argument('--mode',choices=['all','boundary'],required=True)
    args=parser.parse_args()
    if not 1<=args.month<=12:parser.error('Invalid month')
    report=audit(args.folder,args.anchor,args.month,args.mode)
    print('Positive numerical feasibility cut independently replayed; no annual convergence claim.')
