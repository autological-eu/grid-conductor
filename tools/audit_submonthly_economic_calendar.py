"""Replay a complete conditional economic calendar at one cyclic annual state."""
import argparse,json,math
from pathlib import Path
import numpy as np
from scipy import sparse
from monthly_dispatch import digest,save
from annual_inventory_workspace import validate_warm
from disk_storage_blocks import load_block
from audit_monthly_dispatch_witnesses import replay
from submonthly_objective_donor import load as donor


def audit(args):
    target=args.folder/'annual-replay.json'
    if target.exists():raise ValueError('Preserve previous economic annual replay')
    domain_path=args.workspace/'master-workspace.json';domain=json.loads(domain_path.read_text())
    if domain['input_sha256']!=digest(args.input):raise ValueError('Annual source differs')
    for name,value in domain['workspace_sha256'].items():
        if digest(args.workspace/name)!=value:raise ValueError('Annual inventory domain changed')
    # A prefix is never an annual calendar, even when every available solve passed.
    rows=domain['blocks'];position=0
    for index,row in enumerate(rows):
        if row['index']!=index or row['start_hour']!=position or row['end_hour_exclusive']-position!=row['hours']:
            raise ValueError('Annual chronology is incomplete or inconsistent')
        position=row['end_hour_exclusive']
    if domain['year']!=2025 or position!=8760 or len(rows)!=59:raise ValueError('Complete prepared 2025 calendar required')
    with np.load(args.workspace/'master-state.npz',allow_pickle=False) as saved:
        bounds=saved['bounds'].copy();rhs=saved['rhs'].copy();limits=saved['limit'].copy()
    state=None;master=None;checked=[]
    for row in rows:
        index=row['index'];folder=args.folder/f'{index:02d}'
        cut_path=folder/'independent-replay.json';donor(cut_path,domain)
        cut=json.loads(cut_path.read_text());receipt=json.loads((folder/'verified.json').read_text())
        with np.load(folder/'boundary-state.npz',allow_pickle=False) as saved:current=saved['inventories_mwh'].copy()
        if state is None:
            state=validate_warm(current,bounds,sparse.load_npz(args.workspace/'master-equality.npz'),rhs)
            if np.max(sparse.load_npz(args.workspace/'master-inequality.npz')@state-limits,initial=0.)>1e-7:
                raise ValueError('Annual state fails necessary envelopes')
            master=cut['master_sha256']
        if not np.array_equal(current,state) or cut['master_sha256']!=master:
            raise ValueError('Block witnesses do not share one exact linked annual state')
        block_path=args.calendar/f'{index:02d}'/'block.npz'
        if digest(block_path)!=domain['block_sha256'][index]:raise ValueError('Original coefficients changed')
        with np.load(folder/'witness.npz',allow_pickle=False) as saved:arrays={name:saved[name].copy() for name in saved.files}
        values=replay(load_block(block_path),state,arrays,receipt)
        if any(values[key]!=cut[key] for key in values):raise ValueError('Annual block replay differs from saved independent replay')
        checked.append(dict(index=index,hours=row['hours'],receipt_sha256=digest(folder/'verified.json'),
            replay_sha256=digest(cut_path),witness_sha256=cut['witness_sha256'],block_sha256=cut['block_sha256'],**values))
    state_path=args.folder/'annual-state.npz';np.savez_compressed(state_path,inventories_mwh=state)
    result=dict(status='independently_replayed_economic_annual_feasible',year=2025,hours=position,blocks=len(checked),
        input_sha256=domain['input_sha256'],inventory_workspace_sha256=digest(domain_path),master_sha256=master,
        annual_state_sha256=digest(state_path),annual_feasible_cost_eur=math.fsum(r['cost_eur'] for r in checked),rows=checked,
        cyclic_closure_residual_mwh=float(np.max(abs(sparse.load_npz(args.workspace/'master-equality.npz')@state-rhs),initial=0.)),
        producer_sha256=digest(Path(__file__)),dependencies={name:digest(Path(__file__).parent/name) for name in
            ['submonthly_objective_donor.py','audit_monthly_dispatch_witnesses.py','check_storage_dual_bounds.py','annual_inventory_workspace.py','disk_storage_blocks.py']},
        scope='Independently replayed linked annual feasible upper bound, not convergence, empirical validation, native/fast comparison or intervention benefits.')
    save(target,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','workspace','calendar','folder']:parser.add_argument('--'+name,type=Path,required=True)
    result=audit(parser.parse_args());print(f"Linked annual economic primal replayed, cost EUR {result['annual_feasible_cost_eur']:.6f}; no optimum inferred.")
