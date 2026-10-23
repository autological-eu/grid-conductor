"""Reuse exact sparse order topology; refresh every varying cost/bound/RHS."""
import hashlib
import json
import numpy as np
from linked_profile_orders import compile_book


class CachedBook:
    def __init__(self):self.signature=None;self.template=None;self.builds=0

    def compile(self,base,orders,reservations=None,storage=None):
        reservations=reservations or {};storage=storage or {};A=base['A'];h=hashlib.sha256()
        for data in [A.data,A.indices,A.indptr]:h.update(np.ascontiguousarray(data).tobytes())
        structural=dict(T=base['T'],shape=A.shape,orders=[{k:v for k,v in r.items() if k!='price'} for r in orders],reservations={name:dict(columns=res['columns'],mw=np.asarray(res['mw']).tolist()) for name,res in reservations.items()},storage=storage)
        h.update(json.dumps(structural,sort_keys=True,allow_nan=False).encode());signature=h.hexdigest()
        if signature!=self.signature:
            self.template=compile_book(base,orders,reservations,storage);self.signature=signature;self.builds+=1
        template=self.template;T,n=template['T'],template['n'];B=len(orders);upper=np.asarray(base['upper'],float).copy()
        for res in reservations.values():
            cap=np.asarray(res['mw'])
            if cap.min()<0 or np.max(cap-upper[:,res['columns']])>1e-7:raise ValueError('Reservation exceeds current original capacity')
            upper[:,res['columns']]-=cap
        cost=template['c'].copy();cost[:T*n]=np.asarray(base['cost']).ravel()
        cost[T*n:T*n+B]=[r['price']*q.sum() for r,q in zip(orders,template['profiles'],strict=True)]
        if not np.isfinite(cost).all():raise ValueError('Nonfinite refreshed bid cost')
        lower=template['lower'].copy();hi=template['upper'].copy();lower[:T*n]=np.asarray(base['lower']).ravel();hi[:T*n]=upper.ravel()
        rlo=template['row_lower'].copy();rhi=template['row_upper'].copy();nr=base['A'].shape[0]
        rlo[:T*nr]=np.asarray(base['row_lower']).ravel();rhi[:T*nr]=np.asarray(base['row_upper']).ravel()
        return template|dict(c=cost,lower=lower,upper=hi,row_lower=rlo,row_upper=rhi,orders=orders)
