"""Split independently verified monthly primals; no new solve or optimum claim."""
import argparse,json,math,subprocess,sys,time
from pathlib import Path
import numpy as np
from monthly_dispatch import digest,save
from audit_annual_warm_state import guard_reason,terminate_worker


def worker(args):
    import pypsa
    from scipy import sparse
    from disk_storage_blocks import load_block
    from audit_monthly_dispatch_witnesses import replay
    from prepare_annual_coordination import validate_calendar
    from prepare_submonthly_calendar import verify_block
    from prepare_submonthly_blocks import partitions
    from submonthly_primal_mapping import restrict_primal,inventory_at
    from audit_submonthly_equivalence import difference
    tools=Path(__file__).parent
    master=json.loads((args.monthly/'master-workspace.json').read_text())
    if digest(args.input)!=master['input_sha256']:raise ValueError('Monthly source mismatch')
    for name,value in master['workspace_sha256'].items():
        if digest(args.monthly/name)!=value:raise ValueError('Monthly master changed')
    receipt_path=args.monthly/'warm-audit'/f'{args.month:02d}.json'
    receipt=json.loads(receipt_path.read_text())
    monthly_path=args.monthly/f'{args.month:02d}.npz'
    witness_path=receipt_path.parent/f'{args.month:02d}-witness.npz'
    expected=dict(input_sha256=master['input_sha256'],block_sha256=digest(monthly_path),
                  warm_state_sha256=master['workspace_sha256']['master-state.npz'],
                  witness_sha256=digest(witness_path),month=args.month,
                  audit_tool_sha256=digest(tools/'audit_annual_warm_state.py'))
    if any(receipt.get(k)!=v for k,v in expected.items()):raise ValueError('Monthly witness provenance mismatch')
    required={'native_storage_solver.py','sparse_primal_correction.py','check_storage_dual_bounds.py'}
    if set(receipt.get('dependencies',{}))!=required or any(digest(tools/k)!=v for k,v in receipt['dependencies'].items()):
        raise ValueError('Monthly witness dependencies changed')
    with np.load(args.monthly/'master-state.npz',allow_pickle=False) as data:monthly_state=data['warm_state_mwh'].copy()
    with np.load(witness_path,allow_pickle=False) as data:arrays={k:data[k].copy() for k in data.files}
    original=load_block(monthly_path);checked=replay(original,monthly_state,arrays,receipt)
    n=pypsa.Network(args.input);validate_calendar(n,2025)
    n.global_constraints.drop(n.global_constraints.index,inplace=True)
    rows=partitions(2025,168);selected=[r for r in rows if r['month']==args.month]
    times=n.snapshots[selected[0]['start_hour']:selected[-1]['end_hour_exclusive']]
    parent=n.copy();parent.set_snapshots(times)
    parent.storage_units['cyclic_state_of_charge']=False
    parent.storage_units['cyclic_state_of_charge_per_period']=False
    parent.storage_units['state_of_charge_initial']=0.
    model=parent.optimize.create_model(include_objective_constant=False);mat=model.matrices
    senses=np.asarray(mat.sense);ns=len(n.storage_units)
    if not np.all((senses=='=')|(senses=='<')|(senses=='>')):raise ValueError('Unknown native sense')
    # Prove that coordinates index exactly the saved monthly LP, not a merely
    # equally sized or similar model. Boundary rows are independently replayed.
    for left,right in [(mat.A.tocsr()[senses=='='],original.equality[:-ns]),
                       (sparse.vstack([mat.A.tocsr()[senses=='<'],-mat.A.tocsr()[senses=='>']]),original.inequality)]:
        if difference(left,right)!=0.:raise ValueError('Reconstructed monthly matrix differs')
    for left,right in [(mat.c,original.cost),(mat.b[senses=='='],original.rhs[:-ns]),
                       (np.r_[mat.b[senses=='<'],-mat.b[senses=='>']],original.limit),
                       (np.c_[mat.lb,mat.ub],np.asarray(original.bounds,dtype=float))]:
        if not np.array_equal(left,right,equal_nan=True):raise ValueError('Reconstructed monthly coefficients differ')
    primal=arrays['primal'];del original,arrays,mat
    state=np.zeros((len(rows)+1,ns))
    first=selected[0]['index'];last=selected[-1]['index']+1
    state[first]=monthly_state.reshape(13,ns)[args.month-1]
    for row in selected:state[row['index']+1]=inventory_at(model,primal,n.snapshots[row['end_hour_exclusive']-1])
    if np.max(abs(state[last]-monthly_state.reshape(13,ns)[args.month]))>1e-7:
        raise ValueError('Monthly endpoint mismatch')
    reports=[]
    for row in selected:
        index=row['index'];folder=args.calendar/f'{index:02d}'
        verify_block(folder,row,master['input_sha256'],len(rows))
        child=n.copy();child.set_snapshots(n.snapshots[row['start_hour']:row['end_hour_exclusive']])
        child.storage_units['cyclic_state_of_charge']=False
        child.storage_units['cyclic_state_of_charge_per_period']=False
        child.storage_units['state_of_charge_initial']=0.
        child_model=child.optimize.create_model(include_objective_constant=False)
        x=restrict_primal(model,child_model,primal);block=load_block(folder/'block.npz')
        eq=float(np.max(abs(block.equality@x+block.coupling@state.ravel()-block.rhs),initial=0.))
        ub=float(max(0.,np.max(block.inequality@x+block.inequality_coupling@state.ravel()-block.limit,initial=0.)))
        bounds=np.asarray(block.bounds,dtype=float)
        violation=float(max(0.,np.max(bounds[:,0]-x,initial=0.),np.max(x-bounds[:,1],initial=0.)))
        if not np.isfinite(x).all() or max(eq,ub,violation)>1e-7:raise ValueError('Restricted primal feasibility failed')
        target=args.output/f'{index:02d}-primal.npz'
        if target.exists():raise ValueError('Existing primal must not be overwritten')
        np.savez_compressed(target,primal=x)
        reports.append(dict(index=index,block_sha256=digest(folder/'block.npz'),primal_sha256=digest(target),
                            cost_eur=math.fsum(float(c)*float(v) for c,v in zip(block.cost,x)),
                            max_equality_residual=eq,max_inequality_violation=ub,max_bound_violation=violation))
        del child_model,child,block,x
    total=math.fsum(r['cost_eur'] for r in reports)
    if abs(total-checked['cost_eur'])>1e-4:raise ValueError('Restricted total cost differs from source monthly witness')
    np.savez_compressed(args.output/'boundary-state.npz',positions=np.arange(first,last+1),inventories_mwh=state[first:last+1])
    save(args.output/'verified.json',dict(status='restricted_monthly_primal_verified',month=args.month,
         input_sha256=master['input_sha256'],source_receipt_sha256=digest(receipt_path),
         source_witness_sha256=digest(witness_path),producer_sha256=digest(Path(__file__)),
         dependencies={k:digest(tools/k) for k in ['submonthly_primal_mapping.py','audit_monthly_dispatch_witnesses.py','pypsa_storage_blocks.py']},
         boundary_state_sha256=digest(args.output/'boundary-state.npz'),rows=reports,
         cost_eur=total,source_cost_difference_eur=total-checked['cost_eur'],
         scope='Restricted feasible monthly primal only; no derived dual, annual linkage, optimisation or empirical validation claim.'))


def run(args):
    if args.output.exists():raise ValueError('Preserve existing witness evidence')
    args.output.mkdir(parents=True)
    with (args.output/'worker.log').open('w') as log:
        child=subprocess.Popen([sys.executable,__file__,'--input',str(args.input),'--monthly',str(args.monthly),
             '--calendar',str(args.calendar),'--output',str(args.output),'--month',str(args.month),'--worker'],
             stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        peak=0;start=time.monotonic();save(args.output/'status.json',dict(status='restricting_monthly_witness',pid=child.pid))
        while child.poll() is None:
            try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
            except FileNotFoundError:rss=0
            peak=max(peak,rss);reason=guard_reason(time.monotonic()-start,rss,6.,300.)
            if reason:terminate_worker(child);save(args.output/'status.json',dict(status=reason,peak_rss_bytes=peak));return
            time.sleep(1)
        save(args.output/'status.json',dict(status='restricted_witness_complete' if child.returncode==0 else 'failed_requires_review',
             returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-start))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','monthly','calendar','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--month',type=int,required=True);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if not 1<=args.month<=12:parser.error('Invalid month')
    for name in ['input','monthly','calendar','output']:setattr(args,name,getattr(args,name).resolve())
    worker(args) if args.worker else run(args)
