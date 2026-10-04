"""Prepare an isolated fixed-inventory candidate; no dispatch or optimum claim."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy import sparse
from annual_inventory_workspace import validate_warm
from monthly_dispatch import digest, save


def checked_candidate(candidate,bounds,equality,rhs,inequality,limit):
    state=validate_warm(candidate,bounds,equality,rhs)
    if np.max(inequality@state-limit,initial=0.)>1e-7:
        raise ValueError('Candidate violates original reachability tolerance')
    return state


def prepare(parent,output):
    if output.exists():raise ValueError('Candidate workspace already exists; never overwrite evidence')
    master=json.loads((parent/'master-workspace.json').read_text())
    audit_path=parent/'warm-audit'/'independent-witness-audit.json'
    audit=json.loads(audit_path.read_text())
    proposal_path=parent/'initial-cut-master.json';proposal=json.loads(proposal_path.read_text())
    if audit['status']!='annual_fixed_inventory_feasible' or audit['verified_months']!=12 or audit['annual_feasible_cost_eur'] is None:
        raise ValueError('A fully verified annual feasible incumbent is required')
    if proposal['witness_audit_sha256']!=digest(audit_path) or proposal['input_sha256']!=master['input_sha256'] or audit['input_sha256']!=master['input_sha256']:
        raise ValueError('Proposal/incumbent source mismatch; rebuild cut master')
    if proposal['tool_sha256']!=digest(Path(__file__).with_name('annual_inventory_master.py')):
        raise ValueError('Proposal implementation changed; rebuild cut master')
    for name,value in proposal['dependencies'].items():
        if digest(Path(__file__).with_name(name))!=value:raise ValueError('Master dependency changed')
    if not proposal['proposal_accepted'] or proposal['proposal_mwh'] is None:
        raise ValueError('No accepted master inventory proposal')
    for name,value in master['workspace_sha256'].items():
        if digest(parent/name)!=value:raise ValueError('Parent workspace changed')
    for row in audit['rows']:
        receipt_path=parent/'warm-audit'/f"{row['month']:02d}.json"
        receipt=json.loads(receipt_path.read_text())
        if digest(receipt_path)!=row['receipt_sha256'] or digest(receipt_path.parent/receipt['witness_file'])!=row['witness_sha256']:
            raise ValueError('Incumbent witness changed')
    with np.load(parent/'master-state.npz',allow_pickle=False) as data:
        arrays={name:data[name].copy() for name in data.files}
    arrays['warm_state_mwh']=checked_candidate(proposal['proposal_mwh'],arrays['bounds'],
        sparse.load_npz(parent/'master-equality.npz'),arrays['rhs'],
        sparse.load_npz(parent/'master-inequality.npz'),arrays['limit'])
    # Validate every source block before creating files. Symlinks avoid large copies.
    names=['master-equality.npz','master-inequality.npz','objective-floors.json']
    for month in range(1,13):
        metadata=json.loads((parent/f'{month:02d}.json').read_text())
        if metadata['input_sha256']!=master['input_sha256'] or digest(parent/f'{month:02d}.npz')!=metadata['block_sha256']:
            raise ValueError('Candidate block/source mismatch')
        names.extend([f'{month:02d}.npz',f'{month:02d}.json'])
    output.mkdir(parents=True)
    for name in names:(output/name).symlink_to((parent/name).resolve())
    with (output/'master-state.npz').open('wb') as stream:np.savez_compressed(stream,**arrays)
    child=dict(master);child['workspace_sha256']=dict(master['workspace_sha256'])
    child['workspace_sha256']['master-state.npz']=digest(output/'master-state.npz')
    child.update(candidate_parent_workspace_sha256=digest(parent/'master-workspace.json'),
        candidate_proposal_sha256=digest(proposal_path),candidate_incumbent_audit_sha256=digest(audit_path),
        candidate_preparation_sha256=digest(Path(__file__)),
        scope='Master-feasible inventory candidate only; requires all twelve monthly dispatch witnesses. Not an annual optimum.')
    save(output/'master-workspace.json',child)
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();prepare(args.parent.resolve(),args.output.resolve())
    print('Isolated annual inventory candidate prepared; no dispatch result accepted.')
