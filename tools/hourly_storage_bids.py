"""Divisible storage bids with causal carried stock and cached own-model foresight."""
import numpy as np
from scipy.sparse import coo_matrix,hstack


def validate_assets(assets,zones):
    if len({r['id'] for r in assets})!=len(assets):raise ValueError('Duplicate storage ID')
    for r in assets:
        if r['zone'] not in zones:raise ValueError('Unknown storage zone')
        for k in ['charge_mw','discharge_mw','energy_mwh','eta_charge','eta_discharge','standing_loss']:
            if not np.isfinite(r[k]):raise ValueError('Nonfinite storage parameter')
        if min(r['charge_mw'],r['discharge_mw'],r['energy_mwh'])<=0:raise ValueError('Storage MW/MWh must be positive')
        if not 0<r['eta_charge']<=1 or not 0<r['eta_discharge']<=1 or not 0<=r['standing_loss']<1:raise ValueError('Invalid storage efficiency/loss')


def future_reference(prices,horizon):
    if prices.ndim!=2 or not np.isfinite(prices).all() or horizon<1:raise ValueError('Invalid own-model forecast')
    T=len(prices);out=np.empty_like(prices)
    for t in range(T):out[t]=np.maximum(0,np.median(prices[t+1:min(T,t+1+horizon)] if t+1<T else prices[t:t+1],axis=0))
    return out


def coefficients(assets,zones,energy,reference,margin):
    validate_assets(assets,zones);energy=np.asarray(energy,float)
    if energy.shape!=(len(assets),) or not np.isfinite(energy).all() or margin<=0:raise ValueError('Invalid storage state or margin')
    cap=np.array([r['energy_mwh'] for r in assets]);eta_c=np.array([r['eta_charge'] for r in assets]);eta_d=np.array([r['eta_discharge'] for r in assets]);phi=1-np.array([r['standing_loss'] for r in assets])
    if (energy<0).any() or (energy>cap).any():raise ValueError('Storage state outside physical bounds')
    previous=energy*phi;ref=np.array([reference[zones.index(r['zone'])] for r in assets]);ref=np.maximum(ref,0)
    buy=eta_c*eta_d*ref-margin;sell=ref+margin
    charge=np.minimum([r['charge_mw'] for r in assets],np.maximum(cap-previous,0)/eta_c)
    discharge=np.minimum([r['discharge_mw'] for r in assets],previous*eta_d)
    assert (sell-buy>0).all()
    return dict(buy=buy,sell=sell,charge_max=charge,discharge_max=discharge,previous=previous,capacity=cap,eta_c=eta_c,eta_d=eta_d)


def advance(bids,charge,discharge,tolerance=1e-4):
    charge=np.asarray(charge);discharge=np.asarray(discharge)
    if min(charge.min(initial=0),discharge.min(initial=0)) < -tolerance:raise ValueError('Negative storage dispatch')
    if max(np.maximum(charge-bids['charge_max'],0).max(initial=0),np.maximum(discharge-bids['discharge_max'],0).max(initial=0))>tolerance:raise ValueError('Storage power/energy bound violated')
    if np.minimum(charge,discharge).max(initial=0)>1e-6:raise ValueError('Simultaneous storage cycling')
    e=bids['previous']+charge*bids['eta_c']-discharge/bids['eta_d']
    error=max(np.maximum(-e,0).max(initial=0),np.maximum(e-bids['capacity'],0).max(initial=0))
    if error>tolerance:raise ValueError('Storage inventory violation')
    corrected=np.clip(e,0,bids['capacity']);correction=float(abs(corrected-e).max(initial=0))
    return corrected,correction


def matrix(original,assets,zones):
    validate_assets(assets,zones);S=len(assets);rr=[zones.index(r['zone']) for r in assets];cols=np.arange(S)
    charge=coo_matrix((-np.ones(S),(rr,cols)),shape=(original.shape[0],S)).tocsc()
    return hstack([original,charge,-charge],format='csc')


def certificate(A,c,lower,upper,row_lower,row_upper,x,y):
    ax=A@x;rc=c-A.T@y;finite_l=np.isfinite(lower);finite_u=np.isfinite(upper);rl=np.isfinite(row_lower);ru=np.isfinite(row_upper)
    primal=float(max(np.maximum(lower-x,0).max(initial=0),np.maximum(x-upper,0).max(initial=0),np.maximum(row_lower-ax,0).max(initial=0),np.maximum(ax-row_upper,0).max(initial=0)))
    signs=float(max(np.maximum(rc[~finite_l],0).max(initial=0),np.maximum(-rc[~finite_u],0).max(initial=0),np.maximum(y[~rl],0).max(initial=0),np.maximum(-y[~ru],0).max(initial=0)))
    dual=float(np.maximum(y[rl],0)@row_lower[rl]+np.minimum(y[ru],0)@row_upper[ru]+np.maximum(rc[finite_l],0)@lower[finite_l]+np.minimum(rc[finite_u],0)@upper[finite_u])
    gap=abs(float(c@x)-dual)
    comp=float(max(abs(np.maximum(y[rl],0)*(ax[rl]-row_lower[rl])).max(initial=0),abs(np.minimum(y[ru],0)*(ax[ru]-row_upper[ru])).max(initial=0),abs(np.maximum(rc[finite_l],0)*(x[finite_l]-lower[finite_l])).max(initial=0),abs(np.minimum(rc[finite_u],0)*(x[finite_u]-upper[finite_u])).max(initial=0)))
    if primal>1e-4 or signs>=1e-5 or gap>=.05 or comp>=.05:raise ValueError(f'Hourly storage certificate failed: {primal,signs,gap,comp}')
    return dict(primal_mw=primal,signs_eur_mwh=signs,duality_gap_eur=gap,complementarity_eur=comp)
