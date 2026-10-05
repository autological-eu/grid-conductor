"""Independently replay saved transferred supports, never re-run dispatch."""
import argparse,json
from pathlib import Path
import numpy as np
from monthly_dispatch import digest,save
from disk_storage_blocks import load_block
from audit_monthly_dispatch_witnesses import replay
from prepare_submonthly_blocks import partitions


def audit(args):
    target=args.support/'independent-replay.json'
    if target.exists():raise ValueError('Preserve existing independent replay')
    producer=args.support/'verified.json';record=json.loads(producer.read_text())
    tools=Path(__file__).parent;source=digest(args.input)
    annual_path=args.annual/'verified.json';annual=json.loads(annual_path.read_text())
    if record['status']!='transferred_dual_supports_checked' or record['input_sha256']!=source or annual['input_sha256']!=source or record['producer_sha256']!=digest(tools/'audit_submonthly_dual_support.py') or record['annual_primal_audit_sha256']!=digest(annual_path):
        raise ValueError('Source-matched transferred support and annual primal required')
    month=record['month']
    if record['parent_receipt_sha256']!=digest(args.monthly/'warm-audit'/f'{month:02d}.json'):
        raise ValueError('Source parent changed')
    for name,value in record['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Transfer dependency changed')
    if annual['annual_state_sha256']!=digest(args.annual/'annual-state.npz'):
        raise ValueError('Global inventory state changed')
    if annual['producer_sha256']!=digest(tools/'audit_submonthly_warm_calendar.py'):
        raise ValueError('Annual primal audit producer changed')
    selected=[r['index'] for r in partitions(2025,168) if r['month']==month]
    if [r['index'] for r in record['rows']]!=selected:raise ValueError('Exact chronological support partition required')
    with np.load(args.annual/'annual-state.npz',allow_pickle=False) as data:state=data['inventories_mwh'].copy()
    checked=[]
    for row in record['rows']:
        index=row['index'];parent=next(r for r in annual['rows'] if r['index']==index)
        block_path=args.calendar/f'{index:02d}'/'block.npz'
        primal_path=args.warm/f'{month:02d}'/f'{index:02d}-primal.npz';dual_path=args.support/f'{index:02d}-dual.npz'
        if digest(block_path)!=row['block_sha256'] or digest(primal_path)!=row['primal_sha256'] or digest(dual_path)!=row['dual_sha256'] or parent['primal_sha256']!=row['primal_sha256'] or parent['block_sha256']!=row['block_sha256']:
            raise ValueError('Primal/dual or coefficient content changed')
        with np.load(primal_path,allow_pickle=False) as data:arrays={'primal':data['primal'].copy()}
        with np.load(dual_path,allow_pickle=False) as data:arrays.update({name:data[name].copy() for name in data.files})
        block=load_block(block_path);values=replay(block,state,arrays,row)
        checked.append(dict(index=index,**values));del block,arrays
    result=dict(status='independently_replayed_transferred_supports',month=month,input_sha256=source,
          producer_receipt_sha256=digest(producer),annual_primal_audit_sha256=digest(annual_path),
          replay_tool_sha256=digest(Path(__file__)),
          dependencies={name:digest(tools/name) for name in ['audit_monthly_dispatch_witnesses.py','check_storage_dual_bounds.py','disk_storage_blocks.py']},
          rows=checked,scope='Floating-point finite-bound LP support replay only; no new native termination, annual gap improvement, empirical validation or investment claim.')
    save(target,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','monthly','calendar','warm','annual','support']:parser.add_argument('--'+name,type=Path,required=True)
    result=audit(parser.parse_args());print(f"Independently replayed {len(result['rows'])} transferred sub-block supports; no master adoption yet.")
