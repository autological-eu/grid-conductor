"""24 local-hour bid tables plus January-centered daily condition adjustments."""
import numpy as np
import pandas as pd
from intraday_offer_bids_2025 import TIMEZONES

def feature_rows(groups,data,hours,reference,centers=None):
    utc=pd.Timestamp('2025-01-01',tz='UTC')+pd.to_timedelta(hours,unit='h')
    X=np.zeros((len(hours),len(groups),26))
    for g,row in enumerate(groups):
        local=utc.tz_convert(TIMEZONES[row['zone'][:2]])
        X[np.arange(len(hours)),g,np.asarray(local.hour)]=1
        X[:,g,24]=np.asarray(local.dayofweek>=5,dtype=float)
        X[:,g,25]=data['capacity'][hours,g]/1000/reference[g]
    if centers is None:centers=X[:,:,24:].mean(axis=0)
    X[:,:,24:]-=centers
    return X,centers

def initialize(groups):
    w=np.zeros((groups,26,10));w[:,:24,0]=-30
    w[:,:24,1:]=np.log(np.expm1((60-.05)/20))
    return w

def regularizer(w,initial,active):
    delta=w-initial;n=max(1,int(active.sum())*26*10)
    grad=.002*delta*active[:,None,None]/n
    ridge=.001*float((delta[active]**2).sum())/n
    diff=np.roll(w[:,:24],-1,axis=1)-w[:,:24];nn=max(1,int(active.sum())*24*10)
    smooth=.001*float((diff[active]**2).sum())/nn
    dd=.002*diff*active[:,None,None]/nn
    grad[:,:24]+=np.roll(dd,1,axis=1)-dd
    return ridge+smooth,grad
