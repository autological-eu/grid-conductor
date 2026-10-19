"""Bounded smooth inverse-bid proposals and deterministic finite-fit ensemble rules."""
import hashlib,json
import numpy as np
from generation_mix_2025 import ROOT,MONTH,allocate

PLAN=ROOT/'config/inverse-bid-ensemble-2025.json'
FAMILIES=['gas','coal','nuclear']
FUELS=['Wind','Solar','Nuclear','Gas','Coal']


def zero(nz,nc):return dict(price=np.zeros((nz,3,5)),mix=np.zeros((nc,3)),curve=np.zeros(2))


def proposal(m,layout,features,season,cost,values,prices,observed,monthly,target,design):
    beta=np.zeros((m['nz'],3,5));counts=np.zeros((m['nz'],3),int);cfg=design['price_proposal']
    interior=(values[:,:m['ng']]>cfg['interior_margin_mw'])&(m['availability']-values[:,:m['ng']]>cfg['interior_margin_mw'])
    for zi,z in enumerate(m['zones']):
        for fi,family in enumerate(FAMILIES):
            ids=[j for j,k in enumerate(layout['kinds']) if k==family and m['offer_zones'][j]==z]
            if not ids:continue
            good=np.isfinite(observed[:,zi])&np.any(interior[:,ids]&(abs(cost[:,ids]-prices[:,zi,None])<=cfg['price_match_eur_mwh']),axis=1);counts[zi,fi]=good.sum()
            if good.sum()<cfg['minimum_local_interior_hours']:continue
            x=features[good,zi,:];y=np.clip(observed[good,zi]-prices[good,zi],-cfg['target_clip_eur_mwh'],cfg['target_clip_eur_mwh'])
            beta[zi,fi]=np.linalg.solve(x.T@x+cfg['ridge']*np.eye(5),x.T@y)
    mix=np.zeros((target['generation'].shape[1],3));known=np.zeros_like(mix,dtype=bool)
    lower=np.array([r['generation_lower_twh'] for r in monthly]);upper=np.array([r['generation_upper_twh'] for r in monthly])
    for ci in range(len(mix)):
        for fi,fuel in enumerate(['Gas','Coal','Nuclear']):
            k=FUELS.index(fuel);r=target['generation'][:,ci,k]
            if not np.isfinite(r).all():continue
            known[ci,fi]=True;v=r.sum();gap=v-np.clip(v,lower[:,ci,k].sum(),upper[:,ci,k].sum())
            mix[ci,fi]=np.clip(-15*gap/max(v,1),-15,15)
    return dict(price=beta,mix=mix,support_hours=counts,complete_mix_targets=known)


def advance(parent,prop,step,design):
    a,b,c=step
    return dict(price=np.array(parent['price'])+a*np.array(prop['price']),
                mix=np.clip(np.array(parent['mix'])+b*np.array(prop['mix']),-np.array(design['maximum_accumulated_mix_eur_mwh']),np.array(design['maximum_accumulated_mix_eur_mwh'])),
                curve=np.clip(np.array(parent['curve'])+c,0,1))


def costs(m,layout,accepted,features,shares,state,design):
    price=np.einsum('tzk,zfk->tzf',features,np.asarray(state['price']));mix=np.asarray(state['mix']);out=accepted.copy()
    for j,family in enumerate(layout['kinds']):
        if family not in FAMILIES:continue
        fi=FAMILIES.index(family);zi=m['zones'].index(m['offer_zones'][j]);bound=design['maximum_total_shift_eur_mwh'][fi]
        shift=price[:,zi,fi]+mix[:,fi]@shares[j]
        out[:,j]+=np.clip(shift,-bound,bound)
        if fi<2:out[:,j]+=float(state['curve'][fi])*design['thermal_curve_top_eur_mwh'][fi]*design['thermal_curve_rank_multipliers'][layout['ranks'][j]]
        out[:,j]=np.maximum(out[:,j],0)
    return out


def fingerprint(cost):return hashlib.sha256(np.ascontiguousarray(cost).tobytes()).hexdigest()


def penalty(m,layout,accepted,cost):
    numerator=denominator=0.
    for j,family in enumerate(layout['kinds']):
        if family not in FAMILIES:continue
        bound=dict(gas=105.,coal=85.,nuclear=15.)[family];a=m['availability'][:,j]
        numerator+=float((a*((cost[:,j]-accepted[:,j])/bound)**2).sum());denominator+=float(a.sum())
    return numerator/denominator if denominator else 0.


def record_score(metrics,reference,regularization,design):
    norm={k:float(metrics[k]/max(reference[k],1e-12)) for k in reference}
    weights=design['objective_weights'];score=sum(weights[k]*norm[k] for k in weights)+design['regularization_weight']*regularization
    bounds=design['research_filters'];ok=norm['price']<=bounds['price_ratio_maximum']+1e-12 and all(norm[k]<=bounds[b]+1e-12 for k,b in [('daily_demeaned_price','daily_demeaned_ratio_maximum'),('generation','generation_ratio_maximum'),('trade','trade_ratio_maximum')])
    return dict(score=float(score),penalty=float(regularization),normalized=norm,eligible=bool(ok))


def best(records):return min((r for r in records if r['eligible']),key=lambda r:(r['score'],r['penalty'],r['ordinal']))


def vector(state):return np.r_[np.asarray(state['price']).ravel()/45,np.asarray(state['mix']).ravel()/30,np.asarray(state['curve'])]


def ensemble(records,states,design):
    winner=best(records);rule=design['ensemble'];pool=[r for r in records if r['eligible'] and r['score']<=winner['score']+rule['score_tolerance']+1e-12 and r['metrics']['price']<=winner['metrics']['price']+rule['price_tolerance_eur_mwh']+1e-12]
    selected=[winner['id']];pool=[r for r in pool if r['id']!=winner['id']]
    while pool and len(selected)<rule['maximum_members']:
        def key(r):
            v=vector(states[r['id']]);distance=min(float(np.mean((v-vector(states[k]))**2)) for k in selected)
            return (-distance,r['score'],r['ordinal'])
        r=min(pool,key=key);selected.append(r['id']);pool.remove(r)
    return selected


def fuel_points(ctx,values):
    point,_,_,_=allocate(ctx['availability'],values[:,:len(ctx['groups'])],ctx['groups'],ctx['generation_keys'],ctx['generation_labels'])
    point=point.reshape(8760,len(ctx['countries']),5)
    return np.array([point[MONTH==k].sum(axis=0)/1e6 for k in range(1,13)])
