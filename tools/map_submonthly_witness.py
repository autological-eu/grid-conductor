"""Map replayed fixed-inventory dispatch witnesses to native asset identities.

Recreate labels only, never solve or infer renewable availability from dispatch.
Original coefficient and RHS identity is required before interpreting columns.
"""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
from scipy import sparse
from monthly_dispatch import digest,save


def same(a,b,name):
    if sparse.issparse(a) or sparse.issparse(b):
        a=sparse.csr_matrix(a);b=sparse.csr_matrix(b)
        if a.shape!=b.shape or np.max(abs((a-b).data),initial=0.)>1e-12:raise ValueError(name+' coefficients differ')
    else:
        a=np.asarray(a);b=np.asarray(b)
        if a.shape!=b.shape or not np.array_equal(a,b,equal_nan=True):raise ValueError(name+' values differ')


def native_model(network,snapshots):
    n=network.copy();n.set_snapshots(snapshots)
    n.global_constraints.drop(n.global_constraints.index,inplace=True)
    n.storage_units['cyclic_state_of_charge']=False
    n.storage_units['cyclic_state_of_charge_per_period']=False
    n.storage_units['state_of_charge_initial']=0.
    return n,n.optimize.create_model(include_objective_constant=False)


def verify_layout(model,block,ns):
    mat=model.matrices;A=mat.A.tocsr();b=np.asarray(mat.b);sense=np.asarray(mat.sense)
    eq=sense=='=';less=sense=='<';greater=sense=='>'
    if not np.all(eq|less|greater):raise ValueError('Unknown native constraint sense')
    same(mat.c,block.cost,'Objective')
    same(np.c_[mat.lb,mat.ub],np.asarray(block.bounds),'Variable bounds')
    native_eq=block.equality[:-ns] if ns else block.equality
    native_rhs=block.rhs[:-ns] if ns else block.rhs
    same(A[eq],native_eq,'Native equalities');same(b[eq],native_rhs,'Native equality RHS')
    same(sparse.vstack([A[less],-A[greater]],format='csr'),block.inequality,'Native inequalities')
    same(np.r_[b[less],-b[greater]],block.limit,'Native inequality RHS')
    return np.asarray(mat.vlabels),np.asarray(mat.clabels)[eq]


def values(labels,ids,vector):
    labels=np.asarray(labels);ids=np.asarray(ids)
    if labels.dtype.kind not in 'iu' or ids.dtype.kind not in 'iu' or len(np.unique(ids))!=len(ids):
        raise ValueError('Unique integer native identities required')
    positions={int(label):i for i,label in enumerate(ids)}
    if any(int(label) not in positions for label in labels.flat):raise ValueError('Missing native identity; no zero substitution')
    result=np.asarray(vector)[np.array([positions[int(label)] for label in labels.flat])].reshape(labels.shape)
    if not np.isfinite(result).all():raise ValueError('Nonfinite witness quantity')
    return result


def quantities(network,model,block,arrays):
    if not (network.generators.sign==1.).all():raise ValueError('Nonunit generator sign needs explicit injection/unit accounting')
    cols,rows=verify_layout(model,block,len(network.storage_units))
    p=model.variables['Generator-p'].labels.transpose('snapshot','name')
    balance=model.constraints['Bus-nodal_balance'].labels.transpose('snapshot','name')
    generation=values(p.values,cols,arrays['primal'])
    prices=values(balance.values,rows,arrays['equality_duals'])/network.snapshot_weightings.objective.to_numpy()[:,None]
    if (generation < -1e-7).any():raise ValueError('Unexpected negative generator output')
    return dict(snapshots=[str(v) for v in p.coords['snapshot'].values],
        generator_ids=p.coords['name'].values.tolist(),bus_ids=balance.coords['name'].values.tolist(),
        generation_mw=generation,nodal_price_eur_per_mwh=prices)


def worker(args):
    import pypsa
    from disk_storage_blocks import load_block
    from submonthly_objective_donor import load
    from prepare_annual_coordination import validate_calendar
    domain_path=args.workspace/'master-workspace.json';domain=json.loads(domain_path.read_text())
    annual_path=args.annual/'annual-replay.json';annual=json.loads(annual_path.read_text());source=digest(args.input)
    if (annual['status']!='independently_replayed_economic_annual_feasible' or annual['input_sha256']!=source
            or domain['input_sha256']!=source or annual['hours']!=8760 or annual['blocks']!=59):
        raise ValueError('Verified linked annual economic witness required')
    from submonthly_inventory_driver import verify_annual
    verify_annual(args.annual,domain)
    row=domain['blocks'][args.index];folder=args.annual/f'{args.index:02d}'
    load(folder/'independent-replay.json',domain)
    proof=json.loads((folder/'independent-replay.json').read_text())
    annual_row=annual['rows'][args.index]
    if (annual_row['index']!=args.index or annual_row['replay_sha256']!=digest(folder/'independent-replay.json')
            or proof['master_sha256']!=annual['master_sha256']):raise ValueError('Annual block witness linkage differs')
    path=args.calendar/f'{args.index:02d}'/'block.npz'
    if digest(path)!=domain['block_sha256'][args.index]:raise ValueError('Prepared native coefficients changed')
    n=pypsa.Network(args.input);validate_calendar(n,2025)
    n,model=native_model(n,n.snapshots[row['start_hour']:row['end_hour_exclusive']])
    block=load_block(path)
    with np.load(folder/'witness.npz',allow_pickle=False) as data:arrays={k:data[k].copy() for k in ['primal','equality_duals']}
    q=quantities(n,model,block,arrays)
    generation=q.pop('generation_mw');prices=q.pop('nodal_price_eur_per_mwh')
    out=args.output/'quantities.npz';np.savez_compressed(out,generation_mw=generation,nodal_price_eur_per_mwh=prices)
    assets=[]
    for gid in q['generator_ids']:
        g=n.generators.loc[gid];assets.append(dict(id=gid,bus=str(g.bus),country=str(n.buses.loc[g.bus,'country']),carrier=str(g.carrier)))
    tools=Path(__file__).parent
    save(args.output/'verified.json',dict(status='native_witness_identity_mapping_verified_not_market_validation',
        **row,input_sha256=source,annual_replay_sha256=digest(annual_path),block_sha256=digest(path),
        witness_sha256=digest(folder/'witness.npz'),replay_sha256=digest(folder/'independent-replay.json'),
        quantities_sha256=digest(out),**q,generators=assets,
        generator_energy_mwh=float(np.sum(generation)),
        producer_sha256=digest(Path(__file__)),dependencies={name:digest(tools/name) for name in
            ['disk_storage_blocks.py','submonthly_objective_donor.py','prepare_annual_coordination.py','monthly_dispatch.py','submonthly_inventory_driver.py']},
        limitations=['Fixed-boundary conditional nodal duals; not converged annual market prices.',
            'Native bus identity is not verified bidding-zone assignment; aggregation requires geographic gates.',
            'Generation dispatch remains output, never original renewable availability or a lifecycle factor.',
            'No fitted costs, empirical acceptance, annual optimum or investment benefits inferred.']))


def run(args):
    from audit_annual_warm_state import terminate_worker
    if args.output.exists():raise ValueError('Preserve existing mapping evidence; review failures explicitly')
    args.output.mkdir(parents=True)
    command=[sys.executable,__file__]
    for name in ('input','workspace','calendar','annual','output','index'):command.extend(['--'+name,str(getattr(args,name))])
    command.append('--worker');started=time.monotonic();peak=0
    with (args.output/'worker.log').open('w') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
            env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'})
        save(args.output/'status.json',dict(status='mapping_original_native_labels',pid=child.pid,index=args.index))
        while child.poll() is None:
            try:rss=sum(int(l.split()[1])*1024 for l in Path(f'/proc/{child.pid}/status').read_text().splitlines() if l.startswith('VmRSS:'))
            except FileNotFoundError:rss=0
            peak=max(peak,rss)
            if rss>2*2**30 or time.monotonic()-started>180:
                terminate_worker(child);save(args.output/'status.json',dict(status='resource_guard_requires_review',peak_rss_bytes=peak));return
            time.sleep(1)
        save(args.output/'status.json',dict(status='mapping_complete' if child.returncode==0 else 'failed_requires_review',
            returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started))
        if child.returncode:raise RuntimeError('Mapping worker failed; inspect preserved local evidence')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('input','workspace','calendar','annual','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--index',type=int,required=True);p.add_argument('--worker',action='store_true');args=p.parse_args()
    if not 0<=args.index<59:p.error('Invalid annual block index')
    worker(args) if args.worker else run(args)
