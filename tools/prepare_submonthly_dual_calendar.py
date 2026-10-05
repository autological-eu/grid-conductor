"""Sequential guarded support transfer plus independent saved-dual replay."""
import argparse,json,os,subprocess,sys
from importlib.metadata import version
from pathlib import Path
from annual_inventory_driver import driver_lock
from monthly_dispatch import digest,save
from prepare_submonthly_blocks import partitions


def verify(folder,month,source):
    tools=Path(__file__).parent
    record=json.loads((folder/'verified.json').read_text())
    replay=json.loads((folder/'independent-replay.json').read_text())
    status=json.loads((folder/'status.json').read_text())
    if status['status']!='transferred_support_check_complete' or record['status']!='transferred_dual_supports_checked' or replay['status']!='independently_replayed_transferred_supports' or record['input_sha256']!=source or replay['input_sha256']!=source or record['month']!=month or replay['month']!=month:
        raise ValueError('Completed source-matched transferred/replayed support required')
    if replay['producer_receipt_sha256']!=digest(folder/'verified.json') or record['producer_sha256']!=digest(tools/'audit_submonthly_dual_support.py') or replay['replay_tool_sha256']!=digest(tools/'replay_submonthly_dual_witness.py'):
        raise ValueError('Support producer or independent replay changed')
    if set(record['dependencies'])!={'submonthly_dual_mapping.py','submonthly_primal_mapping.py','native_coordinate_restriction.py','audit_submonthly_warm_calendar.py','check_storage_dual_bounds.py'} or set(replay['dependencies'])!={'audit_monthly_dispatch_witnesses.py','check_storage_dual_bounds.py','disk_storage_blocks.py'}:
        raise ValueError('Incomplete support dependency fingerprints')
    for proof in [record,replay]:
        for name,value in proof['dependencies'].items():
            if digest(tools/name)!=value:raise ValueError('Support dependency changed')
    expected=[r['index'] for r in partitions(2025,168) if r['month']==month]
    if [r['index'] for r in record['rows']]!=expected or [r['index'] for r in replay['rows']]!=expected:
        raise ValueError('Incomplete chronological support partition')
    for row in record['rows']:
        if digest(folder/f"{row['index']:02d}-dual.npz")!=row['dual_sha256']:
            raise ValueError('Saved support witness changed')
    return record


def run(args):
    args.output.mkdir(parents=True,exist_ok=True);tools=Path(__file__).parent
    source=digest(args.input);annual_hash=digest(args.annual/'verified.json')
    signature=dict(input_sha256=source,annual_primal_audit_sha256=annual_hash,
       annual_state_sha256=digest(args.annual/'annual-state.npz'),
       monthly_master_sha256=digest(args.monthly/'master-workspace.json'),
       tools={p.name:digest(p) for p in tools.glob('*.py')},
       packages={name:version(name) for name in ['numpy','scipy','pypsa','linopy','highspy']})
    with driver_lock(args.output/'prepare.lock'):
        manifest=args.output/'preparation-manifest.json'
        if manifest.exists() and json.loads(manifest.read_text())!=signature:
            raise ValueError('Frozen support-transfer provenance changed')
        save(manifest,signature);verified=[]
        try:
            for month in range(1,13):
                if digest(args.input)!=source or digest(args.annual/'verified.json')!=annual_hash or digest(args.annual/'annual-state.npz')!=signature['annual_state_sha256'] or digest(args.monthly/'master-workspace.json')!=signature['monthly_master_sha256'] or any(digest(tools/k)!=v for k,v in signature['tools'].items()) or any(version(k)!=v for k,v in signature['packages'].items()):
                    raise ValueError('Frozen source/state/tools/packages changed')
                folder=args.output/f'{month:02d}'
                command=[]
                for name in ['input','monthly','calendar','warm','annual']:command+=['--'+name,str(getattr(args,name))]
                if not folder.exists():
                    save(args.output/'status.json',dict(status='transferring_monthly_duals',pid=os.getpid(),month=month,verified_months=len(verified)))
                    subprocess.run([sys.executable,str(tools/'audit_submonthly_dual_support.py'),*command,'--output',str(folder),'--month',str(month)],check=True)
                if not (folder/'independent-replay.json').exists():
                    subprocess.run([sys.executable,str(tools/'replay_submonthly_dual_witness.py'),*command,'--support',str(folder)],check=True)
                receipt=verify(folder,month,source)
                if receipt['annual_primal_audit_sha256']!=annual_hash or receipt['parent_receipt_sha256']!=digest(args.monthly/'warm-audit'/f'{month:02d}.json'):
                    raise ValueError('Support anchor changed')
                for row in receipt['rows']:
                    if row['block_sha256']!=digest(args.calendar/f"{row['index']:02d}"/'block.npz') or row['primal_sha256']!=digest(args.warm/f'{month:02d}'/f"{row['index']:02d}-primal.npz"):
                        raise ValueError('Support source block/primal changed')
                verified.append(dict(month=month,receipt_sha256=digest(folder/'verified.json'),replay_sha256=digest(folder/'independent-replay.json')))
            save(args.output/'verified-months.json',dict(input_sha256=source,annual_primal_audit_sha256=annual_hash,rows=verified,
                 scope='Independently replayed supports only; annual master adoption, optimisation gap and empirical/investment gates remain required.'))
            save(args.output/'status.json',dict(status='transferred_support_calendar_verified',pid=os.getpid(),verified_months=12))
        except Exception as error:
            save(args.output/'status.json',dict(status='failed_requires_review',pid=os.getpid(),verified_months=len(verified),error_type=type(error).__name__))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','monthly','calendar','warm','annual','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    for name in ['input','monthly','calendar','warm','annual','output']:setattr(args,name,getattr(args,name).resolve())
    run(args)
