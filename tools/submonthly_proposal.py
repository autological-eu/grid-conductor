"""Stabilise a search proposal without restricting the annual master relaxation."""
import numpy as np
from annual_inventory_workspace import validate_warm


def stabilise(proposal,anchor,weight,bounds,equality,rhs,inequality,limit):
    if not np.isfinite(weight) or not 0<weight<=1:
        raise ValueError('Explicit positive proposal weight at most one required')
    proposal=np.asarray(proposal,dtype=float);anchor=np.asarray(anchor,dtype=float)
    if proposal.shape!=anchor.shape or not np.isfinite(proposal).all() or not np.isfinite(anchor).all():
        raise ValueError('Finite matching source inventory layout required')
    point=(1.-weight)*anchor+weight*proposal
    point=validate_warm(point,bounds,equality,rhs)
    if np.max(inequality@point-limit,initial=0.)>1e-7:
        raise ValueError('Stabilised search point violates necessary inventory constraints')
    return point
