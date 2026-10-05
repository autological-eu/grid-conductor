"""Check linked native blocks against a monolithic LP by eliminating internal SOC."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
from scipy import sparse
from monthly_dispatch import digest, save
from pypsa_storage_blocks import block


def keys(labels, names):
    result={}
    for name in names:
        for coordinates,label in labels[name].labels.to_series().items():
            if int(label)<0:continue
            coordinates=coordinates if isinstance(coordinates,tuple) else (coordinates,)
            result[int(label)]=(name,*map(str,coordinates))
    return result


def layout(network,snapshots):
    n=network.copy();n.set_snapshots(snapshots)
    n.storage_units['cyclic_state_of_charge']=False
    n.storage_units['cyclic_state_of_charge_per_period']=False
    n.storage_units['state_of_charge_initial']=0.
    model=n.optimize.create_model(include_objective_constant=False);mat=model.matrices
    columns=keys(model.variables,list(model.variables));rows=keys(model.constraints,list(model.constraints))
    sense=np.asarray(mat.sense);eq=sense=='=';less=sense=='<';greater=sense=='>'
    if not np.all(eq|less|greater):raise ValueError('Unsupported native constraint sense')
    labels=model.variables['StorageUnit-state_of_charge'].labels.sel(snapshot=snapshots[-1]).values
    positions={int(label):i for i,label in enumerate(mat.vlabels)}
    return dict(columns=[columns[int(label)] for label in mat.vlabels],
                eq_keys=[rows[int(label)] for label in np.asarray(mat.clabels)[eq]],
                ub_keys=[rows[int(label)] for label in np.r_[np.asarray(mat.clabels)[less],np.asarray(mat.clabels)[greater]]],
                equality=mat.A.tocsr()[eq],rhs=np.asarray(mat.b)[eq],
                inequality=sparse.vstack([mat.A.tocsr()[less],-mat.A.tocsr()[greater]],format='csr'),
                limit=np.r_[np.asarray(mat.b)[less],-np.asarray(mat.b)[greater]],
                cost=np.asarray(mat.c),bounds=list(zip(mat.lb,mat.ub)),
                terminal_columns=[positions[int(label)] for label in labels])


def permutation(actual,expected):
    if len(set(actual))!=len(actual) or len(set(expected))!=len(expected) or set(actual)!=set(expected):
        raise ValueError('Native labels do not form identical unique domains')
    lookup={key:i for i,key in enumerate(actual)}
    return np.array([lookup[key] for key in expected],dtype=int)


def difference(left,right):
    if left.shape!=right.shape:raise ValueError('Coefficient shapes differ')
    delta=sparse.csr_matrix(left)-sparse.csr_matrix(right)
    return float(np.max(abs(delta.data),initial=0.))


def compare(network,snapshots,split):
    if not 0<split<len(snapshots):raise ValueError('Two nonempty chronological parts required')
    times=[snapshots[:split],snapshots[split:]];ns=len(network.storage_units)
    expected=layout(network,snapshots);layouts=[layout(network,t) for t in times]
    parts=[block(network,t,i,2) for i,t in enumerate(times)]
    widths=[len(b.cost) for b in parts];nx=sum(widths)
    columns=layouts[0]['columns']+layouts[1]['columns'];col_order=permutation(columns,expected['columns'])
    # Substitute the shared middle inventory with block 0's terminal SOC.
    internal=sparse.lil_matrix((3*ns,nx))
    for j,column in enumerate(layouts[0]['terminal_columns']):internal[ns+j,column]=1.
    external=sparse.lil_matrix((3*ns,2*ns))
    for j in range(ns):external[j,j]=1.;external[2*ns+j,ns+j]=1.
    internal=internal.tocsr();external=external.tocsr()
    local_eq=sparse.block_diag([parts[0].equality[:-ns],parts[1].equality],format='csr')
    coupling_eq=sparse.vstack([parts[0].coupling[:-ns],parts[1].coupling],format='csr')
    eq=(local_eq+coupling_eq@internal)[:,col_order];eq_external=coupling_eq@external
    terminal_keys=[('boundary-terminal',str(key)) for key in network.storage_units.index]
    eq_order=permutation(layouts[0]['eq_keys']+layouts[1]['eq_keys']+terminal_keys,expected['eq_keys']+terminal_keys)
    eq=eq[eq_order];eq_external=eq_external[eq_order]
    rhs=np.r_[parts[0].rhs[:-ns],parts[1].rhs][eq_order]
    terminal=sparse.lil_matrix((ns,len(expected['cost'])))
    for j,column in enumerate(expected['terminal_columns']):terminal[j,column]=1.
    expected_eq=sparse.vstack([expected['equality'],terminal],format='csr')
    expected_external=sparse.lil_matrix((expected_eq.shape[0],2*ns))
    # Native energy-balance labels identify initial-inventory rows independently.
    lookup={key:i for i,key in enumerate(expected['eq_keys'])}
    for j,key in enumerate(network.storage_units.index):
        row=lookup[('StorageUnit-energy_balance',str(snapshots[0]),str(key))]
        retention=(1-float(network.storage_units.loc[key,'standing_loss']))**float(network.snapshot_weightings.stores.loc[snapshots[0]])
        if not bool(network.storage_units.loc[key,'cyclic_state_of_charge']):retention=1.
        expected_external[row,j]=retention;expected_external[len(expected['rhs'])+j,ns+j]=-1.
    ub=sparse.block_diag([b.inequality for b in parts],format='csr')
    ub_c=sparse.vstack([b.inequality_coupling for b in parts],format='csr')
    ub=(ub+ub_c@internal)[:,col_order];ub_external=ub_c@external
    ub_order=permutation(layouts[0]['ub_keys']+layouts[1]['ub_keys'],expected['ub_keys'])
    ub=ub[ub_order];ub_external=ub_external[ub_order]
    limit=np.r_[parts[0].limit,parts[1].limit][ub_order]
    cost=np.r_[parts[0].cost,parts[1].cost][col_order]
    bounds=np.asarray(parts[0].bounds+parts[1].bounds,dtype=float)[col_order]
    checks=dict(equality_coefficients=difference(eq,expected_eq),
                equality_boundary_coefficients=difference(eq_external,expected_external),
                equality_rhs=float(np.max(abs(rhs-np.r_[expected['rhs'],np.zeros(ns)]),initial=0.)),
                inequality_coefficients=difference(ub,expected['inequality']),
                inequality_boundary_coefficients=difference(ub_external,sparse.csr_matrix(ub_external.shape)),
                inequality_rhs=float(np.max(abs(limit-expected['limit']),initial=0.)),
                objective_coefficients=float(np.max(abs(cost-expected['cost']),initial=0.)))
    if not np.array_equal(bounds,np.asarray(expected['bounds'],dtype=float),equal_nan=True):
        raise ValueError('Native bounds differ after variable permutation')
    if max(checks.values())>1e-12:raise ValueError(f'Linked/monolithic coefficients differ: {checks}')
    return dict(status='coefficient_equivalence_passed',hours=len(snapshots),parts=[len(t) for t in times],
                storage_units=ns,variables=len(cost),equality_rows=eq.shape[0],inequality_rows=ub.shape[0],
                coefficient_tolerance=1e-12,maximum_differences=checks,bounds_identical=True,
                scope='Two-block conditional coefficient identity only; no dispatch solve, annual convergence or empirical validation.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--worker',action='store_true')
    args=parser.parse_args()
    if not args.worker:
        from audit_annual_warm_state import guard_reason,terminate_worker
        args.output.parent.mkdir(parents=True,exist_ok=True)
        if args.output.exists():raise ValueError('Existing equivalence evidence must not be overwritten')
        status=args.output.with_suffix('.status.json')
        with args.output.with_suffix('.log').open('w') as log:
            child=subprocess.Popen([sys.executable,__file__,'--input',str(args.input.resolve()),'--output',str(args.output.resolve()),'--worker'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            save(status,dict(status='auditing_equivalence',pid=child.pid));peak=0;started=time.monotonic()
            while child.poll() is None:
                try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
                except FileNotFoundError:rss=0
                peak=max(peak,rss);reason=guard_reason(time.monotonic()-started,rss,6.,300.)
                if reason:terminate_worker(child);save(status,dict(status=reason,peak_rss_bytes=peak));sys.exit(1)
                time.sleep(1)
            save(status,dict(status='coefficient_equivalence_passed' if child.returncode==0 else 'failed',returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started))
            sys.exit(child.returncode)
    import pypsa
    from prepare_annual_coordination import validate_calendar
    n=pypsa.Network(args.input);validate_calendar(n,2025)
    n.global_constraints.drop(n.global_constraints.index,inplace=True)
    report=compare(n,n.snapshots[:48],24)
    report.update(input_sha256=digest(args.input),producer_sha256=digest(Path(__file__)),
                  dependencies={name:digest(Path(__file__).with_name(name)) for name in ['pypsa_storage_blocks.py','prepare_annual_coordination.py']})
    args.output.parent.mkdir(parents=True,exist_ok=True);save(args.output,report)
    print('48h native coefficient equivalence passed; no annual result accepted.')
