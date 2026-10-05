"""Locked, sequential warm-primal restriction with frozen provenance.

Completion is twelve restricted monthly witnesses, not an annual linkage audit.
"""
import argparse,json,os,subprocess,sys
from pathlib import Path
from annual_inventory_driver import driver_lock
from monthly_dispatch import digest,save


def verify(folder,month,source_hash):
    receipt=json.loads((folder/'verified.json').read_text())
    status=json.loads((folder/'status.json').read_text())
    if status['status']!='restricted_witness_complete' or receipt['status']!='restricted_monthly_primal_verified' or receipt['month']!=month or receipt['input_sha256']!=source_hash:
        raise ValueError('Incomplete or mismatched restricted monthly witness')
    if receipt['producer_sha256']!=digest(Path(__file__).with_name('prepare_submonthly_warm_witness.py')):
        raise ValueError('Restricted witness producer changed')
    for name,value in receipt['dependencies'].items():
        if digest(Path(__file__).with_name(name))!=value:raise ValueError('Restriction dependency changed')
    if digest(folder/'boundary-state.npz')!=receipt['boundary_state_sha256']:
        raise ValueError('Restricted inventory content changed')
    for row in receipt['rows']:
        if digest(folder/f"{row['index']:02d}-primal.npz")!=row['primal_sha256']:
            raise ValueError('Restricted primal changed')
    return receipt


def run(args):
    args.output.mkdir(parents=True,exist_ok=True);tools=Path(__file__).parent
    # Freeze every local Python module: the preparer must fail closed if any
    # research implementation changes during a long unattended pass.
    source_hash=digest(args.input)
    signature=dict(input_sha256=source_hash,monthly_master_sha256=digest(args.monthly/'master-workspace.json'),
                   calendar_manifest_sha256=digest(args.calendar/'preparation-manifest.json'),
                   calendar_verified_sha256=digest(args.calendar/'verified-blocks.json'),
                   tools={p.name:digest(p) for p in tools.glob('*.py')})
    with driver_lock(args.output/'prepare.lock'):
        manifest=args.output/'preparation-manifest.json'
        if manifest.exists() and json.loads(manifest.read_text())!=signature:
            raise ValueError('Frozen warm preparation provenance changed')
        save(manifest,signature);verified=[]
        try:
            for month in range(1,13):
                if digest(args.input)!=source_hash or any(digest(tools/k)!=v for k,v in signature['tools'].items()) or digest(args.monthly/'master-workspace.json')!=signature['monthly_master_sha256'] or digest(args.calendar/'preparation-manifest.json')!=signature['calendar_manifest_sha256'] or digest(args.calendar/'verified-blocks.json')!=signature['calendar_verified_sha256']:
                    raise ValueError('Frozen source/tools/workspace changed')
                folder=args.output/f'{month:02d}'
                if not folder.exists():
                    save(args.output/'status.json',dict(status='restricting_monthly_primal',pid=os.getpid(),month=month,verified_months=len(verified)))
                    subprocess.run([sys.executable,str(tools/'prepare_submonthly_warm_witness.py'),
                      '--input',str(args.input),'--monthly',str(args.monthly),'--calendar',str(args.calendar),
                      '--output',str(folder),'--month',str(month)],check=True)
                receipt=verify(folder,month,source_hash)
                if receipt['source_receipt_sha256']!=digest(args.monthly/'warm-audit'/f'{month:02d}.json') or receipt['source_witness_sha256']!=digest(args.monthly/'warm-audit'/f'{month:02d}-witness.npz'):
                    raise ValueError('Source monthly witness changed')
                for row in receipt['rows']:
                    if row['block_sha256']!=digest(args.calendar/f"{row['index']:02d}"/'block.npz'):
                        raise ValueError('Restricted target block changed')
                verified.append(dict(month=month,receipt_sha256=digest(folder/'verified.json')))
            save(args.output/'verified-months.json',dict(input_sha256=source_hash,rows=verified,
                 scope='Restricted monthly witnesses only; a separate global-state replay is required for annual linkage.'))
            save(args.output/'status.json',dict(status='restricted_monthly_calendar_complete',pid=os.getpid(),verified_months=12))
        except Exception as error:
            save(args.output/'status.json',dict(status='failed_requires_review',pid=os.getpid(),verified_months=len(verified),error_type=type(error).__name__))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','monthly','calendar','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    for name in ['input','monthly','calendar','output']:setattr(args,name,getattr(args,name).resolve())
    run(args)
