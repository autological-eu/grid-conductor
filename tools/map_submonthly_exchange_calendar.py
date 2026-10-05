"""Locked chronological branch mapping of saved annual witnesses, without solving."""
import argparse,fcntl,json,os,subprocess,sys
from pathlib import Path
from importlib.metadata import version
import numpy as np
from monthly_dispatch import digest,save
from map_submonthly_exchanges import country_injections,terminals

FILES=['map_submonthly_exchanges.py','map_submonthly_witness.py','disk_storage_blocks.py',
    'submonthly_objective_donor.py','prepare_annual_coordination.py','submonthly_inventory_driver.py','monthly_dispatch.py']


def verify(folder,row,source,annual_hash,mapper_hash):
    status=json.loads((folder/'status.json').read_text());r=json.loads((folder/'verified.json').read_text())
    if (status['status']!='mapping_complete' or status['returncode']!=0
            or r['status']!='native_branch_identity_diagnostic_not_exchange_validation'
            or any(r[k]!=v for k,v in row.items()) or r['input_sha256']!=source
            or r['annual_replay_sha256']!=annual_hash or r['producer_sha256']!=mapper_hash
            or r['quantities_sha256']!=digest(folder/'quantities.npz')):
        raise ValueError('Source/calendar/branch mapping differs')
    for name,value in r['dependencies'].items():
        if digest(Path(__file__).parent/name)!=value:raise ValueError('Mapping implementation changed')
    times=np.datetime64('2025-01-01T00:00','ns')+np.arange(row['start_hour'],row['end_hour_exclusive']).astype('timedelta64[h]')
    if not np.array_equal(np.array(r['snapshots'],dtype='datetime64[ns]'),times):raise ValueError('Exact UTC chronology required')
    identities=[(a['kind'],a['id']) for a in r['assets']]
    if len(set(identities))!=len(identities) or any(k not in ('line','link') for k,_ in identities):
        raise ValueError('Unique supported branch identities required')
    with np.load(folder/'quantities.npz',allow_pickle=False) as data:q={k:data[k] for k in data.files}
    keys={'country_net_export_mw'};country={}
    for kind in ('line','link'):
        assets=[a for a in r['assets'] if a['kind']==kind]
        if not assets:continue
        keys.update((kind+'_p0_mw',kind+'_p1_mw'))
        p0=q[kind+'_p0_mw'];p1=q[kind+'_p1_mw']
        if p0.shape!=(row['hours'],len(assets)) or p1.shape!=p0.shape:raise ValueError('Branch grid differs')
        _,expected=terminals(p0,[a['efficiency'] for a in assets])
        if not np.isfinite(p1).all() or np.max(abs(p1-expected),initial=0.)>1e-7:raise ValueError('Native terminal algebra differs')
        for name,v in country_injections(assets,p0,p1).items():country.setdefault(name,np.zeros(row['hours']));country[name]+=v
    if set(q)!=keys or r['countries']!=sorted(country):raise ValueError('Complete terminal/country inventory required')
    expected=np.column_stack([country[c] for c in r['countries']]);export=q['country_net_export_mw']
    if export.shape!=expected.shape or not np.isfinite(export).all() or np.max(abs(export-expected),initial=0.)>1e-7:
        raise ValueError('Cross-country terminal accounting differs')
    return r


def run(args):
    args.output.mkdir(parents=True,exist_ok=True);tools=Path(__file__).parent
    domain_path=args.workspace/'master-workspace.json';domain=json.loads(domain_path.read_text())
    annual_path=args.annual/'annual-replay.json'
    from submonthly_inventory_driver import verify_annual
    if domain['input_sha256']!=digest(args.input):raise ValueError('Original source differs')
    verify_annual(args.annual,domain)
    signature=dict(input_sha256=domain['input_sha256'],domain_sha256=digest(domain_path),
        annual_replay_sha256=digest(annual_path),producer_sha256=digest(Path(__file__)),
        dependencies={name:digest(tools/name) for name in FILES},
        packages={name:version(name) for name in ['numpy','scipy','pandas','pypsa','linopy']})
    with (args.output/'mapping.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        args.mapping_lock_owned=True
        manifest=args.output/'manifest.json'
        if manifest.exists() and json.loads(manifest.read_text())!=signature:raise ValueError('Frozen mapping signature changed; preserve evidence')
        save(manifest,signature);rows=[];position=0
        for expected in domain['blocks']:
            if digest(Path(__file__))!=signature['producer_sha256']:raise ValueError('Mapping supervisor changed')
            for name,value in signature['packages'].items():
                if version(name)!=value:raise ValueError('Mapping environment changed')
            if digest(args.input)!=signature['input_sha256'] or digest(domain_path)!=signature['domain_sha256'] or digest(annual_path)!=signature['annual_replay_sha256']:
                raise ValueError('Source/domain/annual chain changed')
            for name,value in signature['dependencies'].items():
                if digest(tools/name)!=value:raise ValueError('Frozen mapping code changed')
            if expected['start_hour']!=position:raise ValueError('Incomplete chronology')
            target=args.output/f"{expected['index']:02d}"
            save(args.output/'status.json',dict(status='mapping',pid=os.getpid(),index=expected['index'],complete_blocks=len(rows),mapped_hours=position))
            if not target.exists():
                subprocess.run([sys.executable,str(tools/'map_submonthly_exchanges.py'),'--input',str(args.input),
                    '--workspace',str(args.workspace),'--calendar',str(args.calendar),'--annual',str(args.annual),
                    '--output',str(target),'--index',str(expected['index'])],check=True)
            row={k:expected[k] for k in ('index','month','start_hour','end_hour_exclusive','hours')}
            verify(target,row,signature['input_sha256'],signature['annual_replay_sha256'],signature['dependencies']['map_submonthly_exchanges.py'])
            rows.append(dict(**row,receipt_sha256=digest(target/'verified.json'),quantities_sha256=digest(target/'quantities.npz')))
            position=expected['end_hour_exclusive']
        if len(rows)!=59 or position!=8760:raise ValueError('Complete year required')
        save(args.output/'verified-calendar.json',dict(status='annual_native_branch_mapping_complete_not_exchange_validation',
            year=2025,hours=8760,input_sha256=signature['input_sha256'],annual_replay_sha256=signature['annual_replay_sha256'],
            manifest_sha256=digest(manifest),rows=rows))
        save(args.output/'status.json',dict(status='mapping_complete',complete_blocks=59,mapped_hours=8760))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('input','workspace','calendar','annual','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();args.mapping_lock_owned=False
    try:run(args)
    except Exception:
        if args.mapping_lock_owned:save(args.output/'status.json',dict(status='failed_requires_review'))
        raise
