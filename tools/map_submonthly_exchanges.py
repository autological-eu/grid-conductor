"""Recover signed native branch terminal flows; no observed-exchange validation."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
from monthly_dispatch import digest,save
from map_submonthly_witness import native_model,verify_layout,values


def terminals(p0,efficiency):
    p0=np.asarray(p0,dtype=float);efficiency=np.asarray(efficiency,dtype=float)
    if p0.ndim!=2 or efficiency.shape!=(p0.shape[1],) or not np.isfinite(p0).all() or not np.isfinite(efficiency).all() or (efficiency<=0).any():
        raise ValueError('Finite branch time grid and positive native efficiencies required')
    return p0,-p0*efficiency[None,:]


def country_injections(assets,p0,p1):
    if p0.shape!=p1.shape or p0.shape[1]!=len(assets):raise ValueError('Matched terminal identities required')
    groups={}
    for i,asset in enumerate(assets):
        a,b=asset['country0'],asset['country1']
        if not a or not b:raise ValueError('Explicit country identities required')
        if a==b:continue
        for country,value in ((a,p0[:,i]),(b,p1[:,i])):
            groups.setdefault(country,np.zeros(p0.shape[0]));groups[country]+=value
    return groups


def worker(args):
    import pypsa
    from disk_storage_blocks import load_block
    from submonthly_objective_donor import load
    from prepare_annual_coordination import validate_calendar
    from submonthly_inventory_driver import verify_annual
    domain=json.loads((args.workspace/'master-workspace.json').read_text());source=digest(args.input)
    annual_path=args.annual/'annual-replay.json';annual=json.loads(annual_path.read_text())
    if domain['input_sha256']!=source or annual['input_sha256']!=source:raise ValueError('Source identity differs')
    verify_annual(args.annual,domain)
    row=domain['blocks'][args.index];folder=args.annual/f'{args.index:02d}'
    load(folder/'independent-replay.json',domain)
    if annual['rows'][args.index]['replay_sha256']!=digest(folder/'independent-replay.json'):
        raise ValueError('Annual block linkage differs')
    path=args.calendar/f'{args.index:02d}'/'block.npz'
    if digest(path)!=domain['block_sha256'][args.index]:raise ValueError('Prepared coefficients changed')
    n=pypsa.Network(args.input);validate_calendar(n,2025)
    n,model=native_model(n,n.snapshots[row['start_hour']:row['end_hour_exclusive']])
    cols,_=verify_layout(model,load_block(path),len(n.storage_units))
    with np.load(folder/'witness.npz',allow_pickle=False) as data:primal=data['primal'].copy()
    outputs={};assets=[];country={}
    for kind,frame,var in [('line',n.lines,'Line-s'),('link',n.links,'Link-p')]:
        if frame.empty:continue
        if kind=='link':
            if set(frame.carrier)!={'DC'}:raise ValueError('Non-DC links need explicit multiport accounting')
            if any((frame[c].fillna('')!='').any() for c in frame.columns if c.startswith('bus') and c not in ('bus0','bus1')):
                raise ValueError('Multiport links unsupported')
            if not n.links_t.efficiency.empty:raise ValueError('Dynamic link efficiency requires explicit interval mapping')
        labels=model.variables[var].labels.transpose('snapshot','name')
        ids=labels.coords['name'].values.tolist()
        if len(set(ids))!=len(ids) or set(ids)!=set(frame.index):raise ValueError('Incomplete branch identity')
        frame=frame.loc[ids]
        efficiency=frame.efficiency.to_numpy() if kind=='link' else np.ones(len(ids))
        p0,p1=terminals(values(labels.values,cols,primal),efficiency)
        records=[dict(id=str(sid),kind=kind,bus0=str(unit.bus0),bus1=str(unit.bus1),
            country0=str(n.buses.loc[unit.bus0,'country']),country1=str(n.buses.loc[unit.bus1,'country']),
            efficiency=float(efficiency[i])) for i,(sid,unit) in enumerate(frame.iterrows())]
        outputs[kind+'_p0_mw']=p0;outputs[kind+'_p1_mw']=p1;assets.extend(records)
        for name,v in country_injections(records,p0,p1).items():country.setdefault(name,np.zeros(len(n.snapshots)));country[name]+=v
    names=sorted(country);outputs['country_net_export_mw']=np.column_stack([country[c] for c in names])
    out=args.output/'quantities.npz';np.savez_compressed(out,**outputs)
    tools=Path(__file__).parent
    save(args.output/'verified.json',dict(status='native_branch_identity_diagnostic_not_exchange_validation',**row,
        input_sha256=source,annual_replay_sha256=digest(annual_path),witness_sha256=digest(folder/'witness.npz'),
        block_sha256=digest(path),quantities_sha256=digest(out),producer_sha256=digest(Path(__file__)),
        dependencies={name:digest(tools/name) for name in ['map_submonthly_witness.py','disk_storage_blocks.py','submonthly_objective_donor.py','prepare_annual_coordination.py','submonthly_inventory_driver.py','monthly_dispatch.py']},
        snapshots=[str(t) for t in n.snapshots],assets=assets,countries=names,
        units='MW; p0/p1 positive withdrawal at respective native terminal; country net export sums cross-country terminal withdrawals.',
        limitations=['Model-country grouping, not accepted bidding-zone exchanges.',
            'Signed native terminal accounting; reverse flows retained, no clipping or capacity inference.',
            'Native link efficiency algebra retained, not verified metered losses or scheduled exchanges.',
            'Fixed-inventory candidate 001; no annual optimum, empirical or investment validation.']))


def run(args):
    from audit_annual_warm_state import terminate_worker
    if args.output.exists():raise ValueError('Preserve previous pilot evidence')
    args.output.mkdir(parents=True)
    command=[sys.executable,__file__,'--worker']
    for name in ('input','workspace','calendar','annual','output','index'):command.extend(['--'+name,str(getattr(args,name))])
    started=time.monotonic();peak=0
    with (args.output/'worker.log').open('w') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
            env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'})
        save(args.output/'status.json',dict(status='mapping_native_branch_labels',pid=child.pid,index=args.index))
        while child.poll() is None:
            try:rss=sum(int(l.split()[1])*1024 for l in Path(f'/proc/{child.pid}/status').read_text().splitlines() if l.startswith('VmRSS:'))
            except FileNotFoundError:rss=0
            peak=max(peak,rss)
            if rss>2**30 or time.monotonic()-started>180:
                terminate_worker(child);save(args.output/'status.json',dict(status='resource_guard_requires_review',peak_rss_bytes=peak));return
            time.sleep(1)
        save(args.output/'status.json',dict(status='mapping_complete' if child.returncode==0 else 'failed_requires_review',
            returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started))
        if child.returncode:raise RuntimeError('Inspect preserved branch mapping failure')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('input','workspace','calendar','annual','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--index',type=int,required=True);p.add_argument('--worker',action='store_true');args=p.parse_args()
    if not 0<=args.index<59:p.error('Invalid annual block index')
    worker(args) if args.worker else run(args)
