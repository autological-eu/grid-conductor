"""Guarded source-matched transfer of monthly LP duals; not a new solve."""
import argparse,json,math,subprocess,sys,time
from pathlib import Path
from monthly_dispatch import digest,save
from audit_annual_warm_state import guard_reason,terminate_worker


def worker(args):
    import numpy as np
    import pypsa
    from scipy import sparse
    from disk_storage_blocks import load_block
    from audit_monthly_dispatch_witnesses import replay
    from prepare_annual_coordination import validate_calendar
    from audit_submonthly_equivalence import difference
    from audit_submonthly_warm_calendar import primal_checks
    from submonthly_primal_mapping import restrict_primal
    from native_coordinate_restriction import restrict
    from submonthly_dual_mapping import restrict_duals
    from check_storage_dual_bounds import objective_support
    from prepare_submonthly_blocks import partitions
    from prepare_submonthly_warm_calendar import verify
    source_hash=digest(args.input);tools=Path(__file__).parent
    annual=json.loads((args.annual/'verified.json').read_text())
    if annual['status']!='annual_restricted_primal_feasible' or annual['input_sha256']!=source_hash or annual['producer_sha256']!=digest(tools/'audit_submonthly_warm_calendar.py') or annual['annual_state_sha256']!=digest(args.annual/'annual-state.npz'):
        raise ValueError('Verified annual primal required')
    for name,value in annual['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Annual replay dependency changed')
    if annual['restriction_manifest_sha256']!=digest(args.warm/'preparation-manifest.json') or annual['completed_months_sha256']!=digest(args.warm/'verified-months.json'):
        raise ValueError('Restriction calendar changed')
    with np.load(args.annual/'annual-state.npz',allow_pickle=False) as saved:state=saved['inventories_mwh'].copy()
    proof=verify(args.warm/f'{args.month:02d}',args.month,source_hash)
    path=args.monthly/'warm-audit'/f'{args.month:02d}.json';receipt=json.loads(path.read_text())
    witness=path.parent/f'{args.month:02d}-witness.npz'
    if digest(path)!=proof['source_receipt_sha256'] or digest(witness)!=proof['source_witness_sha256']:
        raise ValueError('Parent witness changed')
    for name,value in receipt['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Parent witness dependency changed')
    with np.load(witness,allow_pickle=False) as saved:arrays={name:saved[name].copy() for name in saved.files}
    with np.load(args.monthly/'master-state.npz',allow_pickle=False) as saved:monthly_state=saved['warm_state_mwh'].copy()
    if digest(args.monthly/'master-state.npz')!=receipt['warm_state_sha256'] or digest(args.monthly/f'{args.month:02d}.npz')!=receipt['block_sha256']:
        raise ValueError('Parent primal domain changed')
    original=load_block(args.monthly/f'{args.month:02d}.npz');replay(original,monthly_state,arrays,receipt)
    n=pypsa.Network(args.input);validate_calendar(n,2025);n.global_constraints.drop(n.global_constraints.index,inplace=True)
    rows=[r for r in partitions(2025,168) if r['month']==args.month];ns=len(n.storage_units)
    parent=n.copy();parent.set_snapshots(n.snapshots[rows[0]['start_hour']:rows[-1]['end_hour_exclusive']])
    def make_model(network):
        network.storage_units['cyclic_state_of_charge']=False
        network.storage_units['cyclic_state_of_charge_per_period']=False
        network.storage_units['state_of_charge_initial']=0.
        return network.optimize.create_model(include_objective_constant=False)
    model=make_model(parent);mat=model.matrices;sense=np.asarray(mat.sense)
    for left,right in [(mat.A.tocsr()[sense=='='],original.equality[:-ns]),(sparse.vstack([mat.A.tocsr()[sense=='<'],-mat.A.tocsr()[sense=='>']]),original.inequality)]:
        if difference(left,right)!=0.:raise ValueError('Parent native row layout differs')
    for left,right in [(mat.c,original.cost),(mat.b[sense=='='],original.rhs[:-ns]),(np.r_[mat.b[sense=='<'],-mat.b[sense=='>']],original.limit),(np.c_[mat.lb,mat.ub],np.asarray(original.bounds,dtype=float))]:
        if not np.array_equal(left,right,equal_nan=True):raise ValueError('Parent native coefficients differ')
    del original,mat
    checked=[]
    for row in rows:
        index=row['index'];target=next(item for item in annual['rows'] if item['index']==index)
        path=args.calendar/f'{index:02d}'/'block.npz';primal_path=args.warm/f'{args.month:02d}'/f'{index:02d}-primal.npz'
        if digest(path)!=target['block_sha256'] or digest(primal_path)!=target['primal_sha256']:
            raise ValueError('Target coefficients or primal changed')
        child=n.copy();times=n.snapshots[row['start_hour']:row['end_hour_exclusive']];child.set_snapshots(times)
        child_model=make_model(child);block=load_block(path)
        with np.load(primal_path,allow_pickle=False) as saved:x=saved['primal'].copy()
        if not np.array_equal(x,restrict(model,child_model,arrays['primal'],'variables')):
            raise ValueError('Primal column mapping differs from verified restriction')
        values=primal_checks(block,state,x)
        result=restrict_duals(n,model,child_model,arrays,times[-1])
        gradient,intercept=objective_support(block,state,result);support=float(intercept+gradient@state)
        if not np.isfinite(support) or not np.isfinite(gradient).all() or support>values['cost_eur']+1e-7:
            raise ValueError('Transferred dual support exceeds feasible primal')
        dual_path=args.output/f'{index:02d}-dual.npz'
        np.savez_compressed(dual_path,equality_duals=result.eqlin.marginals,inequality_duals=result.ineqlin.marginals,
                            lower_marginals=result.lower.marginals,upper_marginals=result.upper.marginals)
        checked.append(dict(index=index,block_sha256=target['block_sha256'],primal_sha256=target['primal_sha256'],
             dual_sha256=digest(dual_path),dual_support_eur=support,dual_intercept_eur=float(intercept),
             gradient_eur_per_mwh=gradient.tolist(),local_gap_eur=values['cost_eur']-support,**values))
        del child,child_model,block,x,result
    save(args.output/'verified.json',dict(status='transferred_dual_supports_checked',month=args.month,input_sha256=source_hash,
         annual_primal_audit_sha256=digest(args.annual/'verified.json'),parent_receipt_sha256=digest(args.monthly/'warm-audit'/f'{args.month:02d}.json'),
         producer_sha256=digest(Path(__file__)),dependencies={name:digest(tools/name) for name in ['submonthly_dual_mapping.py','submonthly_primal_mapping.py','native_coordinate_restriction.py','audit_submonthly_warm_calendar.py','check_storage_dual_bounds.py']},
         rows=checked,scope='Transferred floating-point affine supports checked against original LP and feasible primal; independent saved-dual replay and master adoption still required. No new solver termination or annual optimum.'))


def run(args):
    if args.output.exists():raise ValueError('Preserve existing dual evidence')
    args.output.mkdir(parents=True)
    with (args.output/'worker.log').open('w') as log:
        command=[sys.executable,__file__]
        for name in ['input','monthly','calendar','warm','annual','output']:command+=['--'+name,str(getattr(args,name))]
        child=subprocess.Popen(command+['--month',str(args.month),'--worker'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        started=time.monotonic();peak=0;save(args.output/'status.json',dict(status='checking_transferred_supports',pid=child.pid))
        while child.poll() is None:
            try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
            except FileNotFoundError:rss=0
            peak=max(peak,rss);reason=guard_reason(time.monotonic()-started,rss,6.,300.)
            if reason:terminate_worker(child);save(args.output/'status.json',dict(status=reason,peak_rss_bytes=peak));return
            time.sleep(1)
        save(args.output/'status.json',dict(status='transferred_support_check_complete' if child.returncode==0 else 'failed_requires_review',returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','monthly','calendar','warm','annual','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--month',type=int,required=True);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if not 1<=args.month<=12:parser.error('Invalid month')
    worker(args) if args.worker else run(args)
