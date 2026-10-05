"""Restrict native row prices; restore missing future-SOC price at block end.

Transferred multipliers are candidate LP supports, not new solver termination
records. Replay original coefficients and finite-bound support before adoption.
"""
import numpy as np
from scipy.optimize import OptimizeResult
from submonthly_primal_mapping import native_positions,restrict_primal
from native_coordinate_restriction import restrict


def restrict_row_prices(parent,child,prices):
    parent_labels=np.asarray(parent.matrices.clabels);child_labels=np.asarray(child.matrices.clabels)
    prices=np.asarray(prices,dtype=float)
    if prices.shape!=parent_labels.shape or not np.isfinite(prices).all():
        raise ValueError('Finite native row prices of exact width required')
    result=np.empty(len(child_labels));covered=np.zeros(len(child_labels),dtype=bool)
    for name in child.constraints:
        if name not in parent.constraints:raise ValueError('Parent constraint component missing')
        target=child.constraints[name].labels;source=parent.constraints[name].labels
        if set(source.dims)!=set(target.dims):raise ValueError('Constraint dimensions differ')
        source=source.sel({dim:target.coords[dim] for dim in target.dims}).transpose(*target.dims)
        source=np.asarray(source).ravel();target=np.asarray(target).ravel();active=target>=0
        destination=native_positions(child_labels,target[active])
        if covered[destination].any():raise ValueError('Duplicate child constraint row')
        result[destination]=prices[native_positions(parent_labels,source[active])];covered[destination]=True
    if not covered.all():raise ValueError('Unmapped child constraint rows')
    return result


def restrict_duals(network,parent,child,arrays,last_snapshot):
    mat=parent.matrices;sense=np.asarray(mat.sense);ns=len(network.storage_units)
    y=np.asarray(arrays['equality_duals'],dtype=float);z=np.asarray(arrays['inequality_duals'],dtype=float)
    if ns<1 or not np.all((sense=='=')|(sense=='<')|(sense=='>')):
        raise ValueError('Supported native senses and storage units required')
    if y.shape!=(int(np.sum(sense=='='))+ns,) or z.shape!=(int(np.sum(sense!='=')),) or not np.isfinite(y).all() or not np.isfinite(z).all():
        raise ValueError('Parent dual dimensions differ from native layout')
    prices=np.empty(len(sense));prices[sense=='=']=y[:-ns]
    less=int(np.sum(sense=='<'));prices[sense=='<']=z[:less];prices[sense=='>']=-z[less:]
    child_prices=restrict(parent,child,prices,'constraints')
    # A terminal +SOC row replaces the omitted next-hour energy balance's
    # retained previous-SOC coefficient. Preserve the final monthly terminal
    # multiplier when this is the last sub-block instead.
    parent_times=parent.variables['StorageUnit-state_of_charge'].labels.coords['snapshot'].to_index()
    if last_snapshot==parent_times[-1]:terminal=y[-ns:].copy()
    else:
        position=parent_times.get_loc(last_snapshot)
        if not isinstance(position,(int,np.integer)):raise ValueError('Unique terminal timestamp required')
        following=parent_times[position+1]
        labels=parent.constraints['StorageUnit-energy_balance'].labels.sel(snapshot=following).values
        retention=(1-network.storage_units.standing_loss.to_numpy())**float(network.snapshot_weightings.stores.loc[following])
        terminal=retention*prices[native_positions(mat.clabels,labels)]
    child_sense=np.asarray(child.matrices.sense)
    if not np.all((child_sense=='=')|(child_sense=='<')|(child_sense=='>')):
        raise ValueError('Unsupported child native sense')
    return OptimizeResult(
        eqlin=OptimizeResult(marginals=np.r_[child_prices[child_sense=='='],terminal]),
        ineqlin=OptimizeResult(marginals=np.r_[child_prices[child_sense=='<'],-child_prices[child_sense=='>']]),
        lower=OptimizeResult(marginals=restrict(parent,child,arrays['lower_marginals'],'variables')),
        upper=OptimizeResult(marginals=restrict(parent,child,arrays['upper_marginals'],'variables')))
