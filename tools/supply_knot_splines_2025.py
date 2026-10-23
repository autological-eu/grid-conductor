"""Six explicit supply-price nodes, monotone cubic Hermite interpolation.

The economic curve has nodes at exactly 0,20,40,60,80,100% availability.
Positive price increments enforce monotonicity; arbitrary alternating curvature
is allowed. Differentiation uses analytic clock derivatives and complex-step
derivatives of the local cubic formula, not finite-difference clearing runs.
"""
from dataclasses import dataclass
import numpy as np
from scipy.special import expit

KNOTS=np.linspace(0,1,6)


def initial_parameters(count):
    out=np.zeros((count,10));out[:,5:]=np.log(np.expm1((9.6-.001)/20))
    return out


def coefficients(increments):
    h=.2;delta=increments/h;y=np.c_[np.zeros(len(delta)),np.cumsum(increments,axis=1)]
    left=(3*delta[:,0]-delta[:,1])/2;right=(3*delta[:,-1]-delta[:,-2])/2
    slopes=np.c_[np.where(np.real(left)>0,left,0),2*delta[:,:-1]*delta[:,1:]/(delta[:,:-1]+delta[:,1:]),np.where(np.real(right)>0,right,0)]
    a=(slopes[:,:-1]+slopes[:,1:]-2*delta)/h**2
    b=(3*delta-2*slopes[:,:-1]-slopes[:,1:])/h
    return a,b,slopes[:,:-1],y[:,:-1],y,slopes


def raw(u,increments):
    u=np.asarray(u);a,b,c,d,y,slopes=coefficients(increments);h=.2
    v=np.clip(u,0,1);i=np.minimum((v/h).astype(int),4);r=np.arange(len(v));z=v-i*h
    aa=a[r,i];bb=b[r,i];cc=c[r,i];dd=d[r,i]
    price=((aa*z+bb)*z+cc)*z+dd;slope=(3*aa*z+2*bb)*z+cc
    spans=a*h**4/4+b*h**3/3+c*h**2/2+d*h
    prefix=np.c_[np.zeros(len(v)),np.cumsum(spans,axis=1)]
    integral=prefix[r,i]+aa*z**4/4+bb*z**3/3+cc*z**2/2+dd*z
    low=np.minimum(u,0);high=np.maximum(u-1,0)
    price+=low*slopes[:,0]+high*slopes[:,-1]
    integral+=.5*low**2*slopes[:,0]+high*y[:,-1]+.5*high**2*slopes[:,-1]
    slope=np.where(u<0,slopes[:,0],np.where(u>1,slopes[:,-1],slope))
    return price,integral,slope


def spline(u,increments):
    p,j,m=raw(u,increments);center=raw(np.full(len(increments),.5),increments)[0]
    return p-center,j-np.asarray(u)*center,m


@dataclass
class KnotCost:
    capacity:np.ndarray
    source:np.ndarray
    parameter:np.ndarray
    features:np.ndarray
    zero_bid:np.ndarray
    theta:np.ndarray
    extra_count:int
    generation_regularizer:float=.01
    network_regularizer:float=1e-6

    def __post_init__(self):
        self.ng=len(self.capacity);pars=self.theta[self.parameter]
        self.z=(self.features*pars[:,:5]).sum(axis=1)/4;self.shift=80*np.tanh(self.z)
        self.increments=.001+20*np.logaddexp(0,pars[:,5:]);self.increment_derivative=20*expit(pars[:,5:])
        self.shift[self.zero_bid]=0

    def evaluate(self,x):
        q=x[:self.ng];u=q/self.capacity;p,j,m=spline(u,self.increments)
        p[self.zero_bid]=0;j[self.zero_bid]=0;m[self.zero_bid]=0
        gradient=np.r_[self.source+self.shift+p+self.generation_regularizer*u,self.network_regularizer*x[self.ng:]]
        H=np.r_[(m+self.generation_regularizer)/self.capacity,np.full(self.extra_count,self.network_regularizer)]
        value=float((q*(self.source+self.shift)+self.capacity*j+.5*self.generation_regularizer*q*u).sum()+.5*self.network_regularizer*(x[self.ng:]**2).sum())
        if not np.isfinite(value) or not np.isfinite(gradient).all() or not (H>0).all():raise ValueError('Invalid monotone cubic cost')
        return value,gradient,H

    def parameter_vjp(self,x,adjoint):
        u=x[:self.ng]/self.capacity;shape=[]
        for k in range(5):
            inc=self.increments.astype(complex);inc[:,k]+=1e-25j
            shape.append(np.imag(spline(u,inc)[0])/1e-25*self.increment_derivative[:,k])
        factors=np.c_[20*(1-np.tanh(self.z)**2)[:,None]*self.features,np.array(shape).T]
        factors[self.zero_bid]=0;out=np.zeros_like(self.theta)
        np.add.at(out,self.parameter,-adjoint[:self.ng,None]*factors)
        return out

    def interval_bids(self,bins):
        edges=np.linspace(0,1,bins+1);primitive=[]
        for u in edges:
            j=spline(np.full(self.ng,u),self.increments)[1];j[self.zero_bid]=0;primitive.append(j)
        return self.source[:,None]+self.shift[:,None]+np.diff(np.array(primitive).T,axis=1)*bins
