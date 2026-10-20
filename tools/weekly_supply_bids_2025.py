"""A bounded weekly supply-bid hypothesis; observed targets only enter fitting."""
import numpy as np
import pandas as pd
from intraday_offer_bids_2025 import TIMEZONES


def weekly(zones):
    times=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC')
    raw=np.column_stack([(times.tz_convert(TIMEZONES[z[:2]]).dayofweek>=5).astype(float) for z in zones])
    return raw-raw.mean(axis=0),raw.astype(bool)


def fit(m,layout,c,x,p,o,calendar,design):
    w,weekend=weekly(m['zones']);coef=np.zeros((m['nz'],3));support=[]
    interior=(x[:,:m['ng']]>.001)&(m['availability']-x[:,:m['ng']]>.001)
    for zi,z in enumerate(m['zones']):
        for fi,f in enumerate(design['resources']):
            ids=[j for j,k in enumerate(layout['kinds']) if k==f and m['offer_zones'][j]==z]
            valid=np.isfinite(o[:,zi])
            if ids:valid&=np.any(interior[:,ids]&(abs(c[:,ids]-p[:,zi,None])<=1e-5),axis=1)
            else:valid[:]=False
            n=int(valid.sum());nw=int((valid&weekend[:,zi]).sum());nd=n-nw
            if n>=design['minimum_interior_hours'] and min(nw,nd)>=design['minimum_daytype_hours']:
                a=np.c_[calendar[valid,zi],w[valid,zi]];b=np.clip(o[valid,zi]-p[valid,zi],-100,100)
                value=np.linalg.solve(a.T@a+design['ridge']*np.eye(16),a.T@b)[-1]
                coef[zi,fi]=np.clip(value,-design['coefficient_bounds_eur_mwh'][fi],design['coefficient_bounds_eur_mwh'][fi])
            support.append(dict(zone=z,resource=f,interior_hours=n,weekend_hours=nw,weekday_hours=nd,coefficient=float(coef[zi,fi])))
    return coef,support


def offers(m,layout,anchor,coef):
    w,_=weekly(m['zones']);c=anchor.copy()
    for j,f in enumerate(layout['kinds']):
        if f in ['gas','coal','nuclear']:
            zi=m['zones'].index(m['offer_zones'][j]);fi=['gas','coal','nuclear'].index(f)
            c[:,j]=np.maximum(0,anchor[:,j]+w[:,zi]*coef[zi,fi])
    return c
