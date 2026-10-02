"""Preserve native LP coefficients while exposing chronological inventory boundaries."""
import numpy as np
from scipy import sparse
from storage_coordinator import Block

def block(network,snapshots,index,count):
    n=network.copy();n.set_snapshots(snapshots)
    ids=n.storage_units.index;ns=len(ids);nx=(count+1)*ns
    if len(n.stores) or n.generators.committable.any() or any(n.generators[k].notna().any() for k in ['ramp_limit_up','ramp_limit_down']):raise ValueError('Unsupported cross-block state')
    for key in ['e_sum_min','e_sum_max']:
        if key in n.generators and any(np.isfinite(v) and (v>0 if key=='e_sum_min' else True) for v in n.generators[key].dropna()):raise ValueError('Energy budgets need master constraints')
    if len(n.global_constraints):raise ValueError('Global constraints require explicit master treatment')
    for frame in [n.generators,n.lines,n.links,n.storage_units]:
        for k in ['p_nom_extendable','s_nom_extendable']:
            if k in frame and frame[k].any():raise ValueError('Expansion unsupported')
    if len(n.storage_units_t.state_of_charge_set.columns):raise ValueError('Explicit hourly SOC targets require dedicated boundary mapping')
    n.storage_units['cyclic_state_of_charge']=False;n.storage_units['cyclic_state_of_charge_per_period']=False;n.storage_units['state_of_charge_initial']=0.
    model=n.optimize.create_model(include_objective_constant=False);mat=model.matrices
    if mat.Q is not None and mat.Q.nnz:raise ValueError('Quadratic objective unsupported')
    A=mat.A.tocsr();b=np.asarray(mat.b);sense=np.asarray(mat.sense);C=sparse.lil_matrix((len(b),nx))
    label_to_row={int(v):i for i,v in enumerate(mat.clabels)}
    balances=model.constraints['StorageUnit-energy_balance'].labels.sel(snapshot=snapshots[0]).values
    for j,label in enumerate(balances):
        # Previous period inventory loses energy during this first interval.
        coefficient=(1-float(n.storage_units.loc[ids[j],'standing_loss']))**float(n.snapshot_weightings.stores.iloc[0])
        if index==0 and not bool(network.storage_units.loc[ids[j],'cyclic_state_of_charge']):coefficient=1.
        C[label_to_row[int(label)],index*ns+j]=coefficient
    label_to_col={int(v):i for i,v in enumerate(mat.vlabels)}
    terminals=model.variables['StorageUnit-state_of_charge'].labels.sel(snapshot=snapshots[-1]).values
    T=sparse.lil_matrix((ns,A.shape[1]));D=sparse.lil_matrix((ns,nx))
    for j,label in enumerate(terminals):T[j,label_to_col[int(label)]]=1.;D[j,(index+1)*ns+j]=-1.
    eq=sense=='=';less=sense=='<';greater=sense=='>'
    if not np.all(eq|less|greater):raise ValueError('Unknown native constraint sense')
    return Block(np.asarray(mat.c),list(zip(mat.lb,mat.ub)),sparse.vstack([A[eq],T],format='csr'),np.r_[b[eq],np.zeros(ns)],sparse.vstack([C.tocsr()[eq],D],format='csr'),sparse.vstack([A[less],-A[greater]],format='csr'),np.r_[b[less],-b[greater]],sparse.vstack([C.tocsr()[less],-C.tocsr()[greater]],format='csr'))
