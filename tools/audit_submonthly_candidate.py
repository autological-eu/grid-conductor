"""Guarded fixed-boundary native LP oracle for one shorter annual block."""
import argparse,json,math,subprocess,sys,time
from pathlib import Path
from monthly_dispatch import digest,save
from audit_annual_warm_state import guard_reason,terminate_worker


def worker(args):
    import numpy as np
    from scipy import sparse
    from annual_inventory_workspace import validate_warm
    from disk_storage_blocks import load_block
    from native_storage_solver import solve_native
    from sparse_primal_correction import correct_sparse
    from check_storage_dual_bounds import objective_support
    from audit_submonthly_warm_calendar import primal_checks
    tools=Path(__file__).parent
    manifest_path=args.workspace/'master-workspace.json';manifest=json.loads(manifest_path.read_text())
    master=json.loads(args.master.read_text());replay_path=args.master.with_suffix('.dual-replay.json')
    replay=json.loads(replay_path.read_text())
    source=digest(args.input)
    if master['input_sha256']!=source or manifest['input_sha256']!=source or master['inventory_workspace_sha256']!=digest(manifest_path) or master['producer_sha256']!=digest(tools/'build_submonthly_cut_master.py') or replay['master_receipt_sha256']!=digest(args.master) or replay['status']!='independently_replayed_master_dual_support':
        raise ValueError('Source-matched independently replayed master required')
    if replay['tool_sha256']!=digest(tools/'replay_grouped_master_dual.py') or replay['support_tool_sha256']!=digest(tools/'grouped_master_dual.py') or replay['witness_sha256']!=digest(args.master.with_suffix('.witness.npz')):
        raise ValueError('Master replay producer or witness changed')
    for record in [master,manifest]:
        for name,value in record['dependencies'].items():
            if digest(tools/name)!=value:raise ValueError('Candidate source implementation changed')
    for name,value in manifest['workspace_sha256'].items():
        if digest(args.workspace/name)!=value:raise ValueError('Candidate inventory domain changed')
    with np.load(args.workspace/'master-state.npz',allow_pickle=False) as data:
        state=validate_warm(master['proposal_mwh'],data['bounds'],sparse.load_npz(args.workspace/'master-equality.npz'),data['rhs'])
        if np.max(sparse.load_npz(args.workspace/'master-inequality.npz')@state-data['limit'],initial=0.)>1e-7:
            raise ValueError('Candidate fails necessary inventory envelope')
    path=args.calendar/f'{args.index:02d}'/'block.npz'
    if not 0<=args.index<len(manifest['blocks']) or digest(path)!=manifest['block_sha256'][args.index]:
        raise ValueError('Candidate block source differs')
    block=load_block(path)
    result=solve_native(block,state,time_limit=120.,threads=1)
    if result is None:
        # The pinned adapter returns None only for native kInfeasible; unknown
        # or time-limited terminations raise. A diagnosis is not a replayed cut.
        save(args.output/'unresolved.json',dict(status='native_reported_infeasible_no_verified_cut',
             native_model_status='Infeasible',index=args.index,input_sha256=source,master_sha256=digest(args.master),
             producer_sha256=digest(Path(__file__)),native_solver_sha256=digest(tools/'native_storage_solver.py'),
             scope='Native diagnostic reports this fixed-boundary candidate infeasible. No independently verified infeasibility cut or annual result is established.'))
        raise ValueError('Native candidate reported infeasible; no verified cut')
    candidate,correction=correct_sparse(block,state,result.x)
    if not correction['original_unit_gate_passed']:raise ValueError('Candidate sparse correction original-unit gate failed')
    values=primal_checks(block,state,candidate);result.x=candidate;result.fun=values['cost_eur']
    gradient,intercept=objective_support(block,state,result);lower=float(intercept+gradient@state)
    if not np.isfinite(lower) or not np.isfinite(gradient).all() or lower>values['cost_eur']+1e-7:
        raise ValueError('Candidate primal/dual support inconsistent')
    witness=args.output/'witness.npz'
    np.savez_compressed(witness,primal=candidate,equality_duals=result.eqlin.marginals,inequality_duals=result.ineqlin.marginals,
                        lower_marginals=result.lower.marginals,upper_marginals=result.upper.marginals)
    np.savez_compressed(args.output/'boundary-state.npz',inventories_mwh=state)
    save(args.output/'verified.json',dict(status='conditional_submonthly_candidate_verified',index=args.index,
         input_sha256=source,master_sha256=digest(args.master),inventory_workspace_sha256=digest(manifest_path),block_sha256=digest(path),
         witness_sha256=digest(witness),boundary_state_sha256=digest(args.output/'boundary-state.npz'),
         dual_support_eur=lower,dual_intercept_eur=float(intercept),gradient_eur_per_mwh=gradient.tolist(),local_gap_eur=values['cost_eur']-lower,
         correction_checks=correction,producer_sha256=digest(Path(__file__)),
         dependencies={name:digest(tools/name) for name in ['native_storage_solver.py','sparse_primal_correction.py','check_storage_dual_bounds.py','audit_submonthly_warm_calendar.py']},
         **values,scope='Single fixed-boundary native block only; independent saved-witness replay still required. Not an annual feasible candidate, optimum or investment result.'))


def run(args):
    if args.output.exists():raise ValueError('Preserve existing candidate evidence')
    args.output.mkdir(parents=True)
    with (args.output/'worker.log').open('w') as log:
        command=[sys.executable,__file__]
        for name in ['input','workspace','calendar','master','output']:command+=['--'+name,str(getattr(args,name))]
        child=subprocess.Popen(command+['--index',str(args.index),'--worker'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        started=time.monotonic();peak=0;save(args.output/'status.json',dict(status='solving_conditional_submonthly_candidate',pid=child.pid,index=args.index))
        while child.poll() is None:
            try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
            except FileNotFoundError:rss=0
            peak=max(peak,rss);reason=guard_reason(time.monotonic()-started,rss,6.,300.)
            if reason:terminate_worker(child);save(args.output/'status.json',dict(status=reason,peak_rss_bytes=peak));return
            time.sleep(1)
        save(args.output/'status.json',dict(status='conditional_candidate_check_complete' if child.returncode==0 else 'failed_requires_review',returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','workspace','calendar','master','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--index',type=int,required=True);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if not 0<=args.index<59:parser.error('Invalid block index')
    worker(args) if args.worker else run(args)
