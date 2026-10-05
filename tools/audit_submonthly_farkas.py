"""Guarded dual-ray diagnostic and saved source-bounded feasibility support."""
import argparse,json,subprocess,sys,time
from pathlib import Path
from monthly_dispatch import digest,save
from audit_annual_warm_state import guard_reason,terminate_worker


def worker(args):
    import numpy as np
    from disk_storage_blocks import load_block
    from submonthly_farkas_support import native_ray,checked_support
    from audit_submonthly_warm_calendar import primal_checks
    tools=Path(__file__).parent;source=digest(args.input)
    master=json.loads(args.master.read_text());annual=json.loads((args.annual/'verified.json').read_text())
    if master['input_sha256']!=source or annual['input_sha256']!=source or annual['status']!='annual_restricted_primal_feasible' or master['producer_sha256']!=digest(tools/'build_submonthly_cut_master.py') or annual['producer_sha256']!=digest(tools/'audit_submonthly_warm_calendar.py') or annual['annual_state_sha256']!=digest(args.annual/'annual-state.npz'):
        raise ValueError('Source-matched master/verified annual anchor required')
    for record in [master,annual]:
        for name,value in record['dependencies'].items():
            if digest(tools/name)!=value:raise ValueError('Source/anchor producer dependency changed')
    row=next(r for r in annual['rows'] if r['index']==args.index)
    path=args.calendar/f'{args.index:02d}'/'block.npz';primal=args.warm/f"{row['month']:02d}"/f'{args.index:02d}-primal.npz'
    if digest(path)!=row['block_sha256'] or digest(primal)!=row['primal_sha256']:
        raise ValueError('Original source block or anchor witness changed')
    block=load_block(path);state=np.asarray(master['proposal_mwh'],dtype=float)
    with np.load(args.annual/'annual-state.npz',allow_pickle=False) as data:anchor=data['inventories_mwh'].copy()
    with np.load(primal,allow_pickle=False) as data:point=data['primal'].copy()
    primal_checks(block,anchor,point)
    dependencies=['submonthly_farkas_support.py','check_storage_dual_bounds.py','audit_submonthly_warm_calendar.py']
    if args.economic_ray:
        from economic_infeasibility_ray import native_ray
        dependencies.append('economic_infeasibility_ray.py')
    ray,termination=native_ray(block,state,seconds=120.)
    value,result,g,intercept,at_anchor,sign,norm=checked_support(block,state,anchor,ray)
    np.savez_compressed(args.output/'witness.npz',ray=ray,equality_duals=result.eqlin.marginals,inequality_duals=result.ineqlin.marginals,
                        candidate_state_mwh=state,anchor_state_mwh=anchor)
    save(args.output/'verified.json',dict(status='farkas_support_requires_independent_replay',index=args.index,input_sha256=source,
       master_sha256=digest(args.master),anchor_audit_sha256=digest(args.annual/'verified.json'),block_sha256=digest(path),anchor_primal_sha256=digest(primal),
       witness_sha256=digest(args.output/'witness.npz'),native_termination=termination,dual_support=value,gradient=g.tolist(),intercept=intercept,
       feasibility_limit=1e-7-intercept,anchor_support=at_anchor,ray_orientation=sign,ray_normalisation=norm,
       producer_sha256=digest(Path(__file__)),dependencies={name:digest(tools/name) for name in dependencies},
       diagnostic_objective='Original economic coefficients; ray supported against zero-objective feasible set' if args.economic_ray else 'Zero objective',
       scope='Source-bounded zero-objective feasibility support only; not an economic objective, price or welfare estimate. Independent saved-witness replay required before adoption.'))


def run(args):
    if args.output.exists():raise ValueError('Preserve existing ray evidence')
    args.output.mkdir(parents=True)
    with (args.output/'worker.log').open('w') as log:
        command=[sys.executable,__file__]
        for name in ['input','calendar','warm','annual','master','output']:command+=['--'+name,str(getattr(args,name))]
        if args.economic_ray:command+=['--economic-ray']
        child=subprocess.Popen(command+['--index',str(args.index),'--worker'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        started=time.monotonic();peak=0;save(args.output/'status.json',dict(status='diagnosing_native_dual_ray',pid=child.pid,index=args.index))
        while child.poll() is None:
            try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
            except FileNotFoundError:rss=0
            peak=max(peak,rss);reason=guard_reason(time.monotonic()-started,rss,6.,300.)
            if reason:terminate_worker(child);save(args.output/'status.json',dict(status=reason,peak_rss_bytes=peak));return
            time.sleep(1)
        save(args.output/'status.json',dict(status='farkas_support_requires_replay' if child.returncode==0 else 'failed_requires_review',returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','calendar','warm','annual','master','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--index',type=int,required=True);parser.add_argument('--worker',action='store_true')
    parser.add_argument('--economic-ray',action='store_true',help='Diagnose original-cost IPM model before requesting its ray; support still uses zero objective')
    args=parser.parse_args()
    if not 0<=args.index<59:parser.error('Invalid block index')
    worker(args) if args.worker else run(args)
