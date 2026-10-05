"""Replay 59 restricted primals against one chronological annual inventory state.

This establishes a feasible upper bound only. No dual transfer, convergence,
solver parity, market validation or investment result is inferred.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from monthly_dispatch import digest,save
from prepare_submonthly_blocks import partitions
from prepare_submonthly_calendar import verify_block
from prepare_submonthly_warm_calendar import verify
from submonthly_inventory_mapping import boundary_positions,project_state
from annual_inventory_workspace import boundaries,validate_warm
from disk_storage_blocks import load_block


def merge_boundaries(pieces,count,storage_units,tolerance=1e-7):
    state=np.full((count+1,storage_units),np.nan)
    for positions,values in pieces:
        positions=np.asarray(positions)
        values=np.asarray(values,dtype=float)
        if positions.ndim!=1 or not np.issubdtype(positions.dtype,np.integer) or len(np.unique(positions))!=len(positions) or np.any(positions<0) or np.any(positions>count) or values.shape!=(len(positions),storage_units) or not np.isfinite(values).all():
            raise ValueError('Invalid restricted boundary piece')
        for position,row in zip(positions,values):
            if np.isfinite(state[position]).all():
                if np.max(abs(state[position]-row),initial=0.)>tolerance:
                    raise ValueError('Adjacent monthly inventories disagree')
            else:state[position]=row
    if not np.isfinite(state).all():raise ValueError('Missing chronological boundary inventories')
    return state


def primal_checks(block,state,x):
    x=np.asarray(x,dtype=float)
    if x.shape!=block.cost.shape or not np.isfinite(x).all():raise ValueError('Invalid restricted primal')
    eq=float(np.max(abs(block.equality@x+block.coupling@state-block.rhs),initial=0.))
    ub=float(max(0.,np.max(block.inequality@x+block.inequality_coupling@state-block.limit,initial=0.)))
    lo=np.array([-np.inf if a is None else a for a,b in block.bounds])
    hi=np.array([np.inf if b is None else b for a,b in block.bounds])
    bound=float(max(0.,np.max(lo-x,initial=0.),np.max(x-hi,initial=0.)))
    if not np.isfinite([eq,ub,bound]).all() or max(eq,ub,bound)>1e-7:
        raise ValueError('Restricted annual primal fails original-unit gates')
    return dict(cost_eur=math.fsum(float(c)*float(v) for c,v in zip(block.cost,x)),
                max_equality_residual=eq,max_inequality_violation=ub,max_bound_violation=bound)


def audit(args):
    tools=Path(__file__).parent;source_hash=digest(args.input)
    if args.output.exists():raise ValueError('Preserve existing annual audit evidence')
    monthly=json.loads((args.monthly/'master-workspace.json').read_text())
    manifest=json.loads((args.warm/'preparation-manifest.json').read_text())
    completed=json.loads((args.warm/'verified-months.json').read_text())
    calendar=json.loads((args.calendar/'verified-blocks.json').read_text())
    if any(d['input_sha256']!=source_hash for d in [monthly,manifest,completed,calendar]):
        raise ValueError('Annual source fingerprint mismatch')
    if manifest['monthly_master_sha256']!=digest(args.monthly/'master-workspace.json') or manifest['calendar_manifest_sha256']!=digest(args.calendar/'preparation-manifest.json') or manifest['calendar_verified_sha256']!=digest(args.calendar/'verified-blocks.json'):
        raise ValueError('Frozen workspace changed')
    for name,value in manifest['tools'].items():
        if digest(tools/name)!=value:raise ValueError('Frozen restriction tool changed')
    if [row['month'] for row in completed['rows']]!=list(range(1,13)):
        raise ValueError('All twelve chronological monthly receipts required')
    for name,value in monthly['workspace_sha256'].items():
        if digest(args.monthly/name)!=value:raise ValueError('Monthly master artifact changed')
    rows=partitions(2025,168);ns=len(calendar['storage_ids']);pieces=[];receipts=[]
    for row in completed['rows']:
        month=row['month'];folder=args.warm/f'{month:02d}'
        if digest(folder/'verified.json')!=row['receipt_sha256']:raise ValueError('Monthly restriction receipt changed')
        receipt=verify(folder,month,source_hash)
        if receipt['source_receipt_sha256']!=digest(args.monthly/'warm-audit'/f'{month:02d}.json') or receipt['source_witness_sha256']!=digest(args.monthly/'warm-audit'/f'{month:02d}-witness.npz'):
            raise ValueError('Original monthly witness changed')
        selected=[r for r in rows if r['month']==month]
        if [r['index'] for r in receipt['rows']]!=[r['index'] for r in selected]:
            raise ValueError('Restricted month does not cover its exact partition')
        with np.load(folder/'boundary-state.npz',allow_pickle=False) as saved:
            positions=saved['positions'].copy();values=saved['inventories_mwh'].copy()
        if not np.array_equal(positions,np.arange(selected[0]['index'],selected[-1]['index']+2)):
            raise ValueError('Restricted inventory boundary positions differ')
        pieces.append((positions,values));receipts.append(receipt)
    state=merge_boundaries(pieces,len(rows),ns)
    with np.load(args.monthly/'master-state.npz',allow_pickle=False) as data:original_state=data['warm_state_mwh'].copy()
    if np.max(abs(project_state(state.ravel(),ns,rows)-original_state),initial=0.)>1e-7:
        raise ValueError('Projected annual inventories differ from verified monthly anchor')
    # Canonical month boundaries retain the exact source anchor; all blocks are
    # replayed after this roundoff-only canonicalisation, never assumed feasible.
    state[boundary_positions(rows)]=original_state.reshape(13,ns)
    metadata=json.loads((args.monthly/'01.json').read_text())
    if metadata['storage_ids']!=calendar['storage_ids']:raise ValueError('Storage ordering differs')
    bounds,equality,rhs=boundaries(metadata['storage_capacity_mwh'],metadata['source_initial_inventory_mwh'],metadata['source_cyclic'],months=len(rows))
    state=validate_warm(state.ravel(),bounds,equality,rhs);checked=[]
    if [r['index'] for r in calendar['rows']]!=list(range(len(rows))):raise ValueError('Incomplete coefficient calendar')
    for row in rows:
        index=row['index'];folder=args.calendar/f'{index:02d}';receipt=receipts[row['month']-1]
        target=next(item for item in receipt['rows'] if item['index']==index)
        proof=calendar['rows'][index];meta=verify_block(folder,row,source_hash,len(rows))
        if meta['storage_ids']!=calendar['storage_ids'] or proof['receipt_sha256']!=digest(folder/'block.json') or proof['block_sha256']!=meta['block_sha256'] or target['block_sha256']!=meta['block_sha256']:
            raise ValueError('Prepared annual block provenance differs')
        path=args.warm/f"{row['month']:02d}"/f'{index:02d}-primal.npz'
        if digest(path)!=target['primal_sha256']:raise ValueError('Restricted primal changed')
        block=load_block(folder/'block.npz')
        with np.load(path,allow_pickle=False) as data:x=data['primal'].copy()
        values=primal_checks(block,state,x)
        if values['cost_eur']!=target['cost_eur']:raise ValueError('Restricted cost does not reproduce')
        checked.append(dict(index=index,month=row['month'],hours=row['hours'],block_sha256=meta['block_sha256'],primal_sha256=target['primal_sha256'],**values))
        del block,x
    total=math.fsum(row['cost_eur'] for row in checked)
    source_total=math.fsum(json.loads((args.monthly/'warm-audit'/f'{month:02d}.json').read_text())['cost_eur'] for month in range(1,13))
    if abs(total-source_total)>1e-4:raise ValueError('Annual restricted objective differs from verified source incumbent')
    args.output.mkdir(parents=True);np.savez_compressed(args.output/'annual-state.npz',inventories_mwh=state)
    result=dict(status='annual_restricted_primal_feasible',input_sha256=source_hash,hours=sum(r['hours'] for r in checked),
         blocks=len(checked),storage_units=ns,annual_feasible_cost_eur=total,source_cost_difference_eur=total-source_total,
         cyclic_closure_residual_mwh=float(np.max(abs(equality@state-rhs),initial=0.)),
         annual_state_sha256=digest(args.output/'annual-state.npz'),restriction_manifest_sha256=digest(args.warm/'preparation-manifest.json'),
         completed_months_sha256=digest(args.warm/'verified-months.json'),producer_sha256=digest(Path(__file__)),rows=checked,
         dependencies={name:digest(tools/name) for name in ['prepare_submonthly_warm_calendar.py','prepare_submonthly_calendar.py','submonthly_inventory_mapping.py','annual_inventory_workspace.py','disk_storage_blocks.py']},
         scope='Independently replayed annual feasible primal only; no new lower bound, annual convergence, native/fast parity, empirical or investment validation.')
    save(args.output/'verified.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','monthly','calendar','warm','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=audit(args)
    print(f"Annual restricted primal verified: {result['blocks']} blocks, {result['hours']} hours; feasible cost EUR {result['annual_feasible_cost_eur']:.6f}. No convergence claim.")
