"""Monthly local-hour technology bids with implicit cleared-price gradients.

Observed A09 exchanges are fixed; solve each zone's price root and differentiate
its price and technology dispatch loss through that root. Retrospective only.
"""
import argparse
import json
import time

import numpy as np

from flow_adjusted_zonal_clearing_2025 import DEST
from fast_independent_price_root_2025 import solve as fast_price_root
from monthly_diurnal_splines_2025 import labels
from run_batched_transport_2025 import setup
from supply_knot_splines_2025 import initial_parameters


def train_month(market,s,d,net,covered,month,updates,rate):
    hours=np.flatnonzero(np.datetime64('2025-01','M')+np.arange(12).astype('timedelta64[M]')[month-1]
        ==np.arange('2025-01-01','2026-01-01',dtype='datetime64[h]').astype('datetime64[M]'))
    clock=labels(s['groups'],hours)
    neutral=initial_parameters(market.ng)[:,[0,5,6,7,8,9]]
    weights=np.broadcast_to(neutral,(24,*neutral.shape)).copy()
    initial=weights.copy();m=np.zeros_like(weights);v=np.zeros_like(weights)
    target=market.load[hours]-net[hours]
    cap=market.capacity[hours]@market.Z
    valid=covered[hours]&(target>=0)&(target<=cap)
    obs=d['observed_prices'][hours].copy()
    valid &= np.isfinite(obs);obs=np.where(np.isfinite(obs),obs,0)
    group_zone=market.zone
    # Country technology observations are only scored when every modeled zone
    # in that country has a valid local balance and a source value exists.
    countries=len(s['countries']);techs=len(s['technologies'])
    ci=np.array([g['country_id'] for g in s['groups']]);ti=np.array([s['technologies'].index(g['technology']) for g in s['groups']])
    country_zones=[sorted({g['zone_id'] for g in s['groups'] if g['country_id']==c}) for c in range(countries)]
    country_ok=np.column_stack([valid[:,zs].all(axis=1) if zs else np.zeros(len(hours),bool) for zs in country_zones])
    observed=d['observed_generation'][hours]/1000
    fixed=d['fixed_generation'][hours]/1000
    genmask=np.isfinite(observed)&country_ok[:,:,None]
    obsgen=np.nan_to_num(observed)
    active=(market.capacity[hours]>0).any(axis=0)&~market.zero
    history=[];start=time.perf_counter()
    def clear(weights):
        bids=weights[clock,np.arange(market.ng)]
        offers=market.offers(bids,hours)
        price,quantity,cleared,residual=fast_price_root(market,offers,target,valid)
        return offers,price,quantity,cleared,residual
    def evaluate(weights):
        _,price,quantity,cleared,residual=clear(weights)
        mask=cleared&valid
        actual=fixed.copy()
        for g in range(market.ng):actual[:,ci[g],ti[g]]+=quantity[:,g]
        mixmask=genmask&country_ok[:,:,None]
        return dict(matched_price_cells=int(mask.sum()),
            price_mae=float(abs(price[mask]-obs[mask]).mean()) if mask.any() else None,
            generation_cells=int(mixmask.sum()),
            generation_mae_gw=float(abs(actual[mixmask]-obsgen[mixmask]).mean()) if mixmask.any() else None,
            max_cleared_balance_mw=float(abs(residual[cleared]).max()*1000) if cleared.any() else None)
    before=evaluate(weights)
    for step in range(updates+1):
        offers,price,_,cleared,balance=clear(weights)
        mask=cleared&valid
        q,dq,raw=market.supply(price,offers,parameters=True)
        scaled=np.where(mask,(price-obs)/40,0)
        price_loss=np.sqrt(scaled**2+.01**2)-.01
        n=max(1,int(mask.sum()))
        gp=np.where(mask,scaled/np.sqrt(scaled**2+.01**2)/40/n,0)
        modeled=fixed.copy()
        for g in range(market.ng):modeled[:,ci[g],ti[g]]+=q[:,g]
        error=np.where(genmask,modeled-obsgen,0)
        gen_scaled=error/3
        cells=max(1,int(genmask.sum()))
        gen_loss=np.sqrt(gen_scaled**2+.01**2)-.01
        gc=np.where(genmask,gen_scaled/np.sqrt(gen_scaled**2+.01**2)/3/cells,0)
        gq=gc[:,ci,ti]
        slope=dq@market.Z
        # Implicit function: dP/dtheta = -dQ/dtheta / dQ/dP.
        # A flat aggregate supply leaves the price direction unidentified;
        # retain its error in the score but do not fabricate a gradient.
        identified=mask&(slope>1e-5)
        rhs=gp+(gq*dq)@market.Z
        adjoint=np.divide(rhs,slope,out=np.zeros_like(rhs),where=identified)
        gtheta=(gq-adjoint[:,group_zone])[:,:,None]*raw
        gtheta*=identified[:,group_zone,None]
        gradient=np.zeros_like(weights)
        for g in range(market.ng):np.add.at(gradient[:,g],clock[:,g],gtheta[:,g])
        gradient[:,~active]=0
        delta=weights-initial
        if active.any():gradient[:,active]+=.0002*delta[:,active]/(active.sum()*24*6)
        record=dict(update=step,price_loss=float(price_loss.sum()/n),
                    price_mae=float(abs(price[mask]-obs[mask]).mean()) if mask.any() else None,
                    generation_loss=float(gen_loss.sum()/cells),
                    generation_mae_gw=float(abs(error[genmask]).mean()) if genmask.any() else None,
                    unidentified_price_cells=int((mask&~identified).sum()),
                    matched_price_cells=int(mask.sum()),generation_cells=int(genmask.sum()),
                    seconds=time.perf_counter()-start)
        history.append(record)
        if step==updates:break
        m=.9*m+.1*gradient;v=.999*v+.001*gradient**2;t=step+1
        weights-=rate*(m/(1-.9**t))/(np.sqrt(v/(1-.999**t))+1e-8)
        weights[:,~active]=initial[:,~active]
    after=evaluate(weights)
    summary=dict(month=month,updates=updates,learning_rate=rate,hours=len(hours),
        generation_target_cells=int(genmask.sum()),initial_cleared=before,
        fitted_cleared=after,total_seconds=time.perf_counter()-start,
        initial=history[0],final=history[-1])
    return summary,weights,history


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--updates',type=int,default=100)
    parser.add_argument('--rate',type=float,default=.5)
    parser.add_argument('--months',type=int,nargs='+',default=list(range(1,13)))
    args=parser.parse_args()
    state,market,_,_=setup();s,d,*_=state
    with np.load(DEST/'witness.npz') as z:
        net=z['net_import_gw'];covered=z['covered']
    root=DEST/f'monthly-fit-v1-u{args.updates}-r{args.rate:g}';root.mkdir(exist_ok=True)
    for month in args.months:
        if not 1<=month<=12:raise ValueError('Invalid month')
        path=root/f'month-{month:02d}'
        if (path/'summary.json').exists():
            print('SKIP',month,'existing result',flush=True);continue
        path.mkdir(exist_ok=True)
        summary,weights,history=train_month(market,s,d,net,covered,month,args.updates,args.rate)
        np.savez_compressed(path/'curves.npz',weights=weights)
        (path/'history.json').write_text(json.dumps(history,indent=2)+'\n')
        (path/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        print('MONTH',month,summary,flush=True)


if __name__=='__main__':main()
