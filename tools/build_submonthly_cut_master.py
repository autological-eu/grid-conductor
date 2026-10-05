"""Explicit adoption of monthly/grouped and replayed sub-block supports."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy import sparse
from monthly_dispatch import digest,save
from grouped_storage_master import solve
from prepare_submonthly_inventory_workspace import monthly_projection
from submonthly_inventory_mapping import month_blocks
from prepare_submonthly_dual_calendar import verify


def build(args):
    if args.output.exists():raise ValueError('Preserve existing master checkpoint')
    tools=Path(__file__).parent;domain=json.loads((args.workspace/'master-workspace.json').read_text())
    source=digest(args.input)
    if domain['status']!='submonthly_inventory_workspace_prepared' or domain['input_sha256']!=source or domain['producer_sha256']!=digest(tools/'prepare_submonthly_inventory_workspace.py'):
        raise ValueError('Prepared source-matched submonthly domain required')
    for name,value in domain['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Inventory domain producer dependency changed')
    for name,value in domain['workspace_sha256'].items():
        if digest(args.workspace/name)!=value:raise ValueError('Inventory domain artifact changed')
    rows=domain['blocks'];ns=len(domain['storage_ids']);P=monthly_projection(ns,rows)
    parent=json.loads((args.monthly/'master-workspace.json').read_text())
    parent_audit_path=args.monthly/'warm-audit'/'independent-witness-audit.json'
    parent_audit=json.loads(parent_audit_path.read_text())
    if parent['input_sha256']!=source or parent_audit['input_sha256']!=source or parent_audit['status']!='annual_fixed_inventory_feasible' or parent_audit['verified_months']!=12 or domain['monthly_workspace_sha256']!=digest(args.monthly/'master-workspace.json'):
        raise ValueError('Verified monthly donor source differs')
    cuts=[];evidence=[]
    for row in parent_audit['rows']:
        month=row['month'];path=args.monthly/'warm-audit'/f'{month:02d}.json';receipt=json.loads(path.read_text())
        block=json.loads((args.monthly/f'{month:02d}.json').read_text())
        if digest(path)!=row['receipt_sha256'] or digest(path.parent/receipt['witness_file'])!=row['witness_sha256'] or digest(args.monthly/f'{month:02d}.npz')!=receipt['block_sha256'] or receipt['block_sha256']!=block['block_sha256'] or receipt['input_sha256']!=source:
            raise ValueError('Monthly objective donor changed')
        for name,value in receipt['dependencies'].items():
            if digest(tools/name)!=value:raise ValueError('Monthly donor dependency changed')
        g=np.asarray(receipt['gradient_eur_per_mwh'],dtype=float)
        if g.shape!=(13*ns,):raise ValueError('Monthly objective gradient layout differs')
        cuts.append((month_blocks(month,rows),np.asarray(P.T@g).ravel(),receipt['dual_intercept_eur']))
    adopted=[]
    for month in range(1,13):
        folder=args.support/f'{month:02d}'
        if not (folder/'independent-replay.json').exists():continue
        receipt=verify(folder,month,source)
        if receipt['annual_primal_audit_sha256']!=domain['annual_primal_audit_sha256']:
            raise ValueError('Support anchor differs from inventory domain')
        for item in receipt['rows']:
            index=item['index']
            if item['block_sha256']!=domain['block_sha256'][index] or item['block_sha256']!=digest(args.calendar/f'{index:02d}'/'block.npz'):
                raise ValueError('Sub-block support source differs')
            cuts.append(([index],item['gradient_eur_per_mwh'],item['dual_intercept_eur']))
        adopted.append(month);evidence.append(dict(month=month,receipt_sha256=digest(folder/'verified.json'),replay_sha256=digest(folder/'independent-replay.json')))
    with np.load(args.workspace/'master-state.npz',allow_pickle=False) as data:
        state={name:data[name].copy() for name in data.files}
    U=sparse.load_npz(args.workspace/'master-inequality.npz');limit=state['limit']
    feasibility=[]
    for path in args.feasibility:
        cut=json.loads(path.read_text());month=cut['month'];producer=path.parent/f'{month:02d}-witness.json';receipt=json.loads(producer.read_text())
        if cut['status']!='independently_replayed_numerical_feasibility_cut' or cut['input_sha256']!=source or cut['audit_tool_sha256']!=digest(tools/'audit_annual_feasibility_cut.py') or cut['anchor_audit_sha256']!=digest(parent_audit_path) or cut['block_sha256']!=json.loads((args.monthly/f'{month:02d}.json').read_text())['block_sha256'] or cut['producer_receipt_sha256']!=digest(producer) or cut['witness_sha256']!=digest(path.parent/f'{month:02d}-witness.npz'):
            raise ValueError('Verified feasibility donor differs')
        kind='phase_one_dual_probe.py' if receipt.get('producer_kind')=='dual_probe' else 'annual_inventory_phase_one.py'
        if receipt['tool_sha256']!=digest(tools/kind) or any(digest(tools/name)!=value for name,value in receipt['dependencies'].items()):
            raise ValueError('Feasibility producer changed')
        g=np.asarray(cut['gradient'],dtype=float)
        if g.shape!=(13*ns,):raise ValueError('Feasibility gradient layout differs')
        U=sparse.vstack([U,sparse.csr_matrix((P.T@g).reshape(1,-1))],format='csr');limit=np.r_[limit,cut['feasibility_limit']]
        feasibility.append(dict(path=str(path),sha256=digest(path)))
    witness=args.output.with_suffix('.witness.npz') if args.include_equalities else None
    from submonthly_objective_donor import load as load_objective
    objective_evidence=[]
    for path in args.objective:
        cut,e=load_objective(path,domain);cuts.append(cut);objective_evidence.append(e)
    from submonthly_feasibility_donor import load as load_feasibility
    for path in args.submonthly_feasibility:
        g,b,e=load_feasibility(path,domain,state['warm_state_mwh'])
        U=sparse.vstack([U,sparse.csr_matrix(g.reshape(1,-1))],format='csr')
        limit=np.r_[limit,b];feasibility.append(e)
    result=solve([tuple(b) for b in state['bounds']],sparse.load_npz(args.workspace/'master-equality.npz'),state['rhs'],U,limit,
                 domain['objective_floors_eur'],cuts,state['warm_state_mwh'],include_equalities=args.include_equalities,witness_path=witness)
    upper=domain['annual_feasible_cost_eur']
    if result['lower_bound_eur']>upper+1e-7:raise ValueError('Master lower support exceeds verified annual incumbent')
    from submonthly_proposal import stabilise
    result['unrestricted_proposal_mwh']=result['proposal_mwh']
    result['proposal_mwh']=stabilise(result['proposal_mwh'],state['warm_state_mwh'],args.proposal_weight,
        [tuple(b) for b in state['bounds']],sparse.load_npz(args.workspace/'master-equality.npz'),state['rhs'],U,limit).tolist()
    result['proposal_weight']=args.proposal_weight
    result['proposal_scope']='Convex search point toward verified annual anchor; unrestricted relaxation and lower support are unchanged. Dispatch feasibility is not inferred.'
    result.update(input_sha256=source,annual_feasible_cost_eur=upper,annual_gap_eur=upper-result['lower_bound_eur'],
        adopted_support_months=adopted,support_evidence=evidence,monthly_objective_groups=12,objective_cuts=len(cuts),feasibility_evidence=feasibility,
        additional_objective_evidence=objective_evidence,
        inventory_workspace_sha256=digest(args.workspace/'master-workspace.json'),producer_sha256=digest(Path(__file__)),
        master_equalities_priced=args.include_equalities,
        master_witness_sha256=None if witness is None else digest(witness),
        dependencies={name:digest(tools/name) for name in ['grouped_storage_master.py','grouped_master_dual.py','prepare_submonthly_inventory_workspace.py','prepare_submonthly_dual_calendar.py','storage_master_dual.py','storage_coordinator.py','submonthly_feasibility_donor.py','submonthly_objective_donor.py','submonthly_proposal.py']},
        scope='Explicitly mapped floating-point cut relaxation only; an envelope-feasible proposal is not verified dispatch. Missing support months weaken the relaxation and do not shorten the calendar.')
    save(args.output,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','monthly','calendar','workspace','support','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--feasibility',type=Path,action='append',default=[])
    parser.add_argument('--submonthly-feasibility',type=Path,action='append',default=[],help='Independently replayed necessary cut in the explicit short-block inventory layout')
    parser.add_argument('--objective',type=Path,action='append',default=[],help='Independently replayed singleton economic objective support')
    parser.add_argument('--proposal-weight',type=float,default=1.,help='Convex search weight toward unrestricted proposal; does not restrict the master or alter its lower support')
    parser.add_argument('--include-equalities',action='store_true',help='Restore and price original-unit annual equality multipliers')
    result=build(parser.parse_args());print(f"Grouped master lower support EUR {result['lower_bound_eur']:.6f}; {result['objective_cuts']} cuts. Proposal still needs dispatch verification.")
