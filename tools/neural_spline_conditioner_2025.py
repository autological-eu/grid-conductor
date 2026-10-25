"""Small NumPy MLP conditioner with analytic backprop; no autodiff dependency."""
import numpy as np

class Conditioner:
    def __init__(self, zone, technology, seed=20261025):
        self.zone=np.asarray(zone);self.technology=np.asarray(technology)
        rng=np.random.default_rng(seed)
        self.p=dict(zone=rng.normal(0,.1,(max(zone)+1,8)),technology=rng.normal(0,.1,(max(technology)+1,4)),
                    W1=rng.normal(0,1/np.sqrt(18),(18,32)),b1=np.zeros(32),
                    W2=rng.normal(0,1/np.sqrt(32),(32,32)),b2=np.zeros(32),W3=np.zeros((32,10)),b3=np.zeros(10))
        self.base=np.r_[-30.,np.full(9,np.log(np.expm1((60-.05)/20)))]
    def forward(self,X,active,cache=False):
        # Drop constant intercept: neural biases provide it.
        T,G,_=X.shape
        inp=np.concatenate([X[...,1:],np.broadcast_to(self.p['zone'][self.zone],(T,G,8)),np.broadcast_to(self.p['technology'][self.technology],(T,G,4))],axis=-1)
        h1=np.tanh(inp@self.p['W1']+self.p['b1']);h2=np.tanh(h1@self.p['W2']+self.p['b2'])
        raw=self.base+(h2@self.p['W3']+self.p['b3'])*active[None,:,None]
        return (raw,(inp,h1,h2,active)) if cache else raw
    def backward(self,gradient,cache):
        inp,h1,h2,active=cache;g=gradient*active[None,:,None]
        sums=lambda a,b:np.einsum('tgi,tgj->ij',a,b,optimize=True)
        out=dict(W3=sums(h2,g),b3=g.sum(axis=(0,1)))
        g2=(g@self.p['W3'].T)*(1-h2*h2)
        out.update(W2=sums(h1,g2),b2=g2.sum(axis=(0,1)))
        g1=(g2@self.p['W2'].T)*(1-h1*h1)
        out.update(W1=sums(inp,g1),b1=g1.sum(axis=(0,1)))
        gi=(g1@self.p['W1'].T).sum(axis=0)
        out['zone']=np.zeros_like(self.p['zone']);out['technology']=np.zeros_like(self.p['technology'])
        np.add.at(out['zone'],self.zone,gi[:,6:14]);np.add.at(out['technology'],self.technology,gi[:,14:18])
        return out
