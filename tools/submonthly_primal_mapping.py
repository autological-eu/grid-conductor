"""Restrict a native primal by component coordinates, never by guessed offsets.

This maps saved dispatch/SOC witnesses only. It does not derive renewable
availability, establish source provenance or certify feasibility of a new LP.
Callers must separately replay both source and restricted witnesses.
"""
import numpy as np


def native_positions(labels, requested):
    labels=np.asarray(labels,dtype=np.int64)
    requested=np.asarray(requested,dtype=np.int64)
    if labels.ndim!=1 or len(np.unique(labels))!=len(labels) or np.any(labels<0):
        raise ValueError('Unique nonnegative native column labels required')
    if np.any(requested<0):raise ValueError('Inactive variable cannot index a primal')
    order=np.argsort(labels);sorted_labels=labels[order]
    positions=np.searchsorted(sorted_labels,requested)
    if np.any(positions>=len(labels)) or not np.array_equal(sorted_labels[positions],requested):
        raise ValueError('Requested native variable missing')
    return order[positions]


def restrict_primal(parent_model, child_model, primal):
    parent_labels=np.asarray(parent_model.matrices.vlabels)
    child_labels=np.asarray(child_model.matrices.vlabels)
    values=np.asarray(primal,dtype=float)
    if values.shape!=parent_labels.shape or not np.isfinite(values).all():
        raise ValueError('Finite parent native primal of exact width required')
    result=np.empty(len(child_labels));covered=np.zeros(len(child_labels),dtype=bool)
    for name in child_model.variables:
        if name not in parent_model.variables:raise ValueError('Missing parent variable component')
        child=child_model.variables[name].labels
        parent=parent_model.variables[name].labels
        if set(child.dims)!=set(parent.dims):raise ValueError('Variable coordinate dimensions differ')
        selected=parent.sel({dim:child.coords[dim] for dim in child.dims}).transpose(*child.dims)
        source=np.asarray(selected).ravel();target=np.asarray(child).ravel()
        active=target>=0
        if np.any(source[active]<0):raise ValueError('Active child variable absent in parent')
        destinations=native_positions(child_labels,target[active])
        if np.any(covered[destinations]):raise ValueError('Duplicate child native column')
        result[destinations]=values[native_positions(parent_labels,source[active])]
        covered[destinations]=True
    if not covered.all():raise ValueError('Unmapped child native columns')
    return result


def inventory_at(model, primal, snapshot):
    labels=model.variables['StorageUnit-state_of_charge'].labels.sel(snapshot=snapshot).values
    values=np.asarray(primal,dtype=float)
    if values.shape!=np.asarray(model.matrices.vlabels).shape or not np.isfinite(values).all():
        raise ValueError('Finite native primal of exact width required')
    return values[native_positions(model.matrices.vlabels,labels)].copy()
