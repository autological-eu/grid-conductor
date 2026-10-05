"""Independent source-matched economic block witness replay; no solver call."""
import argparse,json
from pathlib import Path
import numpy as np
from monthly_dispatch import digest,save
from disk_storage_blocks import load_block
from audit_monthly_dispatch_witnesses import replay
from submonthly_objective_donor import PRODUCER_DEPENDENCIES


def audit(args):
    output=args.folder/'independent-replay.json'
    if output.exists():raise ValueError('Preserve previous economic replay')
    path=args.folder/'verified.json';receipt=json.loads(path.read_text())
    domain_path=args.workspace/'master-workspace.json';domain=json.loads(domain_path.read_text())
    tools=Path(__file__).parent;index=receipt['index'];source=digest(args.input)
    if (receipt['status']!='conditional_submonthly_candidate_verified'
            or receipt['input_sha256']!=source or domain['input_sha256']!=source
            or receipt['inventory_workspace_sha256']!=digest(domain_path)
            or receipt['producer_sha256']!=digest(tools/'audit_submonthly_candidate.py')
            or not 0<=index<len(domain['blocks'])
            or receipt['block_sha256']!=domain['block_sha256'][index]):
        raise ValueError('Source-matched economic candidate required')
    if set(receipt['dependencies'])!=PRODUCER_DEPENDENCIES:
        raise ValueError('Complete economic producer fingerprints required')
    for name,value in receipt['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Economic candidate calculation changed')
    block_path=args.calendar/f'{index:02d}'/'block.npz'
    witness=args.folder/'witness.npz';state_path=args.folder/'boundary-state.npz'
    if (digest(block_path)!=receipt['block_sha256'] or digest(witness)!=receipt['witness_sha256']
            or digest(state_path)!=receipt['boundary_state_sha256']):
        raise ValueError('Economic candidate witness/source changed')
    with np.load(state_path,allow_pickle=False) as data:state=data['inventories_mwh'].copy()
    if state.shape!=(len(domain['storage_ids'])*(len(domain['blocks'])+1),) or not np.isfinite(state).all():
        raise ValueError('Explicit finite full-year inventory layout required')
    with np.load(witness,allow_pickle=False) as data:arrays={name:data[name].copy() for name in data.files}
    values=replay(load_block(block_path),state,arrays,receipt)
    result=dict(status='independently_replayed_submonthly_economic_witness',index=index,
        input_sha256=source,inventory_workspace_sha256=digest(domain_path),master_sha256=receipt['master_sha256'],
        producer_receipt_sha256=digest(path),witness_sha256=digest(witness),boundary_state_sha256=digest(state_path),
        block_sha256=receipt['block_sha256'],gradient_eur_per_mwh=receipt['gradient_eur_per_mwh'],
        dual_intercept_eur=receipt['dual_intercept_eur'],tool_sha256=digest(Path(__file__)),
        dependencies={name:digest(tools/name) for name in ['audit_monthly_dispatch_witnesses.py','check_storage_dual_bounds.py','disk_storage_blocks.py','submonthly_objective_donor.py']},
        **values,scope='One conditional original-coefficient economic block only; full annual linkage, convergence and empirical/investment validation remain separate.')
    save(output,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','workspace','calendar','folder']:parser.add_argument('--'+name,type=Path,required=True)
    result=audit(parser.parse_args());print(f"Independently replayed conditional economic block {result['index']}; no annual result inferred.")
