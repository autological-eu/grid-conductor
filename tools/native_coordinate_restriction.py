"""Coordinate restriction with one native-column sort per operation.

Same selection semantics as submonthly_primal_mapping; no guessed offsets,
changed coefficients or relaxed gates. Avoid re-sorting a monthly LP for every
variable component when transferring large saved dual arrays.
"""
import numpy as np


def indexer(labels):
    labels=np.asarray(labels,dtype=np.int64)
    if labels.ndim!=1 or np.any(labels<0):raise ValueError('Native labels must be a nonnegative vector')
    order=np.argsort(labels);sorted_labels=labels[order]
    if np.any(np.diff(sorted_labels)==0):raise ValueError('Duplicate native labels')
    def locate(requested):
        requested=np.asarray(requested,dtype=np.int64)
        positions=np.searchsorted(sorted_labels,requested)
        if np.any(requested<0) or np.any(positions>=len(labels)) or not np.array_equal(sorted_labels[positions],requested):
            raise ValueError('Requested native coordinate missing')
        return order[positions]
    return locate


def restrict(parent,child,values,kind):
    if kind not in ('variables','constraints'):raise ValueError('Unknown native coordinate family')
    label_name='vlabels' if kind=='variables' else 'clabels'
    parent_labels=np.asarray(getattr(parent.matrices,label_name));child_labels=np.asarray(getattr(child.matrices,label_name))
    values=np.asarray(values,dtype=float)
    if values.shape!=parent_labels.shape or not np.isfinite(values).all():raise ValueError('Finite native values of exact width required')
    source_position=indexer(parent_labels);target_position=indexer(child_labels)
    result=np.empty(len(child_labels));covered=np.zeros(len(child_labels),dtype=bool)
    sources=getattr(parent,kind);targets=getattr(child,kind)
    for name in targets:
        if name not in sources:raise ValueError('Parent coordinate component missing')
        target=targets[name].labels;source=sources[name].labels
        if set(source.dims)!=set(target.dims):raise ValueError('Native coordinate dimensions differ')
        source=source.sel({dim:target.coords[dim] for dim in target.dims}).transpose(*target.dims)
        source=np.asarray(source).ravel();target=np.asarray(target).ravel();active=target>=0
        destination=target_position(target[active])
        if np.any(covered[destination]):raise ValueError('Duplicate destination native coordinates')
        result[destination]=values[source_position(source[active])];covered[destination]=True
    if not covered.all():raise ValueError('Unmapped native coordinates')
    return result
