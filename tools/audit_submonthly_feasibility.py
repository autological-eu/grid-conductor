"""Guarded boundary-elastic LP support for an infeasible annual proposal."""
import argparse,json,subprocess,sys,time
from pathlib import Path
from monthly_dispatch import digest,save
from audit_annual_warm_state import guard_reason,terminate_worker


def worker(args):
    import numpy as np
    from disk_storage_blocks import load_block
    from annual_inventory_phase_one import elastic_block,anchor_candidate,feasibility_support
    from native_storage_solver import solve_native
    from sparse_primal_correction import correct_sparse
    from phase_one_dual_probe import recover,probe
    from audit_submonthly_warm_calendar import primal_checks
    tools=Path(__file__).parent;source=digest(args.input)
    master=json.loads(args.master.read_text());domain=json.loads((args.workspace/'master-workspace.json').read_text())
    annual=json.loads((args.annual/'verified.json').read_text());replay=json.loads(args.master.with_suffix('.dual-replay.json').read_text())
    if any(d['input_sha256']!=source for d in [master,domain,annual,replay]) or master['inventory_workspace_sha256']!=digest(args.workspace/'master-workspace.json') or annual['status']!='annual_restricted_primal_feasible' or annual['annual_state_sha256']!=digest(args.annual/'annual-state.npz') or replay['master_receipt_sha256']!=digest(args.master):
        raise ValueError('Source-matched master and independently feasible annual anchor required')
    if master['producer_sha256']!=digest(tools/'build_submonthly_cut_master.py') or annual['producer_sha256']!=digest(tools/'audit_submonthly_warm_calendar.py'):
        raise ValueError('Master/anchor producer changed')
    for record in [master,domain,annual]:
        for name,value in record['dependencies'].items():
            if digest(tools/name)!=value:raise ValueError('Source/anchor dependency changed')
    state=np.asarray(master['proposal_mwh'],dtype=float)
    with np.load(args.annual/'annual-state.npz',allow_pickle=False) as data:anchor=data['inventories_mwh'].copy()
    row=next(r for r in annual['rows'] if r['index']==args.index)
    block_path=args.calendar/f'{args.index:02d}'/'block.npz'
    primal_path=args.warm/f"{row['month']:02d}"/f'{args.index:02d}-primal.npz'
    if digest(block_path)!=row['block_sha256'] or digest(primal_path)!=row['primal_sha256']:
        raise ValueError('Original anchor block/primal changed')
    block=load_block(block_path)
    with np.load(primal_path,allow_pickle=False) as data:primal=data['primal'].copy()
    primal_checks(block,anchor,primal)
    phase=elastic_block(block,boundary_only=True)
    point=anchor_candidate(block,state,primal,boundary_only=True)
    primal_checks(phase,state,point)  # Explicit feasible elastic anchor before any solve.
    diagnostic={}
    if args.dual_probe:
        # Explicit existing diagnostic mode: solver multipliers may be nonoptimal,
        # but the primal is the independently constructed feasible elastic point.
        # Only a globally supported positive cut can pass the checks below.
        result,diagnostic=probe(phase,state,point);candidate=point
        factor=diagnostic['dual_shrink_factor'];checks={'primal_origin':'constructed verified anchor'}
    else:
        result=solve_native(phase,state,time_limit=120.,threads=1)
        if result is None:raise ValueError('Native elastic LP reported infeasible despite constructed feasible point')
        candidate,checks=correct_sparse(phase,state,result.x)
        if not checks['original_unit_gate_passed']:raise ValueError('Phase-I correction failed original-unit gate')
        # Reuse tested finite-bound recovery; restore identity then shrink only
        # unsafe unbounded slack directions. Economic coefficients stay unchanged.
        scale=2.**-7;raw=np.r_[result.eqlin.marginals,result.ineqlin.marginals]
        result,factor=recover(phase,state,candidate,raw*scale,scale)
    checked=feasibility_support(phase,state,result,anchor)
    values=primal_checks(phase,state,candidate)
    witness=args.output/'witness.npz'
    np.savez_compressed(witness,primal=candidate,equality_duals=result.eqlin.marginals,inequality_duals=result.ineqlin.marginals,
                         lower_marginals=result.lower.marginals,upper_marginals=result.upper.marginals)
    np.savez_compressed(args.output/'boundary-state.npz',inventories_mwh=state)
    save(args.output/'verified.json',dict(status='submonthly_feasibility_support_requires_replay',index=args.index,
         input_sha256=source,master_sha256=digest(args.master),anchor_audit_sha256=digest(args.annual/'verified.json'),
         block_sha256=digest(block_path),witness_sha256=digest(witness),boundary_state_sha256=digest(args.output/'boundary-state.npz'),
         cost_eur=values['cost_eur'],dual_support_eur=checked['dual_support'],dual_intercept_eur=checked['intercept'],
         gradient_eur_per_mwh=checked['gradient'],multiplier_shrink_factor=factor,producer_sha256=digest(Path(__file__)),diagnostic=diagnostic,
         dependencies={name:digest(tools/name) for name in ['annual_inventory_phase_one.py','native_storage_solver.py','sparse_primal_correction.py','phase_one_dual_probe.py','check_storage_dual_bounds.py']},
         **{k:v for k,v in checked.items() if k not in ['scope']},
         scope='Boundary-elastic mismatch objective in inventory units, not euros despite legacy cost_eur replay key. Necessary numerical feasibility support only; independent saved-witness replay required before adoption. No welfare, price or annual objective cut.'))


def run(args):
    if args.output.exists():raise ValueError('Preserve existing feasibility evidence')
    args.output.mkdir(parents=True)
    with (args.output/'worker.log').open('w') as log:
        command=[sys.executable,__file__]
        for name in ['input','workspace','calendar','warm','annual','master','output']:command+=['--'+name,str(getattr(args,name))]
        if args.dual_probe:command+=['--dual-probe']
        child=subprocess.Popen(command+['--index',str(args.index),'--worker'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        started=time.monotonic();peak=0;save(args.output/'status.json',dict(status='solving_boundary_feasibility',pid=child.pid,index=args.index))
        while child.poll() is None:
            try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
            except FileNotFoundError:rss=0
            peak=max(peak,rss);reason=guard_reason(time.monotonic()-started,rss,6.,900. if args.dual_probe else 300.)
            if reason:terminate_worker(child);save(args.output/'status.json',dict(status=reason,peak_rss_bytes=peak));return
            time.sleep(1)
        save(args.output/'status.json',dict(status='feasibility_support_requires_replay' if child.returncode==0 else 'failed_requires_review',returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','workspace','calendar','warm','annual','master','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--index',type=int,required=True);parser.add_argument('--worker',action='store_true')
    parser.add_argument('--dual-probe',action='store_true',help='Explicit existing scaled 600s dual probe; nonoptimal multipliers require positive support and independent replay')
    args=parser.parse_args()
    if not 0<=args.index<59:parser.error('Invalid block index')
    worker(args) if args.worker else run(args)
