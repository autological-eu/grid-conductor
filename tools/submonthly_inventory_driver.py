"""Finite locked shorter-block coordination; no annual validation claim.

Every objective and feasibility cut is independently replayed before adoption.
An annual upper bound requires all blocks at one exact linked inventory state.
Failures, exhausted candidate budgets and numerical gaps remain distinct.
"""
import argparse,fcntl,json,os,shutil,subprocess,sys,time
from pathlib import Path
from importlib.metadata import version
from monthly_dispatch import digest,save

FILES=['build_submonthly_cut_master.py','grouped_storage_master.py','grouped_master_dual.py',
    'replay_grouped_master_dual.py','audit_submonthly_candidate.py','replay_submonthly_candidate.py',
    'audit_submonthly_feasibility.py','replay_submonthly_feasibility.py','submonthly_feasibility_donor.py',
    'submonthly_objective_donor.py','audit_submonthly_economic_calendar.py','annual_inventory_phase_one.py',
    'phase_one_dual_probe.py','native_storage_solver.py','sparse_primal_correction.py','check_storage_dual_bounds.py',
    'audit_monthly_dispatch_witnesses.py','disk_storage_blocks.py','storage_coordinator.py','storage_master_dual.py',
    'prepare_submonthly_inventory_workspace.py','prepare_submonthly_dual_calendar.py','monthly_dispatch.py',
    'annual_inventory_workspace.py','inventory_reachability.py','submonthly_inventory_mapping.py',
    'storage_objective_floor.py','prepare_annual_coordination.py','pypsa_storage_blocks.py','submonthly_proposal.py']
WORKERS={'audit_submonthly_candidate.py','audit_submonthly_feasibility.py','audit_submonthly_farkas.py',
    'annual_inventory_driver.py','audit_annual_warm_state.py','annual_inventory_phase_one.py','phase_one_dual_probe.py',
    'prepare_submonthly_calendar.py','prepare_submonthly_warm_calendar.py','prepare_submonthly_dual_calendar.py',
    'submonthly_inventory_driver.py'}


def read(path):return json.loads(path.read_text()) if path.exists() else None


def verify_annual(folder,domain):
    """Verify the saved annual replay chain before reusing its upper bound."""
    import math
    from submonthly_objective_donor import load
    tools=Path(__file__).parent;record=read(folder/'annual-replay.json')
    if (record['status']!='independently_replayed_economic_annual_feasible'
            or record['input_sha256']!=domain['input_sha256'] or record['hours']!=8760 or record['blocks']!=59
            or record['producer_sha256']!=digest(tools/'audit_submonthly_economic_calendar.py')
            or record['annual_state_sha256']!=digest(folder/'annual-state.npz')
            or [row['index'] for row in record['rows']]!=list(range(59))):
        raise ValueError('Cached linked annual replay differs')
    for name,value in record['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Annual replay calculation changed')
    for row in record['rows']:
        block_folder=folder/f"{row['index']:02d}";path=block_folder/'independent-replay.json';load(path,domain)
        if row['replay_sha256']!=digest(path) or row['receipt_sha256']!=digest(block_folder/'verified.json') or row['witness_sha256']!=digest(block_folder/'witness.npz'):
            raise ValueError('Cached annual witness chain changed')
        replay=read(path)
        if replay['master_sha256']!=record['master_sha256'] or row['cost_eur']!=replay['cost_eur']:
            raise ValueError('Cached annual linkage or objective differs')
    value=math.fsum(row['cost_eur'] for row in record['rows'])
    if value!=record['annual_feasible_cost_eur']:raise ValueError('Cached annual cost does not reproduce')
    return value


def verify_master(path,source):
    """Recompute cached lower support; never trust a status/number alone."""
    import numpy as np
    from scipy import sparse
    from grouped_master_dual import support
    tools=Path(__file__).parent;record=read(path);proof=read(path.with_suffix('.dual-replay.json'))
    witness=path.with_suffix('.witness.npz')
    if (record['input_sha256']!=source or record['producer_sha256']!=digest(tools/'build_submonthly_cut_master.py')
            or proof['status']!='independently_replayed_master_dual_support'
            or proof['master_receipt_sha256']!=digest(path) or proof['witness_sha256']!=digest(witness)
            or record['master_witness_sha256']!=digest(witness)
            or proof['tool_sha256']!=digest(tools/'replay_grouped_master_dual.py')
            or proof['support_tool_sha256']!=digest(tools/'grouped_master_dual.py')):
        raise ValueError('Cached master provenance differs')
    for name,value in record['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Cached master implementation changed')
    with np.load(witness,allow_pickle=False) as saved:data={name:saved[name].copy() for name in saved.files}
    matrices={name:sparse.csr_matrix((data[name+'_data'],data[name+'_indices'],data[name+'_indptr']),shape=tuple(data[name+'_shape'])) for name in ['inequality','equality']}
    result=support(data['cost'],matrices['inequality'],data['inequality_rhs'],matrices['equality'],data['equality_rhs'],
        [tuple(b) for b in data['bounds']],data['inequality_duals'],data['equality_duals'],int(data['shared_variables']))
    if result['lower_bound_eur']!=proof['lower_bound_eur'] or result['lower_bound_eur']!=record['lower_bound_eur']:
        raise ValueError('Cached lower support does not reproduce')
    return result['lower_bound_eur']


def active_jobs():
    jobs=[]
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit():continue
        if int(folder.name)==os.getpid():continue
        try:
            if any(line.startswith('State:') and line.split()[1]=='Z' for line in (folder/'status').read_text().splitlines()):continue
            args=(folder/'cmdline').read_bytes().decode().split('\0')
            if any(Path(arg).name in WORKERS for arg in args):jobs.append(int(folder.name))
        except (FileNotFoundError,ProcessLookupError,PermissionError,UnicodeError):continue
    return jobs


def block_action(folder):
    """Stale running receipts never authorize a replacement job."""
    independent=read(folder/'independent-replay.json')
    if independent:return 'complete' if independent.get('status')=='independently_replayed_submonthly_economic_witness' else 'blocked'
    verified=read(folder/'verified.json')
    if verified:return 'replay' if verified.get('status')=='conditional_submonthly_candidate_verified' else 'blocked'
    if not folder.exists():return 'solve'
    failed=read(folder/'unresolved.json')
    if failed and failed.get('status')=='native_reported_infeasible_no_verified_cut':return 'infeasible'
    return 'blocked'


def run(args):
    tools=Path(__file__).parent;args.root.mkdir(parents=True,exist_ok=True)
    domain_path=args.workspace/'master-workspace.json';domain=read(domain_path)
    if not domain or domain['input_sha256']!=digest(args.input) or domain['year']!=2025:
        raise ValueError('Prepared source-matched annual workspace required')
    signature=dict(input_sha256=domain['input_sha256'],domain_sha256=digest(domain_path),
        producer_sha256=digest(Path(__file__)),dependencies={name:digest(tools/name) for name in FILES},
        packages={name:version(name) for name in ['numpy','scipy','pypsa','highspy']},
        max_candidates=args.max_candidates,absolute_gap=args.absolute_gap,relative_gap=args.relative_gap,
        proposal_weight=args.proposal_weight,
        seed_feasibility={str(p.resolve()):digest(p) for p in args.feasibility},
        seed_submonthly_feasibility={str(p.resolve()):digest(p) for p in args.submonthly_feasibility})
    with (args.root/'driver.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old=read(args.root/'driver-manifest.json')
        if old is not None and old!=signature:raise ValueError('Frozen driver source/code/settings changed; explicit migration required')
        save(args.root/'driver-manifest.json',signature)
        def report(stage,**fields):save(args.root/'driver-status.json',dict(status=stage,pid=os.getpid(),**fields))
        def frozen():
            if digest(args.input)!=signature['input_sha256'] or digest(domain_path)!=signature['domain_sha256']:
                raise ValueError('Active annual source changed')
            if any(digest(tools/name)!=value for name,value in signature['dependencies'].items()) or any(version(name)!=value for name,value in signature['packages'].items()):
                raise ValueError('Active annual calculation environment changed')
        def call(name,**values):
            frozen()
            if active_jobs():raise ValueError('Another research worker is live; no duplicate job started')
            if shutil.disk_usage(args.root).free<2*2**30:raise ValueError('Less than 2 GiB free; no worker started')
            command=[sys.executable,str(tools/name)]
            for key,value in values.items():
                key='--'+key.replace('_','-')
                if isinstance(value,bool):
                    if value:command.append(key)
                else:
                    for item in value if isinstance(value,list) else [value]:command.extend([key,str(item)])
            report('executing',tool=name)
            subprocess.run(command,check=True)
        common=dict(input=args.input,workspace=args.workspace,calendar=args.calendar)
        lower=0.;upper=domain['annual_feasible_cost_eur']
        try:
            for iteration in range(1,args.max_candidates+1):
                frozen()
                while active_jobs():
                    report('waiting_for_existing_workers',active_jobs=active_jobs());time.sleep(30);frozen()
                folders=sorted(p for p in args.root.glob('candidate-*') if p.is_dir())
                feasibility=list(args.submonthly_feasibility);objectives=[]
                for folder in folders:
                    for path in folder.glob('phase-*/independent-replay.json'):
                        if read(path).get('status')=='independently_replayed_submonthly_feasibility_cut':feasibility.append(path)
                    for path in folder.glob('[0-9][0-9]/independent-replay.json'):
                        if read(path).get('status')=='independently_replayed_submonthly_economic_witness':objectives.append(path)
                    annual=read(folder/'annual-replay.json')
                    if annual:
                        upper=min(upper,verify_annual(folder,domain))
                folder=args.root/f'candidate-{iteration:03d}';folder.mkdir(exist_ok=True)
                master=folder/'master.json'
                if not master.exists():
                    call('build_submonthly_cut_master.py',**common,monthly=args.monthly,support=args.support,output=master,
                        feasibility=args.feasibility,submonthly_feasibility=feasibility,objective=objectives,include_equalities=True,
                        proposal_weight=args.proposal_weight)
                if not master.with_suffix('.dual-replay.json').exists():call('replay_grouped_master_dual.py',master=master)
                lower=max(lower,verify_master(master,signature['input_sha256']));gap=upper-lower
                if gap < -1e-7:raise ValueError('Annual lower support exceeds feasible incumbent')
                threshold=args.absolute_gap+args.relative_gap*abs(upper)
                report('evaluating_proposal',iteration=iteration,lower_support_eur=lower,annual_feasible_cost_eur=upper,gap_eur=gap)
                if gap<=threshold:
                    report('numerical_gap_gate_met_requires_annual_validation',lower_support_eur=lower,annual_feasible_cost_eur=upper,gap_eur=gap,threshold_eur=threshold);return
                infeasible=False
                for index in range(len(domain['blocks'])):
                    block_folder=folder/f'{index:02d}';action=block_action(block_folder)
                    if action=='solve':
                        call('audit_submonthly_candidate.py',**common,master=master,index=index,output=block_folder)
                        action=block_action(block_folder)
                    if action=='replay':call('replay_submonthly_candidate.py',**common,folder=block_folder);action=block_action(block_folder)
                    if action=='complete':continue
                    if action!='infeasible':
                        report('blocked_requires_review',iteration=iteration,index=index,reason='No independently replayed economic witness or supported infeasibility diagnosis');return
                    phase=folder/f'phase-{index:02d}'
                    if not phase.exists():
                        call('audit_submonthly_feasibility.py',**common,warm=args.warm,annual=args.annual,
                            master=master,index=index,dual_probe=True,output=phase)
                    if not (phase/'independent-replay.json').exists():
                        if not (phase/'verified.json').exists():
                            report('blocked_requires_review',iteration=iteration,index=index,reason='Bounded feasibility probe yielded no independently replayable support');return
                        call('replay_submonthly_feasibility.py',input=args.input,calendar=args.calendar,warm=args.warm,annual=args.annual,folder=phase)
                    infeasible=True;break
                if not infeasible:
                    if not (folder/'annual-replay.json').exists():call('audit_submonthly_economic_calendar.py',**common,folder=folder)
                    upper=min(upper,read(folder/'annual-replay.json')['annual_feasible_cost_eur'])
            report('candidate_limit_not_converged',lower_support_eur=lower,annual_feasible_cost_eur=upper,gap_eur=upper-lower)
        except Exception as error:
            report('failed_requires_review',error_type=type(error).__name__);raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','workspace','calendar','monthly','support','warm','annual','root']:parser.add_argument('--'+name,type=Path,required=True)
    for name in ['feasibility','submonthly-feasibility']:parser.add_argument('--'+name,type=Path,action='append',default=[])
    parser.add_argument('--max-candidates',type=int,default=10)
    parser.add_argument('--absolute-gap',type=float,default=1e-5);parser.add_argument('--relative-gap',type=float,default=1e-9)
    parser.add_argument('--proposal-weight',type=float,default=1.)
    args=parser.parse_args()
    if not 1<=args.max_candidates<=200 or not 0<=args.absolute_gap<1 or not 0<=args.relative_gap<=1e-9 or not 0<args.proposal_weight<=1:
        parser.error('Unsupported finite numerical coordination settings')
    run(args)
