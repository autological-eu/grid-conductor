"""Prepare explicit annual inventory domain for the verified 59-block layout."""
import argparse,json
from pathlib import Path
import numpy as np
import pypsa
from scipy import sparse
from monthly_dispatch import digest,save
from prepare_annual_coordination import validate_calendar
from prepare_submonthly_blocks import partitions
from prepare_submonthly_calendar import verify_block
from annual_inventory_workspace import boundaries,validate_warm
from inventory_reachability import envelope
from submonthly_inventory_mapping import boundary_positions
from disk_storage_blocks import load_block
from storage_objective_floor import nonnegative_objective_floor


def monthly_projection(storage_units,rows):
    positions=boundary_positions(rows);ns=storage_units
    if ns<1:raise ValueError('Positive storage count required')
    cols=np.concatenate([np.arange(position*ns,(position+1)*ns) for position in positions])
    return sparse.csr_matrix((np.ones(len(cols)),(np.arange(len(cols)),cols)),shape=(13*ns,(len(rows)+1)*ns))


def prepare(args):
    if args.output.exists():raise ValueError('Preserve existing workspace evidence')
    tools=Path(__file__).parent;source=digest(args.input)
    annual=json.loads((args.annual/'verified.json').read_text());calendar=json.loads((args.calendar/'verified-blocks.json').read_text())
    monthly=json.loads((args.monthly/'master-workspace.json').read_text())
    if annual['status']!='annual_restricted_primal_feasible' or any(d['input_sha256']!=source for d in [annual,calendar,monthly]) or annual['producer_sha256']!=digest(tools/'audit_submonthly_warm_calendar.py') or annual['annual_state_sha256']!=digest(args.annual/'annual-state.npz'):
        raise ValueError('Source-matched verified annual incumbent required')
    for name,value in annual['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Annual primal replay dependency changed')
    for name,value in monthly['workspace_sha256'].items():
        if digest(args.monthly/name)!=value:raise ValueError('Monthly inventory domain changed')
    n=pypsa.Network(args.input);validate_calendar(n,2025);units=n.storage_units;ids=units.index.tolist();ns=len(ids)
    if ids!=calendar['storage_ids']:raise ValueError('Storage ordering differs')
    rows=partitions(2025,168);capacity=(units.p_nom*units.max_hours).to_numpy()
    bounds,E,rhs=boundaries(capacity,units.state_of_charge_initial.to_numpy(),units.cyclic_state_of_charge.to_numpy(),months=len(rows))
    with np.load(args.annual/'annual-state.npz',allow_pickle=False) as data:state=validate_warm(data['inventories_mwh'],bounds,E,rhs)
    floors=[];block_hashes=[]
    for row in rows:
        folder=args.calendar/f"{row['index']:02d}";meta=verify_block(folder,row,source,len(rows))
        proof=calendar['rows'][row['index']]
        if meta['storage_ids']!=ids or proof['index']!=row['index'] or proof['block_sha256']!=meta['block_sha256'] or proof['receipt_sha256']!=digest(folder/'block.json'):
            raise ValueError('Chronological coefficient proof changed')
        block=load_block(folder/'block.npz');floors.append(nonnegative_objective_floor(block));block_hashes.append(meta['block_sha256']);del block
    data=[];indices=[];columns=[];limits=[]
    def constraint(entries,value):
        r=len(limits);limits.append(float(value))
        for c,v in entries:indices.append(r);columns.append(c);data.append(float(v))
    for row in rows:
        i=row['index'];times=n.snapshots[row['start_hour']:row['end_hour_exclusive']]
        for j,key in enumerate(ids):
            unit=units.loc[key]
            water=n.storage_units_t.inflow.loc[times,key].to_numpy() if key in n.storage_units_t.inflow else np.zeros(len(times))
            retention=np.full(len(times),1-unit.standing_loss)
            if i==0 and not unit.cyclic_state_of_charge:retention[0]=1.
            a,gain,drain,cap=envelope(capacity[j],retention,np.full(len(times),-unit.p_min_pu*unit.p_nom*unit.efficiency_store),np.full(len(times),unit.p_max_pu*unit.p_nom/unit.efficiency_dispatch),water)
            constraint([(i*ns+j,-a),((i+1)*ns+j,1.)],gain)
            constraint([(i*ns+j,a),((i+1)*ns+j,-1.)],drain)
            constraint([((i+1)*ns+j,1.)],cap)
    U=sparse.csr_matrix((data,(indices,columns)),shape=(len(limits),len(bounds)));limit=np.asarray(limits)
    # Retain independently checked old necessary month-boundary envelopes,
    # explicitly projected into the new layout rather than silently discarded.
    P=monthly_projection(ns,rows);outer=sparse.load_npz(args.monthly/'master-inequality.npz')@P
    with np.load(args.monthly/'master-state.npz',allow_pickle=False) as saved:outer_limit=saved['limit'].copy()
    U=sparse.vstack([U,outer],format='csr');limit=np.r_[limit,outer_limit]
    violation=float(max(0.,np.max(U@state-limit,initial=0.)))
    if violation>1e-7:raise ValueError('Verified annual anchor fails necessary storage envelopes')
    args.output.mkdir(parents=True);sparse.save_npz(args.output/'master-equality.npz',E);sparse.save_npz(args.output/'master-inequality.npz',U)
    np.savez_compressed(args.output/'master-state.npz',bounds=np.asarray(bounds),rhs=rhs,limit=limit,warm_state_mwh=state)
    result=dict(status='submonthly_inventory_workspace_prepared',input_sha256=source,year=2025,blocks=rows,storage_ids=ids,
        block_sha256=block_hashes,objective_floors_eur=floors,cyclic_closure_equalities=E.shape[0],reachability_constraints=U.shape[0],warm_reachability_violation=violation,
        annual_primal_audit_sha256=digest(args.annual/'verified.json'),annual_feasible_cost_eur=annual['annual_feasible_cost_eur'],monthly_workspace_sha256=digest(args.monthly/'master-workspace.json'),
        workspace_sha256={name:digest(args.output/name) for name in ['master-equality.npz','master-inequality.npz','master-state.npz']},
        producer_sha256=digest(Path(__file__)),dependencies={name:digest(tools/name) for name in ['inventory_reachability.py','annual_inventory_workspace.py','submonthly_inventory_mapping.py','prepare_submonthly_calendar.py','storage_objective_floor.py','check_storage_dual_bounds.py']},
        scope='Necessary source-inventory envelopes and independently feasible anchor only; no master optimisation, candidate dispatch or convergence claim.')
    save(args.output/'master-workspace.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','monthly','calendar','annual','output']:parser.add_argument('--'+name,type=Path,required=True)
    result=prepare(parser.parse_args());print(f"Prepared {len(result['blocks'])}-block inventory workspace; no new annual optimum.")
