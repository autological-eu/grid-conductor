"""Conditional quadratic I-spline bids, analytic bounded inverse and adjoints."""
import numpy as np
from scipy.special import expit
from batched_transport_cold_retry_2025 import RobustTransportMarket
from batched_transport_dispatch_2025 import softclip

K=9
GRID=np.linspace(0,1,K)

def basis(u):
    # Integrated linear B-spline hats (unnormalized M-splines).
    x=np.asarray(u)[...,None];h=1/(K-1)
    ramp=lambda a:np.maximum(x-a,0)**2/(2*h)
    out=ramp(GRID-h)-2*ramp(GRID)+ramp(GRID+h)
    out[...,0]=np.minimum(x[...,0],h)-np.minimum(x[...,0],h)**2/(2*h)
    # End hat rises only over the final interval; domain is [0,1].
    out[...,-1]=np.maximum(x[...,0]-(1-h),0)**2/(2*h)
    return out

class ConditionalMarket(RobustTransportMarket):
    def offers(self,theta,hours):
        slopes=.05+20*np.logaddexp(0,theta[...,1:])
        reference=self.reference[None,:]*np.ones(theta.shape[:2])
        source=self.source[hours]+theta[...,0]
        nodes=np.concatenate([np.zeros((*slopes.shape[:2],1)),np.cumsum((slopes[...,:-1]+slopes[...,1:])/(2*(K-1)),axis=-1)],axis=-1)+source[...,None]
        return dict(theta=theta,hours=np.asarray(hours),capacity=self.capacity[hours],slopes=slopes,reference=reference,anchors=nodes)

    def supply(self,price,offers,derivative=False,parameters=False):
        slopes=offers['slopes'];C=offers['reference'];A=offers['capacity'];nodes=offers['anchors']
        umax=np.divide(A,C,out=np.zeros_like(A),where=C>0)
        IA=basis(umax);b0=nodes[...,0];bA=b0+(slopes*IA).sum(axis=-1)
        p=price[:,self.zone];tau=self.thermal_tau
        effective=b0+softclip(p-b0,bA-b0,tau)
        ix=np.clip((effective[...,None]>=nodes).sum(axis=-1)-1,0,K-2)
        take=lambda a:np.take_along_axis(a,ix[...,None],axis=-1)[...,0]
        left=take(nodes);s=take(slopes);right=np.take_along_axis(slopes,(ix+1)[...,None],axis=-1)[...,0]
        curvature=(right-s)*(K-1);dy=np.maximum(effective-left,0)
        du=2*dy/(s+np.sqrt(np.maximum(s*s+2*curvature*dy,1e-20)))
        u=ix/(K-1)+du;u=np.clip(u,0,umax)
        q=C*u;bu=s+curvature*du
        sa=expit((p-b0)/tau);sb=expit((p-bA)/tau)
        dq=C/bu*(sa-sb)
        raw=None
        if parameters:
            raw=np.empty_like(offers['theta']);raw[...,0]=-dq
            raw[...,1:]=C[...,None]/bu[...,None]*(sb[...,None]*IA-basis(u))*20*expit(offers['theta'][...,1:])
        # Preserve the earlier near-zero renewable offer and smoothing exactly.
        r=self.zero;rx=p[:,r]
        q[:,r]=A[:,r]/.01*softclip(rx,.01,self.renewable_tau)
        dq[:,r]=A[:,r]/.01*(expit(rx/self.renewable_tau)-expit((rx-.01)/self.renewable_tau))
        if parameters:
            raw[:,r]=0
            return q,dq,raw
        return q,dq if derivative else None

    def coordinate(self,price,offers):
        # Generic coordinate initializer for this spline family, same balance root.
        p=price.copy()
        for z in range(self.nz):
            lo=np.full(len(p),-2000.);hi=np.full(len(p),5000.)
            for _ in range(42):
                p[:,z]=(lo+hi)/2;r=self.evaluate(p,offers)[0][:,z]
                lo=np.where(r<0,p[:,z],lo);hi=np.where(r>=0,p[:,z],hi)
        return p

    def backward(self,theta,result,gq,gp):
        # Parent uses a six-wide parameter allocation only inside its supply;
        # its implicit adjoint itself is dimension independent.
        return super().backward(theta,result,gq,gp)
