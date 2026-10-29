"""Fresh numerical recovery; unchanged market responses and feasibility gates."""
import time
import numpy as np
from scipy.special import expit
from .transport import TransportMarket, softclip


class RecoveredTransportMarket(TransportMarket):
    def coordinate(self,price,offers):
        """Safeguarded scalar price balances to leave flat/clipped merit regions."""
        price=price.copy()
        for z in range(self.nz):
            groups=np.flatnonzero(self.zone==z);edges=np.flatnonzero(self.M[:,z])
            a=offers['anchors'][:,groups,:-1];b=offers['anchors'][:,groups,1:];width=b-a
            capacity=offers['capacity'][:,groups,None]
            tau=np.where(self.zero[groups],self.renewable_tau,self.thermal_tau)[None,:,None]
            weights=capacity/(5*width)
            signs=self.M[edges,z]
            other=price@self.M[edges].T-price[:,z,None]*signs
            lo=self.lower[offers['hours']][:,edges];hi=self.upper[offers['hours']][:,edges]
            def balance(p):
                x=p[:,None,None]-a
                q=(weights*softclip(x,width,tau)).sum(axis=(1,2))
                dq=(weights*(expit(x/tau)-expit((x-width)/tau))).sum(axis=(1,2))
                v=(other+p[:,None]*signs)/self.cost
                flow=lo+softclip(v-lo,hi-lo,self.flow_tau)
                df=(expit((v-lo)/self.flow_tau)-expit((v-hi)/self.flow_tau))/self.cost
                return q+(flow*signs).sum(axis=1)-self.load[offers['hours'],z],dq+df.sum(axis=1)
            lower=np.minimum(price.min(axis=1)-1000,a.min(axis=(1,2),initial=np.inf)-1000)
            upper=np.maximum(price.max(axis=1)+1000,b.max(axis=(1,2),initial=-np.inf)+1000)
            p=price[:,z].copy()
            for _ in range(50):
                residual,derivative=balance(p);done=abs(residual)<=1e-10
                if done.all():break
                lower=np.where((residual<0)&~done,p,lower);upper=np.where((residual>=0)&~done,p,upper)
                candidate=p-np.divide(residual,derivative,out=np.full_like(p,np.inf),where=derivative>1e-14)
                candidate=np.where((candidate>lower)&(candidate<upper)&np.isfinite(candidate),candidate,(lower+upper)/2)
                p=np.where(done,p,candidate)
            price[:,z]=p
        return price

    def solve(self,theta,hours,p0=None,tolerance=1e-9,max_iterations=150):
        began=time.perf_counter();offers=self.offers(theta,hours)
        price=self.initial_prices(offers) if p0 is None else np.array(p0,copy=True)
        done=np.zeros(len(price),bool);iterations=np.zeros(len(price),int);recoveries=0
        for step in range(max_iterations):
            ids=np.flatnonzero(~done)
            if not len(ids):break
            active={k:v[ids] for k,v in offers.items()}
            residual,J,_,_=self.evaluate(price[ids],active,jacobian=True)
            error=abs(residual).max(axis=1);converged=error<=tolerance
            done[ids[converged]]=True;iterations[ids]=step
            if converged.all():continue
            keep=~converged;ids=ids[keep];active={k:v[keep] for k,v in active.items()}
            residual,J=residual[keep],J[keep]
            damping=np.maximum(1e-7,np.minimum(1e-3,abs(residual).max(axis=1)*1e-4))
            delta=np.linalg.solve(J+damping[:,None,None]*np.eye(self.nz),residual[...,None])[...,0]
            # Componentwise clipping can destroy a Newton descent direction.
            # One scalar trust factor per hourly vector preserves that direction.
            delta*=np.minimum(1.,50/np.maximum(abs(delta).max(axis=1),1e-30))[:,None]
            current=(residual*residual).sum(axis=1);pending=np.ones(len(ids),bool);newprice=price[ids].copy();alpha=1.
            for _ in range(20):
                kk=np.flatnonzero(pending)
                if not len(kk):break
                sub={k:v[kk] for k,v in active.items()};trial=price[ids[kk]]-alpha*delta[kk]
                rr=self.evaluate(trial,sub)[0];value=(rr*rr).sum(axis=1)
                accept=value<current[kk]*(1-1e-4*alpha)
                newprice[kk[accept]]=trial[accept];pending[kk[accept]]=False;alpha*=.5
            if pending.any():
                kk=np.flatnonzero(pending);sub={k:v[kk] for k,v in active.items()}
                newprice[kk]=self.coordinate(price[ids[kk]],sub);recoveries+=len(kk)
            price[ids]=newprice
        else:raise RuntimeError(f'Recovered price Newton limit; hours={np.asarray(hours)[~done].tolist()[:10]}')
        residual,J,q,f=self.evaluate(price,offers,jacobian=True)
        maximum=float(abs(residual).max())
        genbound=float(max(np.maximum(-q,0).max(),np.maximum(q-offers['capacity'],0).max()))
        flowbound=float(max(np.maximum(self.lower[hours]-f,0).max(),np.maximum(f-self.upper[hours],0).max()))
        if max(maximum,genbound,flowbound)>1e-7:raise ValueError('Unchanged original MW tolerance failed')
        return dict(prices=price,quantities_gw=q,flows_gw=f,hours=np.asarray(hours),jacobian=J,iterations=iterations,
            coordinate_recoveries=recoveries,seconds=time.perf_counter()-began,
            certificate=dict(balance_mw=maximum*1000,generation_bound_mw=genbound*1000,flow_bound_mw=flowbound*1000,emergency_mwh=0.))
