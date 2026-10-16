"""Bounded hourly supply-bid corrections; no evaluation prices at inference."""
import numpy as np
import pandas as pd

FIT, SELECT = 2880, 4344
GRID = [[0., 0.], [.5, 0.], [0., .5], [.5, .5], [1., 1.]]
TIMEZONES = {
    'AL':'Europe/Tirane','AT':'Europe/Vienna','BA':'Europe/Sarajevo','BE':'Europe/Brussels',
    'BG':'Europe/Sofia','CH':'Europe/Zurich','CZ':'Europe/Prague','DE':'Europe/Berlin',
    'DK':'Europe/Copenhagen','EE':'Europe/Tallinn','ES':'Europe/Madrid','FI':'Europe/Helsinki',
    'FR':'Europe/Paris','GB':'Europe/London','GR':'Europe/Athens','HR':'Europe/Zagreb',
    'HU':'Europe/Budapest','IE':'Europe/Dublin','IT':'Europe/Rome','LT':'Europe/Vilnius',
    'LU':'Europe/Luxembourg','LV':'Europe/Riga','ME':'Europe/Podgorica','MK':'Europe/Skopje',
    'NL':'Europe/Amsterdam','NO':'Europe/Oslo','PL':'Europe/Warsaw','PT':'Europe/Lisbon',
    'RO':'Europe/Bucharest','RS':'Europe/Belgrade','SE':'Europe/Stockholm','SI':'Europe/Ljubljana',
    'SK':'Europe/Bratislava','XK':'Europe/Belgrade'}
DESIGN = dict(
    periods=dict(fit='Jan–Apr [0,2880)',selection='May–Jun [2880,4344)',evaluation='Jul–Dec [4344,8760)'),
    reference='Existing selected resource curves [0,.5,0]; unchanged original physical baseline kept separately',
    residual='Prepared zonal demand minus fixed reservoir injection minus available wind/solar MW, not observed or dispatched generation',
    features='Within-UTC-day residual anomaly / max(Jan–Apr anomaly SD,1 MW), clipped +/-3; local-time sine/cosine first two daily harmonics, with DST, individually demeaned within each UTC day',
    proposal='Per-zone ridge regression on complete Jan–Apr UTC days: observed-minus-prior-price error demeaned daily and clipped +/-100 EUR/MWh; ridge 168 I, no intercept; at least 168 known hours, otherwise zero coefficients',
    inference='No evaluation prices: features use only model inputs and calendar; perfect exogenous daily forecasts assumed. No learned availability or timestamp shifting.',
    grid=GRID,
    offers='Gas/coal/lignite all blocks receive clip(residual strength*residual term + calendar strength*calendar term, +/-30 EUR/MWh); nuclear receives one quarter (max +/-7.5); final offers floored at zero. Preserve monotone blocks and MW. All other bids unchanged.',
    selection='Evaluate exactly five fixed pairs on May–June; include unchanged prior [0,0]; no shortlist, refit or adaptive expansion',
    objective='Equal mean of prior-normalized hourly price MAE, daily-demeaned MAE, monthly generation-interval error, implied-trade interval error; plus .02*mean((Jan–Apr clipped hourly shift/30)^2)',
    ties='Score within 1e-12: lower penalty then earlier grid index',
    scope='Daily features change hourly bids, not ramp/commitment constraints or hydro; independent hourly LPs batched by day. Fixed water, capacity, GSK, demand and physical rows.',
    caveat='Previously inspected 2025; retrospective temporal experiment, not untouched validation, recovered actual bids or automatic acceptance')


def demean(values):
    x=np.asarray(values,float)
    return (x.reshape(-1,24,*x.shape[1:])-x.reshape(-1,24,*x.shape[1:]).mean(axis=1,keepdims=True)).reshape(x.shape)


def features(m,layout):
    residual=m['load'].copy()
    for j,kind in enumerate(layout['kinds']):
        if kind=='renewable':residual[:,m['zones'].index(m['offer_zones'][j])]-=m['availability'][:,j]
    anomaly=demean(residual);scale=np.maximum(anomaly[:FIT].std(axis=0),1.)
    x=np.zeros((8760,m['nz'],5));x[:,:,0]=np.clip(anomaly/scale,-3,3)
    clock=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC')
    for j,z in enumerate(m['zones']):
        h=clock.tz_convert(TIMEZONES[z[:2]]).hour.to_numpy()
        x[:,j,1:]=np.column_stack([fun(2*np.pi*k*h/24) for k in [1,2] for fun in [np.sin,np.cos]])
    # Clipping can introduce a daily mean: remove it consistently in both groups.
    return demean(x),scale,residual


def fit_proposal(x,prior,observed):
    if x.shape[0]!=FIT or prior.shape!=observed.shape or len(prior)!=FIT:
        raise ValueError('Proposal accepts January–April only')
    beta=np.zeros((x.shape[1],5));counts=[]
    for j in range(x.shape[1]):
        good=np.isfinite(observed[:,j]).reshape(-1,24).all(axis=1).repeat(24)
        counts.append(int(good.sum()))
        if good.sum()<168:continue
        delta=observed[:,j]-prior[:,j]
        response=np.clip(demean(delta)[good],-100,100)
        a=x[good,j]
        beta[j]=np.linalg.solve(a.T@a+168*np.eye(5),a.T@response)
    return beta,counts


def shift(x,beta,params):
    if list(params) not in GRID:raise ValueError('Outside predeclared intraday grid')
    a,b=params
    return np.clip(a*x[:,:,0]*beta[:,0]+b*np.einsum('tzk,zk->tz',x[:,:,1:],beta[:,1:]),-30,30)


def costs(anchor,m,layout,hourly):
    if hourly.shape!=(8760,m['nz']) or not np.isfinite(hourly).all() or abs(hourly).max()>30+1e-9:
        raise ValueError('Invalid bounded hourly offer shifts')
    out=anchor.copy()
    for j,kind in enumerate(layout['kinds']):
        if kind in ['gas','coal','nuclear']:
            z=m['zones'].index(m['offer_zones'][j]);factor=.25 if kind=='nuclear' else 1.
            out[:,j]=np.maximum(0,out[:,j]+factor*hourly[:,z])
    return out


def penalty(hourly):return .02*float(np.mean((hourly[:FIT]/30.)**2))
