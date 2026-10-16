"""Seasonal/local-clock supply bids, with no residual-demand predictor."""
import numpy as np
import pandas as pd
from generation_mix_2025 import MONTH
from intraday_offer_bids_2025 import TIMEZONES

FAMILIES=['gas','coal','nuclear']
DESIGN=dict(
    variants=['unchanged','calendar','calendar_ember'],
    features='15 calendar-only columns: intercept, annual sine/cosine, local-clock first/second daily sine/cosine, and their annual sine/cosine interactions. DST applied. No demand, residual demand or observed generation as hourly predictors.',
    fit='Per zone ridge 168 I; clip observed-minus-uncalibrated-control price error +/-100 EUR/MWh; training months only, exclude first/last 48 hours of those months; at least 168 known hours otherwise zero.',
    ember='Training months only: signed observed generation outside baseline conditional allocation interval / max(observed TWh,.25); negative 30 times that fraction, clipped +/-30 EUR/MWh. Fit country/resource annual intercept+sine+cosine with ridge I. Gas/coal/nuclear only; national signals weighted by original nameplate membership of each compiled offer.',
    bids='Original fuel/efficiency/carbon/VOM bids plus clipped calendar [+ Ember] correction, +/-30 EUR/MWh for gas/coal, quarter strength +/-7.5 nuclear; floor final bid at zero. Other resources unchanged; no inherited fitted thermal step markups.',
    folds='Three seasonal rotations: test months 1/4/7/10, 2/5/8/11, 3/6/9/12. Selection is the next rotation; fitting is the remaining rotation. Whole months never split between these roles within a fold.',
    purge='Exclude first/last 48 hours of each fitting/selection month from price fitting/scoring. Ember comparisons retain whole fitting/selection months; test-month Ember never enters fitting/selection.',
    selection='Exactly three variants per fold, equal mean of selection errors normalized by unchanged control: hourly MAE, daily-demeaned MAE, generation interval error, implied-trade interval error; plus .01 times mean squared effective training offer shift /30 over nonzero-capacity gas/coal/nuclear columns. Ties within 1e-12 prefer earlier/simpler variant.',
    refit='Final reconstruction variant is the mode of the three inner-selection winners, ties prefer simpler variant. Refit coefficients using all 2025 price/Ember targets; final accuracy is in-sample and separate from out-of-fold validation.',
    scope='Previously inspected 2025; retrospective season-spanning interpolation, NOT untouched or future-year forecasting validation. Each test month excludes its price/generation targets from its fitting and selection. All eligible areas retained.',
    fixed='Source demand, original available MW, fixed hydro chronology, grid/GSK and capacities unchanged; independent hourly LPs, no new storage/commitment or market acceptance.',
    metrics='Primary all-8760 out-of-fold composite: three different fold fits, not a single deployed annual policy. Final all-year reconstruction is separately labelled. Ramps exclude changes between fold fits.')


def calendar(zones):
    times=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC')
    a=2*np.pi*(np.arange(8760)+.5)/8760
    season=np.column_stack([np.ones(8760),np.sin(a),np.cos(a)])
    x=np.zeros((8760,len(zones),15));x[:,:,:3]=season[:,None,:]
    for j,z in enumerate(zones):
        h=times.tz_convert(TIMEZONES[z[:2]]).hour.to_numpy()
        daily=np.column_stack([f(2*np.pi*k*h/24) for k in [1,2] for f in [np.sin,np.cos]])
        x[:,j,3:7]=daily;x[:,j,7:11]=daily*season[:,1,None];x[:,j,11:15]=daily*season[:,2,None]
    return x,season


def fold_months(index):
    cohorts=[list(range(k+1,13,3)) for k in range(3)]
    return dict(fit=cohorts[(index+2)%3],selection=cohorts[(index+1)%3],test=cohorts[index])


def interior(months):
    mask=np.isin(MONTH,months)
    for month in months:
        ids=np.flatnonzero(MONTH==month);mask[ids[:48]]=False;mask[ids[-48:]]=False
    return mask


def proposals(x,season,prices,observed,monthly,target,months):
    mask=interior(months);beta=np.zeros((x.shape[1],15));counts=[]
    for j in range(x.shape[1]):
        good=mask&np.isfinite(observed[:,j]);counts.append(int(good.sum()))
        if good.sum()<168:continue
        a=x[good,j];b=np.clip(observed[good,j]-prices[good,j],-100,100)
        beta[j]=np.linalg.solve(a.T@a+168*np.eye(15),a.T@b)
    nc=target['generation'].shape[1];gamma=np.zeros((nc,3,3));used=np.zeros((nc,3),int)
    for c in range(nc):
        for k,fuel in enumerate(['Gas','Coal','Nuclear']):
            fi=['Wind','Solar','Nuclear','Gas','Coal'].index(fuel);rows=[];values=[]
            for month in months:
                ref=target['generation'][month-1,c,fi]
                if not np.isfinite(ref):continue
                row=monthly[month-1];lo=row['generation_lower_twh'][c,fi];hi=row['generation_upper_twh'][c,fi]
                gap=ref-np.clip(ref,lo,hi)
                values.append(np.clip(-30*gap/max(ref,.25),-30,30));rows.append(season[MONTH==month].mean(axis=0))
            used[c,k]=len(rows)
            if rows:
                a=np.asarray(rows);gamma[c,k]=np.linalg.solve(a.T@a+np.eye(3),a.T@values)
    return beta,gamma,counts,used


def country_shares(n,layout,countries):
    result=np.zeros((len(layout['members']),len(countries)))
    for j,ids in enumerate(layout['members']):
        for i in ids:
            g=n.generators.iloc[i];c=n.buses.loc[g.bus,'country']
            result[j,countries.index(c)]+=g.p_nom
        if result[j].sum():result[j]/=result[j].sum()
    return result


def bids(m,layout,x,season,beta,gamma,shares,variant):
    if variant not in range(3):raise ValueError('Outside fixed variant design')
    result=m['cost'].astype(float,copy=True)
    if variant==0:return result
    clock=np.einsum('tzk,zk->tz',x,beta);national=np.einsum('tk,cfk->tcf',season,gamma)
    for j,family in enumerate(layout['kinds']):
        if family not in FAMILIES:continue
        d=clock[:,m['zones'].index(m['offer_zones'][j])].copy()
        if variant==2:d+=national[:,:,FAMILIES.index(family)]@shares[j]
        d=np.clip(d,-30,30)*(.25 if family=='nuclear' else 1.)
        result[:,j]=np.maximum(result[:,j]+d,0)
    return result
