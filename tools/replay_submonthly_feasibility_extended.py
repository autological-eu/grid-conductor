"""Independent replay for the versioned extended native Phase-I producer.

No implicit adoption by the frozen annual driver; no solver call.
"""
import argparse,json
from pathlib import Path
import numpy as np
from monthly_dispatch import digest,save
from disk_storage_blocks import load_block
from annual_inventory_phase_one import elastic_block
from audit_monthly_dispatch_witnesses import replay
from audit_submonthly_warm_calendar import primal_checks


def audit(args):
    target=args.folder/'independent-replay.json'
    if target.exists():raise ValueError('Preserve previous independent feasibility replay')
    path=args.folder/'verified.json';record=json.loads(path.read_text());tools=Path(__file__).parent
    source=digest(args.input);annual_path=args.annual/'verified.json';annual=json.loads(annual_path.read_text())
    if record['status']!='submonthly_feasibility_support_requires_replay' or record['input_sha256']!=source or annual['input_sha256']!=source or record['producer_sha256']!=digest(tools/'audit_submonthly_feasibility_extended.py') or record['anchor_audit_sha256']!=digest(annual_path):
        raise ValueError('Source-matched feasibility support and annual anchor required')
    for name,value in record['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Elastic support dependency changed')
    index=record['index'];row=next(r for r in annual['rows'] if r['index']==index)
    block_path=args.calendar/f'{index:02d}'/'block.npz';primal_path=args.warm/f"{row['month']:02d}"/f'{index:02d}-primal.npz'
    witness=args.folder/'witness.npz';state_path=args.folder/'boundary-state.npz'
    if digest(block_path)!=record['block_sha256'] or row['block_sha256']!=record['block_sha256'] or digest(primal_path)!=row['primal_sha256'] or digest(witness)!=record['witness_sha256'] or digest(state_path)!=record['boundary_state_sha256']:
        raise ValueError('Elastic witness/source/verified anchor changed')
    with np.load(witness,allow_pickle=False) as data:arrays={name:data[name].copy() for name in data.files}
    with np.load(state_path,allow_pickle=False) as data:state=data['inventories_mwh'].copy()
    with np.load(args.annual/'annual-state.npz',allow_pickle=False) as data:anchor=data['inventories_mwh'].copy()
    if annual['annual_state_sha256']!=digest(args.annual/'annual-state.npz'):raise ValueError('Annual anchor inventory changed')
    with np.load(primal_path,allow_pickle=False) as data:point=data['primal'].copy()
    block=load_block(block_path);primal_checks(block,anchor,point)
    checked=replay(elastic_block(block,boundary_only=True),state,arrays,record)
    g=np.asarray(record['gradient_eur_per_mwh']);intercept=record['dual_intercept_eur'];at_anchor=float(intercept+g@anchor)
    if checked['dual_support_eur']<=1e-7 or at_anchor>1e-7 or at_anchor!=record['anchor_support'] or not np.array_equal(g,np.asarray(record['gradient'])) or intercept!=record['intercept'] or record['feasibility_limit']!=1e-7-intercept:
        raise ValueError('Necessary positive support/anchor/feasibility limit does not reproduce')
    summary=dict(status='independently_replayed_submonthly_feasibility_cut',index=index,input_sha256=source,
         producer_receipt_sha256=digest(path),witness_sha256=digest(witness),anchor_audit_sha256=digest(annual_path),block_sha256=record['block_sha256'],
         dual_support=checked['dual_support_eur'],gradient=g.tolist(),intercept=intercept,feasibility_limit=record['feasibility_limit'],anchor_support=at_anchor,
         phase_one_point_objective=checked['cost_eur'],max_equality_residual=checked['max_equality_residual'],max_inequality_violation=checked['max_inequality_violation'],max_bound_violation=checked['max_bound_violation'],
         tool_sha256=digest(Path(__file__)),dependencies={name:digest(tools/name) for name in ['annual_inventory_phase_one.py','audit_monthly_dispatch_witnesses.py','check_storage_dual_bounds.py']},
         scope='Necessary floating-point boundary-elastic feasibility cut in inventory units, not euros, welfare or prices. Constructed phase primal is not an economic candidate witness.')
    save(target,summary);return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','calendar','warm','annual','folder']:parser.add_argument('--'+name,type=Path,required=True)
    result=audit(parser.parse_args());print(f"Replayed necessary feasibility cut for block {result['index']}, support {result['dual_support']:.6f} inventory units; not an economic cut.")
