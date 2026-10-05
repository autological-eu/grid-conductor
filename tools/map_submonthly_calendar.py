"""Finite locked native-identity mapping of an already replayed annual witness.

This recreates labels, not dispatch; no annual optimum or market validation.
"""
import argparse,fcntl,json,os,subprocess,sys
from pathlib import Path
from importlib.metadata import version
import numpy as np
from monthly_dispatch import digest,save

FILES=['map_submonthly_witness.py','disk_storage_blocks.py','submonthly_objective_donor.py',
    'prepare_annual_coordination.py','monthly_dispatch.py','submonthly_inventory_driver.py']


def verify(folder,row,source,annual_hash,mapper_hash):
    status=json.loads((folder/'status.json').read_text());record=json.loads((folder/'verified.json').read_text())
    if (status['status']!='mapping_complete' or status['returncode']!=0
            or record['status']!='native_witness_identity_mapping_verified_not_market_validation'
            or any(record[k]!=v for k,v in row.items()) or record['input_sha256']!=source
            or record['annual_replay_sha256']!=annual_hash or record['producer_sha256']!=mapper_hash
            or record['quantities_sha256']!=digest(folder/'quantities.npz')):
        raise ValueError('Mapped native quantities or source/calendar identity differ')
    tools=Path(__file__).parent
    for name,value in record['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Mapped-quantity implementation changed')
    expected_times=np.datetime64('2025-01-01T00:00','ns')+np.arange(row['start_hour'],row['end_hour_exclusive']).astype('timedelta64[h]')
    if not np.array_equal(np.array(record['snapshots'],dtype='datetime64[ns]'),expected_times):
        raise ValueError('Mapped native timestamps differ from exact UTC hourly calendar')
    with np.load(folder/'quantities.npz',allow_pickle=False) as data:
        expected={'generation_mw':len(record['generator_ids']),'nodal_price_eur_per_mwh':len(record['bus_ids']),
            'storage_charge_mw':len(record['storage_ids']),'storage_discharge_mw':len(record['storage_ids']),
            'storage_soc_mwh':len(record['storage_ids'])}
        if set(data.files)!=set(expected):raise ValueError('Complete mapped generation/price/storage quantities required')
        for name,count in expected.items():
            if data[name].shape!=(row['hours'],count) or not np.isfinite(data[name]).all():raise ValueError('Invalid mapped native quantity grid')
    return record


def run(args):
    args.output.mkdir(parents=True,exist_ok=True);tools=Path(__file__).parent
    domain_path=args.workspace/'master-workspace.json';domain=json.loads(domain_path.read_text())
    annual_path=args.annual/'annual-replay.json'
    if domain['year']!=2025 or domain['input_sha256']!=digest(args.input):raise ValueError('Source-matched 2025 inventory domain required')
    from submonthly_inventory_driver import verify_annual
    verify_annual(args.annual,domain)
    signature=dict(input_sha256=domain['input_sha256'],inventory_domain_sha256=digest(domain_path),
        annual_replay_sha256=digest(annual_path),producer_sha256=digest(Path(__file__)),
        dependencies={name:digest(tools/name) for name in FILES},
        packages={name:version(name) for name in ['numpy','scipy','pandas','pypsa','linopy']})
    with (args.output/'mapping.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        manifest=args.output/'manifest.json'
        if manifest.exists() and json.loads(manifest.read_text())!=signature:raise ValueError('Frozen mapping source/code/settings changed; preserve checkpoints')
        save(manifest,signature)
        def frozen():
            if digest(args.input)!=signature['input_sha256'] or digest(domain_path)!=signature['inventory_domain_sha256'] or digest(annual_path)!=signature['annual_replay_sha256']:
                raise ValueError('Active mapping source changed')
            if digest(Path(__file__))!=signature['producer_sha256'] or any(digest(tools/name)!=value for name,value in signature['dependencies'].items()):
                raise ValueError('Active mapping calculation changed')
            if any(version(name)!=value for name,value in signature['packages'].items()):raise ValueError('Active mapping environment changed')
        checked=[];position=0;identity=None
        try:
            for row in domain['blocks']:
                frozen()
                if row['index']!=len(checked) or row['start_hour']!=position or row['end_hour_exclusive']-position!=row['hours']:
                    raise ValueError('Exact chronological native mapping required')
                folder=args.output/f"{row['index']:02d}"
                if not folder.exists():
                    save(args.output/'status.json',dict(status='mapping_calendar_block',pid=os.getpid(),index=row['index'],verified_blocks=len(checked)))
                    command=[sys.executable,str(tools/'map_submonthly_witness.py')]
                    for name in ('input','workspace','calendar','annual'):command.extend(['--'+name,str(getattr(args,name))])
                    command.extend(['--output',str(folder),'--index',str(row['index'])])
                    subprocess.run(command,check=True)
                # Partial/failed folders require explicit review, never a replacement job.
                record=verify(folder,row,signature['input_sha256'],signature['annual_replay_sha256'],signature['dependencies']['map_submonthly_witness.py'])
                current={k:record[k] for k in ('generator_ids','bus_ids','storage_ids','buses_without_price_rows','generators','storage_units')}
                if identity is None:identity=current
                elif current!=identity:raise ValueError('Native asset identity changes across mapped calendar')
                checked.append(dict(**row,receipt_sha256=digest(folder/'verified.json'),quantities_sha256=record['quantities_sha256']))
                position=row['end_hour_exclusive']
                save(args.output/'status.json',dict(status='mapped_block_verified',pid=os.getpid(),index=row['index'],verified_blocks=len(checked)))
            if len(checked)!=59 or position!=8760:raise ValueError('Complete 2025 native mapping required')
            save(args.output/'verified-calendar.json',dict(status='annual_native_witness_mapping_complete_not_validation',year=2025,hours=position,
                input_sha256=signature['input_sha256'],annual_replay_sha256=signature['annual_replay_sha256'],manifest_sha256=digest(manifest),
                **identity,rows=checked,limitations=['Conditional fixed-inventory nodal duals, not converged annual market prices.',
                'Country identities are not verified bidding-zone identities; absent price rows remain unmapped.',
                'Storage charge/discharge stays separate; dispatch never becomes original renewable availability.',
                'No empirical acceptance, avoided emissions or investment benefit inferred.']))
            save(args.output/'status.json',dict(status='mapping_complete_not_validation',verified_blocks=len(checked),hours=position))
        except Exception as error:
            save(args.output/'status.json',dict(status='failed_requires_review',pid=os.getpid(),verified_blocks=len(checked),error_type=type(error).__name__));raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('input','workspace','calendar','annual','output'):p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
