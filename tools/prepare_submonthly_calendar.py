"""Resume guarded submonthly coefficient preparation; no annual solve or state reset."""
import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from annual_inventory_driver import driver_lock
from prepare_submonthly_blocks import partitions
from monthly_dispatch import digest,save

DEPENDENCIES=['prepare_submonthly_blocks.py','pypsa_storage_blocks.py','prepare_annual_coordination.py',
              'disk_storage_blocks.py','audit_submonthly_equivalence.py','audit_annual_warm_state.py',
              'annual_inventory_driver.py','monthly_dispatch.py']


def verify_block(folder,row,source_hash,count):
    status=json.loads((folder/'status.json').read_text())
    data=json.loads((folder/'block.json').read_text())
    if status['status']!='prepared_requires_equivalence_audit' or any(data.get(k)!=v for k,v in row.items()):
        raise ValueError('Submonthly preparation status/calendar mismatch')
    if data['input_sha256']!=source_hash or data['block_count']!=count or data['year']!=2025:
        raise ValueError('Submonthly source/layout mismatch')
    if data['block_sha256']!=digest(folder/'block.npz') or data['producer_sha256']!=digest(Path(__file__).with_name('prepare_submonthly_blocks.py')):
        raise ValueError('Submonthly block/producer fingerprint mismatch')
    if data['shared_variables']!=(count+1)*len(data['storage_ids']):raise ValueError('Shared inventory dimension mismatch')
    if set(data['dependencies'])!={'pypsa_storage_blocks.py','prepare_annual_coordination.py','disk_storage_blocks.py'}:
        raise ValueError('Incomplete exporter dependency fingerprints')
    for name,value in data['dependencies'].items():
        if digest(Path(__file__).with_name(name))!=value:raise ValueError('Submonthly exporter dependency changed')
    return data


def run(args):
    args.output.mkdir(parents=True,exist_ok=True);tools=Path(__file__).resolve().parent
    rows=partitions(2025,168);source_hash=digest(args.input)
    proof=json.loads(args.equivalence.read_text())
    if proof['status']!='coefficient_equivalence_passed' or proof['input_sha256']!=source_hash or not proof['bounds_identical'] or max(proof['maximum_differences'].values())>1e-12:
        raise ValueError('Source-matched coefficient audit required')
    if proof['producer_sha256']!=digest(tools/'audit_submonthly_equivalence.py'):
        raise ValueError('Equivalence audit producer changed')
    signature=dict(input_sha256=source_hash,equivalence_sha256=digest(args.equivalence),
                   producer_sha256=digest(Path(__file__)),dependencies={name:digest(tools/name) for name in DEPENDENCIES},
                   packages={name:version(name) for name in ['numpy','scipy','pandas','pypsa','linopy']},blocks=rows)
    manifest=args.output/'preparation-manifest.json';status=args.output/'status.json'
    with driver_lock(args.output/'prepare.lock'):
        if manifest.exists() and json.loads(manifest.read_text())!=signature:
            raise ValueError('Preparation source/code/versions changed; preserve old evidence')
        save(manifest,signature)
        def report(stage,**values):save(status,dict(status=stage,pid=os.getpid(),**values))
        verified=[]
        try:
            for row in rows:
                if digest(Path(__file__))!=signature['producer_sha256'] or digest(args.input)!=source_hash or digest(args.equivalence)!=signature['equivalence_sha256'] or any(digest(tools/name)!=value for name,value in signature['dependencies'].items()) or any(version(name)!=value for name,value in signature['packages'].items()):
                    raise ValueError('Frozen preparation inputs/code/versions changed')
                folder=args.output/f"{row['index']:02d}"
                if not folder.exists():
                    if shutil.disk_usage(args.output).free<2*2**30:raise RuntimeError('Less than 2 GiB free disk')
                    report('preparing_submonthly_calendar',index=row['index'],verified_blocks=len(verified))
                    subprocess.run([sys.executable,str(tools/'prepare_submonthly_blocks.py'),'--input',str(args.input),
                                    '--output',str(folder),'--index',str(row['index']),'--max-hours','168'],check=True)
                data=verify_block(folder,row,source_hash,len(rows))
                verified.append(dict(index=row['index'],block_sha256=data['block_sha256'],receipt_sha256=digest(folder/'block.json')))
                report('submonthly_block_verified',index=row['index'],verified_blocks=len(verified))
            save(args.output/'verified-blocks.json',dict(input_sha256=source_hash,rows=verified,storage_ids=data['storage_ids'],
                 scope='Coefficient artifacts verified only; linked annual workspace, dispatch and convergence remain required.'))
            report('submonthly_calendar_prepared',verified_blocks=len(verified),scope='No annual dispatch, upper bound or optimum accepted.')
        except Exception as error:
            report('failed_requires_review',verified_blocks=len(verified),error_type=type(error).__name__)
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--equivalence',type=Path,required=True);args=parser.parse_args()
    args.input=args.input.resolve();args.output=args.output.resolve();args.equivalence=args.equivalence.resolve();run(args)
