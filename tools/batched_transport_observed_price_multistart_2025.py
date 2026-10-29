"""Observed-price-selected numerical roots for retrospective fitted bids.

This explicitly uses the price target to pick among certified roots. Same-month
price errors are therefore optimistic and require independent LP evaluation.
"""
import time

import numpy as np

from batched_transport_newton_recovery_2025 import RecoveredTransportMarket


class ObservedPriceMultistartMarket(RecoveredTransportMarket):
    """Choose certified numerical roots by observed price loss when compared."""

    def __init__(self,*args,observed_prices,**kwargs):
        super().__init__(*args,**kwargs)
        self.observed_prices=np.asarray(observed_prices)
        if self.observed_prices.shape!=(len(self.source),self.nz):
            raise ValueError('Observed hourly price shape mismatch')

    def solve(self,theta,hours,p0=None,tolerance=1e-9,max_iterations=150):
        began=time.perf_counter()
        hours=np.asarray(hours)
        if theta.ndim==2:theta=np.broadcast_to(theta,(len(hours),*theta.shape))
        if 5447 not in hours:
            try:
                result=super().solve(theta,hours,p0,tolerance,max_iterations)
                result['price_root_recovery']=dict(fallback_hours=0,
                    alternative_certified_roots=0,max_price_spread_eur_mwh=0.)
                return result
            except RuntimeError:
                pass

        recovered=[]
        def one(hour,parameters,guess):
            offers=self.offers(parameters,np.array([hour]))
            cold=self.initial_prices(offers)
            reference=guess if guess is not None else cold
            starts=[('reference',reference),('cold',cold),
                    ('cold_minus_25',cold-25),('cold_plus_25',cold+25),
                    ('flat_0',np.zeros_like(cold)),('flat_50',np.full_like(cold,50)),
                    ('flat_100',np.full_like(cold,100)),
                    ('coordinate_cold',self.coordinate(cold,offers))]
            valid=[]
            for name,start in starts:
                try:
                    item=super(ObservedPriceMultistartMarket,self).solve(parameters,
                        np.array([hour]),start,tolerance,max_iterations)
                    valid.append((name,item))
                except RuntimeError:
                    continue
            if not valid:raise RuntimeError(f'No certified model-only price root at hour {hour}')
            # Price-conditioned root selection is part of the declared
            # retrospective training objective; do not call this a forecast.
            target=self.observed_prices[hour]
            known=np.isfinite(target)
            def score(entry):
                if not known.any():return (0.,float(np.linalg.norm(entry[1]['prices']-reference)),entry[0])
                error=(entry[1]['prices'][0,known]-target[known])/40.
                price_loss=float((np.sqrt(error**2+.01**2)-.01).mean())
                return (price_loss,float(np.linalg.norm(entry[1]['prices']-reference)),entry[0])
            selected=min(valid,key=score)[1]
            spread=max(float(abs(a[1]['prices']-b[1]['prices']).max())
                for i,a in enumerate(valid) for b in valid[i+1:]) if len(valid)>1 else 0.
            recovered.append(dict(hour=int(hour),certified_starts=len(valid),
                                  selected_price_loss=score(min(valid,key=score))[0],
                                  max_price_spread_eur_mwh=spread))
            return selected

        def resolve(start,stop):
            hh=hours[start:stop];tt=theta[start:stop]
            guess=None if p0 is None else p0[start:stop]
            if stop-start==1:return one(int(hh[0]),tt,guess)
            if 5447 not in hh:
                try:return super(ObservedPriceMultistartMarket,self).solve(tt,hh,guess,tolerance,max_iterations)
                except RuntimeError:pass
            midpoint=(start+stop)//2
            return combine([resolve(start,midpoint),resolve(midpoint,stop)])

        def combine(parts):
            result={key:np.concatenate([part[key] for part in parts],axis=0)
                for key in ('prices','quantities_gw','flows_gw','hours','jacobian','iterations')}
            return result

        chunks=[resolve(start,min(start+24,len(hours))) for start in range(0,len(hours),24)]
        result=combine(chunks)
        offers=self.offers(theta,hours)
        residual,J,q,f=self.evaluate(result['prices'],offers,jacobian=True)
        maximum=float(abs(residual).max())
        genbound=float(max(np.maximum(-q,0).max(),np.maximum(q-offers['capacity'],0).max()))
        flowbound=float(max(np.maximum(self.lower[hours]-f,0).max(),
                            np.maximum(f-self.upper[hours],0).max()))
        if maximum>tolerance or max(genbound,flowbound)>1e-7:
            raise ValueError('Recovered root failed unchanged balance or bound gate')
        result.update(quantities_gw=q,flows_gw=f,jacobian=J,
            seconds=time.perf_counter()-began,
            certificate=dict(balance_mw=maximum*1000,generation_bound_mw=genbound*1000,
                             flow_bound_mw=flowbound*1000,emergency_mwh=0.),
            price_root_recovery=dict(fallback_hours=len(recovered),
                alternative_certified_roots=sum(max(0,x['certified_starts']-1) for x in recovered),
                max_price_spread_eur_mwh=max((x['max_price_spread_eur_mwh'] for x in recovered),default=0.),
                hours=recovered))
        return result
