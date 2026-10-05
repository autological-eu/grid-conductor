"""Finite, locked annual coordination driver. Every accepted cut/upper bound requires replay.

Linux offline research only. It never declares an annual optimum, empirical
validation or an investment result. Solver failures stay explicit checkpoints.
"""
import argparse
from contextlib import contextmanager
import fcntl
import json
from importlib.metadata import version
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from monthly_dispatch import digest,save

CALCULATION_FILES=['audit_annual_warm_state.py','annual_inventory_phase_one.py','phase_one_dual_probe.py','audit_annual_feasibility_cut.py',
 'audit_monthly_dispatch_witnesses.py','annual_inventory_master.py','build_annual_multicut_master.py',
 'prepare_annual_inventory_candidate.py','native_storage_solver.py','check_storage_dual_bounds.py',
 'storage_coordinator.py','storage_master_dual.py','storage_objective_floor.py','disk_storage_blocks.py',
 'annual_inventory_workspace.py','inventory_reachability.py','audit_annual_coordination_preparation.py',
 'prepare_annual_coordination.py','pypsa_storage_blocks.py','sparse_primal_correction.py','monthly_dispatch.py']


@contextmanager
def driver_lock(path):
    with path.open('a+') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield


def live_jobs(folders):
    accepted={str(p.resolve()) for p in folders};result=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            status=(path/'status').read_text()
            if any(line.startswith('State:') and 'Z' in line.split()[1] for line in status.splitlines()):continue
            args=(path/'cmdline').read_bytes().decode().split('\0')
            if not any(Path(arg).name in ('audit_annual_warm_state.py','annual_inventory_phase_one.py','phase_one_dual_probe.py') for arg in args):continue
            if '--folder' not in args:continue
            folder=str(Path(args[args.index('--folder')+1]).resolve())
            if folder in accepted:result.append(int(path.name))
        except (FileNotFoundError,ProcessLookupError,PermissionError,UnicodeError,IndexError):continue
    return result


def read(path):return json.loads(path.read_text()) if path.exists() else None


def choose_action(records,active,max_candidates):
    if active:return ('wait',active)
    for folder,item in records:
        audit=item['audit'];status=item['objective'];phase=item['phase'];cut=item['cut']
        if audit and audit.get('status')=='annual_fixed_inventory_feasible':continue
        if status and status.get('status')=='requested_warm_months_verified':return ('replay',folder)
        if cut and cut.get('status')=='independently_replayed_numerical_feasibility_cut':continue
        if phase and phase.get('status')=='cut_requires_independent_replay':return ('replay_cut',(folder,phase['month']))
        if phase and phase.get('status') in ('failed','stopped_memory_guard','stopped_wall_time_guard') and not item.get('probe'):
            return ('probe',(folder,phase['month']))
        if phase:return ('blocked',dict(folder=str(folder),reason='Phase-I incomplete or failed; inspect actual receipt/log before retry',status=phase['status']))
        if status and status.get('status') in ('failed','stopped_memory_guard','stopped_wall_time_guard'):
            return ('phase_one',(folder,status['month']))
        return ('solve',folder)
    if len(records)>=max_candidates:return ('limit',None)
    return ('propose',None)


def run(args):
    root=args.root.resolve();candidates=args.candidates.resolve();candidates.mkdir(parents=True,exist_ok=True)
    status_path=root/'driver-status.json';manifest_path=root/'driver-manifest.json'
    tools=Path(__file__).resolve().parent
    source_hash=digest(args.source)
    baseline=read(root/'master-workspace.json')
    if not baseline or baseline['input_sha256']!=source_hash or baseline['year']!=2025:
        raise ValueError('Driver source must match the prepared 2025 model')
    packages={name:version(name) for name in ['numpy','scipy','pypsa','highspy']}
    signature=dict(input_sha256=source_hash,driver_sha256=digest(Path(__file__)),packages=packages,
        dependencies={name:digest(tools/name) for name in CALCULATION_FILES},
        absolute_gap=args.absolute_gap,relative_gap=args.relative_gap,max_candidates=args.max_candidates)
    old=read(manifest_path)
    if old is not None and old!=signature:raise ValueError('Driver source/code/settings changed; do not resume old state silently')
    with driver_lock(root/'driver.lock'):
        save(manifest_path,signature)
        def report(stage,**fields):save(status_path,dict(status=stage,pid=os.getpid(),**fields))
        def call(name,*arguments):
            report('executing',tool=name)
            subprocess.run([sys.executable,str(tools/name),*map(str,arguments)],check=True)
        try:
            while True:
                if any(version(name)!=value for name,value in signature['packages'].items()) or digest(args.source)!=signature['input_sha256'] or any(digest(tools/name)!=value for name,value in signature['dependencies'].items()):
                    raise ValueError('Active driver calculation/input changed')
                folders=sorted(p for p in candidates.iterdir() if p.is_dir() and p.name.isdigit())
                active=live_jobs([root,*folders]);records=[]
                for folder in folders:
                    records.append((folder,dict(audit=read(folder/'warm-audit'/'independent-witness-audit.json'),
                      objective=read(folder/'warm-audit'/'status.json'),phase=read(folder/'phase-one-boundary'/'status.json'),
                      cut=read(folder/'phase-one-boundary'/'01-verified-cut.json'),probe=read(folder/'phase-one-boundary-dual-probe'/'status.json'))))
                    # A failed later month must select its own diagnostic/cut.
                    item=records[-1][1];month=(item['phase'] or item['objective'] or {}).get('month',1)
                    if item['probe']:
                        item['phase']=item['probe'];month=item['probe']['month']
                        item['cut']=read(folder/'phase-one-boundary-dual-probe'/f'{month:02d}-verified-cut.json')
                    else:item['cut']=read(folder/'phase-one-boundary'/f'{month:02d}-verified-cut.json')
                action,payload=choose_action(records,active,args.max_candidates)
                report(action,active_jobs=active)
                if action=='wait':
                    time.sleep(30);continue
                if action in ('blocked','limit'):
                    report('blocked' if action=='blocked' else 'candidate_limit_not_converged',detail=payload);return
                if shutil.disk_usage(root).free<2*2**30:raise RuntimeError('Less than 2 GiB free disk; no new compute job started')
                if action=='replay':
                    call('audit_monthly_dispatch_witnesses.py','--folder',payload,'--input',args.source,'--through',12)
                elif action=='replay_cut':
                    folder,month=payload
                    extra=['--probe'] if read(folder/'phase-one-boundary-dual-probe'/'status.json') else []
                    call('audit_annual_feasibility_cut.py','--folder',folder,'--anchor',root,'--month',month,'--mode','boundary',*extra)
                elif action=='phase_one':
                    folder,month=payload
                    call('annual_inventory_phase_one.py','--folder',folder,'--anchor',root,'--month',month,'--mode','boundary')
                elif action=='probe':
                    folder,month=payload
                    call('phase_one_dual_probe.py','--folder',folder,'--anchor',root,'--month',month)
                elif action=='solve':
                    call('audit_annual_warm_state.py','--folder',payload,'--last-month',12,'--memory-gib',6,'--solver-seconds',600,'--wall-seconds',900,'--native-no-crossover','--native-threads',2)
                else:
                    accepted=read(root/'warm-audit'/'independent-witness-audit.json')
                    if not accepted or accepted['status']!='annual_fixed_inventory_feasible':raise ValueError('Verified complete annual incumbent required')
                    feasible=[root]+[folder for folder,item in records if item['audit'] and item['audit'].get('status')=='annual_fixed_inventory_feasible']
                    cuts=[path for folder,item in records for directory in ['phase-one-boundary','phase-one-boundary-dual-probe'] for path in sorted((folder/directory).glob('*-verified-cut.json')) if item['cut']]
                    from build_annual_multicut_master import build
                    parent,result=build(feasible,cuts)
                    threshold=args.absolute_gap+args.relative_gap*abs(result['annual_feasible_cost_eur'])
                    if result['annual_gap_eur']<=threshold:
                        report('gap_gate_met_requires_annual_verification',gap_eur=result['annual_gap_eur'],threshold_eur=threshold);return
                    next_id=max([0]+[int(p.name) for p in folders])+1
                    target=candidates/f'{next_id:03d}'
                    call('prepare_annual_inventory_candidate.py','--parent',parent,'--output',target,'--proposal','multi-cut-master.json')
        except Exception as error:
            report('failed_requires_review',error_type=type(error).__name__)
            raise

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True);parser.add_argument('--candidates',type=Path,required=True);parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--absolute-gap',type=float,default=1e-5);parser.add_argument('--relative-gap',type=float,default=1e-9);parser.add_argument('--max-candidates',type=int,default=200)
    args=parser.parse_args()
    if not 0<=args.absolute_gap<1 or not 0<=args.relative_gap<=1e-9 or not 1<=args.max_candidates<=200:parser.error('Unsupported finite coordination bounds')
    run(args)
