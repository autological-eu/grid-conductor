"""Independent-corridor experimental market, retaining every source zone/hour.

Analytic smoothed inverse supply, bounded quadratic-transport responses and
batched zonal-price Newton. Different network assumption from the PTDF model.
Exact implicit adjoints on identified price directions; no backward ridge and
no emergency generation. GW and EUR/MWh throughout.
"""
import time
import numpy as np
from scipy.special import expit


def softclip(x,width,tau):
    # Same softplus difference without subtracting two huge almost-equal terms.
    return np.clip(x,0,width)+tau*(np.log1p(np.exp(-abs(x/tau)))-np.log1p(np.exp(-abs((x-width)/tau))))


class TransportMarket:
    def __init__(self,zones,groups,lower,upper,edges,capacity,source,load,cost=4.,thermal_tau=.05,renewable_tau=.001,flow_tau=.0001):
        from spline_europe_2025 import ZERO_TECH
        self.zones=zones;self.groups=groups;self.nz=len(zones);self.ng=len(groups)
        self.zone=np.array([g['zone_id'] for g in groups])
        self.Z=np.eye(self.nz)[self.zone]
        self.zero=np.array([g['technology'] in ZERO_TECH for g in groups])
        self.thermal=np.flatnonzero(~self.zero);self.renewable=np.flatnonzero(self.zero)
        self.lower,self.upper=lower,upper
        self.edges=np.asarray(edges,dtype=int).reshape(-1,2)
        self.M=np.zeros((len(edges),self.nz))
        self.M[np.arange(len(edges)),self.edges[:,0]]=-1
        self.M[np.arange(len(edges)),self.edges[:,1]]=1
        self.capacity,self.source,self.load=capacity,source,load
        self.cost=cost;self.thermal_tau=thermal_tau;self.renewable_tau=renewable_tau;self.flow_tau=flow_tau
        self.B=(np.arange(5)[None,:]<np.arange(6)[:,None]).astype(float)-np.array([1,1,.5,0,0])[None,:]

    def offers(self,theta,hours):
        if theta.ndim==2:theta=np.broadcast_to(theta,(len(hours),*theta.shape))
        increments=.001+20*np.logaddexp(0,theta[:,:,1:])
        shift=80*np.tanh(theta[:,:,0]/4)
        nodes=np.concatenate([np.zeros((*increments.shape[:2],1)),np.cumsum(increments,axis=-1)],axis=-1)
        center=(nodes[:,:,2]+nodes[:,:,3])/2
        anchor=self.source[hours,:,None]+shift[:,:,None]+nodes-center[:,:,None]+.01*np.linspace(0,1,6)
        anchor[:,self.zero]=.01*np.linspace(0,1,6)
        return dict(anchors=anchor,capacity=self.capacity[hours],theta=theta,hours=np.asarray(hours))

    def supply(self,price,offers,derivative=False,parameters=False):
        anchor,capacity=offers['anchors'],offers['capacity'];T=len(price)
        q=np.zeros((T,self.ng));dq=np.zeros_like(q) if derivative or parameters else None
        ids=self.thermal
        a,b=anchor[:,ids,:-1],anchor[:,ids,1:]
        width=b-a;x=price[:,self.zone[ids],None]-a
        ramp=softclip(x,width,self.thermal_tau)
        scale=capacity[:,ids,None]/(5*width)
        q[:,ids]=(scale*ramp).sum(axis=-1)
        if derivative or parameters:
            sa=expit(x/self.thermal_tau);sb=expit((x-width)/self.thermal_tau)
            dq[:,ids]=(scale*(sa-sb)).sum(axis=-1)
        rid=self.renewable
        rx=price[:,self.zone[rid]]
        q[:,rid]=capacity[:,rid]/.01*softclip(rx,.01,self.renewable_tau)
        if derivative or parameters:dq[:,rid]=capacity[:,rid]/.01*(expit(rx/self.renewable_tau)-expit((rx-.01)/self.renewable_tau))
        if parameters:
            node=np.zeros((T,len(ids),6))
            node[:,:,:-1]+=scale*(-sa+ramp/width)
            node[:,:,1:]+=scale*(sb-ramp/width)
            raw=np.zeros((T,self.ng,6))
            pars=offers['theta'][:,ids]
            raw[:,ids,0]=node.sum(axis=-1)*20*(1-np.tanh(pars[:,:,0]/4)**2)
            raw[:,ids,1:]=(node@self.B)*20*expit(pars[:,:,1:])
            return q,dq,raw
        return q,dq

    def evaluate(self,price,offers,jacobian=False):
        q,dq=self.supply(price,offers,derivative=jacobian)
        hh=offers['hours'];lower,upper=self.lower[hh],self.upper[hh]
        unconstrained=(price@self.M.T)/self.cost
        f=lower+softclip(unconstrained-lower,upper-lower,self.flow_tau)
        residual=q@self.Z+f@self.M-self.load[hh]
        J=None
        if jacobian:
            df=(expit((unconstrained-lower)/self.flow_tau)-expit((unconstrained-upper)/self.flow_tau))/self.cost
            diagonal=dq@self.Z
            J=np.zeros((len(price),self.nz,self.nz));J[:,np.arange(self.nz),np.arange(self.nz)]=diagonal
            for k,(i,j) in enumerate(self.edges):
                w=df[:,k]
                J[:,i,i]+=w;J[:,j,j]+=w;J[:,i,j]-=w;J[:,j,i]-=w
        return residual,J,q,f

    def initial_prices(self,offers):
        # Model-only copperplate warm start; actual observations are never read.
        lo=offers['anchors'][:,:,0].min(axis=1)-10
        hi=offers['anchors'][:,:,-1].max(axis=1)+10
        demand=self.load[offers['hours']].sum(axis=1)
        for _ in range(35):
            mid=(lo+hi)/2
            q,_=self.supply(np.broadcast_to(mid[:,None],(len(mid),self.nz)),offers)
            more=q.sum(axis=1)<demand
            lo=np.where(more,mid,lo);hi=np.where(more,hi,mid)
        return np.broadcast_to(((lo+hi)/2)[:,None],(len(lo),self.nz)).copy()

    def solve(self,theta,hours,p0=None,tolerance=1e-9,max_iterations=150):
        began=time.perf_counter();offers=self.offers(theta,hours)
        price=self.initial_prices(offers) if p0 is None else np.array(p0,copy=True)
        iterations=np.zeros(len(price),int);done=np.zeros(len(price),bool)
        identity=np.eye(self.nz)
        for step in range(max_iterations):
            ids=np.flatnonzero(~done)
            if not len(ids):break
            active={k:v[ids] for k,v in offers.items()}
            r,J,_,_=self.evaluate(price[ids],active,jacobian=True)
            error=abs(r).max(axis=1);converged=error<=tolerance
            done[ids[converged]]=True;iterations[ids]=step
            if converged.all():continue
            keep=~converged;ids=ids[keep]
            active={k:v[keep] for k,v in active.items()};r,J=r[keep],J[keep]
            # Forward-only Levenberg damping, never used in implicit gradients.
            damping=np.maximum(1e-7,np.minimum(1e-3,abs(r).max(axis=1)*1e-4))
            delta=np.linalg.solve(J+damping[:,None,None]*identity,r[...,None])[...,0].clip(-50,50)
            current=(r*r).sum(axis=1);newprice=price[ids].copy();pending=np.ones(len(ids),bool)
            alpha=1.
            for _ in range(20):
                kk=np.flatnonzero(pending)
                if not len(kk):break
                sub={k:v[kk] for k,v in active.items()}
                trial=price[ids[kk]]-alpha*delta[kk]
                rr=self.evaluate(trial,sub)[0];value=(rr*rr).sum(axis=1)
                accept=value<current[kk]*(1-1e-4*alpha)
                newprice[kk[accept]]=trial[accept];pending[kk[accept]]=False
                alpha*=.5
            if pending.any():
                worst=int(ids[np.flatnonzero(pending)[0]])
                raise RuntimeError(f'Price Newton stalled at hour{int(hours[worst])}, residualGW={float(error.max())}')
            price[ids]=newprice
        else:raise RuntimeError(f'Price Newton limit; unclosed hours={np.flatnonzero(~done).tolist()[:10]}')
        residual,J,q,f=self.evaluate(price,offers,jacobian=True)
        maximum=float(abs(residual).max())
        genbound=float(max(np.maximum(-q,0).max(),np.maximum(q-offers['capacity'],0).max()))
        flowbound=float(max(np.maximum(self.lower[hours]-f,0).max(),np.maximum(f-self.upper[hours],0).max()))
        if max(maximum,genbound,flowbound)>1e-7:raise ValueError('Original MW feasibility tolerance failed in transport model')
        return dict(prices=price,quantities_gw=q,flows_gw=f,hours=np.asarray(hours),jacobian=J,iterations=iterations,
            seconds=time.perf_counter()-began,certificate=dict(balance_mw=maximum*1000,generation_bound_mw=genbound*1000,flow_bound_mw=flowbound*1000,emergency_mwh=0.))

    def backward(self,theta,result,gq,gp):
        offers=self.offers(theta,result['hours'])
        _,dq,raw=self.supply(result['prices'],offers,derivative=True,parameters=True)
        rhs=gp+(gq*dq)@self.Z
        J=result['jacobian']
        eigen,vectors=np.linalg.eigh(J)
        threshold=np.maximum(1e-12,eigen[:,-1]*1e-12)
        identified=eigen>threshold[:,None]
        projected=np.einsum('tji,tj->ti',vectors,rhs)
        # Moore-Penrose convention in genuinely unidentified price directions;
        # report these explicitly, never hide observed-price errors.
        dual=np.einsum('tij,tj->ti',vectors,np.divide(projected,eigen,out=np.zeros_like(projected),where=identified))
        gradient=(gq-dual[:,self.zone])[:,:,None]*raw
        return gradient,dict(unidentified_directions=int((~identified).sum()),unidentified_rhs_max=float(abs(np.where(identified,0,projected)).max()))
