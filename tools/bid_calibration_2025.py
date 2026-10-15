"""Bounded training-only bid adders; all physical inputs remain immutable."""
import json
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,MONTH,CARRIER,EMBER,allocate,digest,ember_rows
from compare_native_exchange_reference import CODES
from compare_daily_dispatch_prices import metrics

NTRAIN=4344
NAMES=['gas','coal','nuclear']
LEVELS=[[-30.,0.,30.],[-30.,0.,30.],[-15.,0.,15.]]
FUELS=['Wind','Solar','Nuclear','Gas','Coal']
DESIGN=dict(training='2025-01-01 through 2025-06-30 UTC: 4344 hours; quantities months 1–6',
    evaluation='2025-07-01 through 2025-12-31 UTC: 4416 hours; quantities months 7–12; no refit',
    parameters=dict(zip(NAMES,LEVELS)),units='Additive EUR/MWh electricity to existing fuel/efficiency/carbon/VOM offers; global by resource',
    search='Exactly two coordinate sweeps, gas then coal then nuclear; all three declared levels at each coordinate; cache identical tuples; no adaptive bounds or split search',
    objective='Mean of training price, generation and trade errors divided by their uncalibrated training values, plus 0.05 * mean squared adders normalized by search bounds',
    price='Equal-zone mean MAE across every eligible A44 area',
    generation='Mean country/fuel/month distance of Ember TWh from saved-group allocation interval / max(reference TWh,0.25); Wind/Solar/Nuclear/Gas/Coal only',
    trade='Mean country/month distance of signed Ember net exports from implied generation-minus-demand allocation interval / max(model demand TWh,1)',
    unknown='Missing references excluded with counts; infeasible generation targets retained and flagged against original availability, never imposed or used to change capacity',
    selection='Training objective only; ties within 1e-12 choose smaller squared adders then lexicographic tuple. Baseline remains a selectable control.',
    scope='Retrospective temporal experiment: 2025 already inspected. Effective bids may compensate for incorrect inputs/constraints; no uniquely recovered bids or acceptance',
    fixed='Same whole European PTDF/GSK/island/link model, demand, original availability and fixed hydro; no rolling-storage restart, renewable scaling or topology change',
    interpretation='Objective weights, normalization floors and finite parameter bounds are experimental settings, not empirical acceptance gates')


def classify(carrier):
    return 'gas' if carrier in ['CCGT','OCGT'] else 'coal' if carrier in ['coal','lignite'] else 'nuclear' if carrier=='nuclear' else None


def prepare(n,m,raw_cost,fixed):
    countries=sorted(n.buses.country.unique());groups={};gkeys=[];ckeys=[]
    fmap={f:fuel for fuel in FUELS for f in EMBER[fuel]}
    for j,(_,g) in enumerate(n.generators.iterrows()):
        groups.setdefault((m['buszone'][g.bus],raw_cost[:,j].tobytes(),g.carrier=='emergency'),[]).append(j)
        country=n.buses.loc[g.bus,'country'];family=CARRIER[g.carrier]
        gkeys.append((country,fmap[family]) if family in fmap else None)
        ckeys.append(country if family!='emergency' else None)
    groups=list(groups.values());classes=[]
    assert len(groups)==m['ng']
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    for k,ids in enumerate(groups):
        kinds={classify(n.generators.iloc[i].carrier) for i in ids};assert len(kinds)==1,'Mixed calibration class in merged offer'
        classes.append(next(iter(kinds)))
        np.testing.assert_allclose(m['availability'][:,k],av[:,ids].sum(axis=1),atol=1e-7,rtol=1e-12)
        np.testing.assert_array_equal(m['cost'][:,k],raw_cost[:,ids[0]])
    demand=np.zeros((8760,len(countries)));hydro=np.zeros_like(demand)
    loads=n.get_switchable_as_dense('Load','p_set')
    for j,c in enumerate(countries):
        buses=n.buses.index[n.buses.country==c];hydro[:,j]=fixed[buses].sum(axis=1)
        demand[:,j]=loads[n.loads.index[n.loads.bus.isin(buses)]].sum(axis=1)
    return dict(countries=countries,groups=groups,generation_keys=gkeys,country_keys=ckeys,
                generation_labels=[(c,f) for c in countries for f in FUELS],classes=classes,
                availability=av,demand=demand,hydro=hydro)


def bids(base_cost,classes,params):
    if len(params)!=3 or any(float(value) not in levels for value,levels in zip(params,LEVELS)):
        raise ValueError('Outside predeclared finite bid experiment')
    delta=np.array([0. if c is None else params[NAMES.index(c)] for c in classes])
    result=base_cost+delta
    if not np.isfinite(result).all() or (result<0).any():raise ValueError('Nonfinite or negative anchored bid')
    return result


def month_quantities(context,values,start):
    T=len(values);stop=start+T
    _,gl,gu,_=allocate(context['availability'][start:stop],values[:,:len(context['groups'])],context['groups'],context['generation_keys'],context['generation_labels'])
    cp,cl,cu,_=allocate(context['availability'][start:stop],values[:,:len(context['groups'])],context['groups'],context['country_keys'],context['countries'])
    for v in [cp,cl,cu]:v+=context['hydro'][start:stop]
    shape=(T,len(context['countries']),len(FUELS));gl=gl.reshape(shape);gu=gu.reshape(shape)
    result=[]
    for month in sorted(set(MONTH[start:stop])):
        mask=MONTH[start:stop]==month
        result.append(dict(month=int(month),generation_lower_twh=gl[mask].sum(axis=0)/1e6,generation_upper_twh=gu[mask].sum(axis=0)/1e6,
            generation_point_twh=cp[mask].sum(axis=0)/1e6,net_export_lower_twh=(cl[mask]-context['demand'][start:stop][mask]).sum(axis=0)/1e6,
            net_export_upper_twh=(cu[mask]-context['demand'][start:stop][mask]).sum(axis=0)/1e6,
            net_export_point_twh=(cp[mask]-context['demand'][start:stop][mask]).sum(axis=0)/1e6,
            demand_twh=context['demand'][start:stop][mask].sum(axis=0)/1e6))
    return result


def targets(prices,countries,months,bank):
    start=0 if months[0]==1 else NTRAIN;stop=NTRAIN if months[-1]==6 else 8760
    generation=np.full((len(months),len(countries),len(FUELS)),np.nan);trade=np.full((len(months),len(countries)),np.nan)
    for t,month in enumerate(months):
        for j,c in enumerate(countries):
            for k,f in enumerate(FUELS):
                value=bank.get((CODES.get(c),f,month))
                if value is not None:generation[t,j,k]=value
            imp=bank.get((CODES.get(c),'Net imports',month))
            if imp is not None:trade[t,j]=-imp
    return dict(prices=prices[start:stop].copy(),generation=generation,trade=trade,months=np.array(months))


def distance(reference,lo,hi):
    return np.maximum(np.maximum(lo-reference,reference-hi),0.)


def loss(prices,monthly,target):
    if prices.shape!=target['prices'].shape:raise ValueError('Price target period mismatch')
    price=[]
    for j in range(prices.shape[1]):
        good=np.isfinite(target['prices'][:,j]);
        if good.any():price.append(float(abs(prices[good,j]-target['prices'][good,j]).mean()))
    lo=np.stack([r['generation_lower_twh'] for r in monthly]);hi=np.stack([r['generation_upper_twh'] for r in monthly]);ref=target['generation']
    assert [r['month'] for r in monthly]==target['months'].tolist()
    known=np.isfinite(ref);g=distance(ref,lo,hi)/np.maximum(ref,.25)
    tlo=np.stack([r['net_export_lower_twh'] for r in monthly]);thi=np.stack([r['net_export_upper_twh'] for r in monthly]);tr=target['trade'];tk=np.isfinite(tr)
    norm=np.maximum(np.stack([r['demand_twh'] for r in monthly]),1.)
    return dict(price=float(np.mean(price)),generation=float(g[known].mean()),trade=float((distance(tr,tlo,thi)/norm)[tk].mean()),
                price_areas=len(price),generation_targets=int(known.sum()),trade_targets=int(tk.sum()))


def score(raw,baseline,params):
    components=[raw[k]/max(baseline[k],1e-9) for k in ['price','generation','trade']]
    reg=.05*float(np.mean((np.array(params)/[30.,30.,15.])**2))
    return float(np.mean(components)+reg)


def choose(records):
    good=[r for r in records if r['score'] is not None]
    best=min(r['score'] for r in good)
    return min([r for r in good if r['score']<=best+1e-12],key=lambda r:(sum((v/b)**2 for v,b in zip(r['params'],[30,30,15])),tuple(r['params'])))


def summaries(prices,target,zones,monthly,countries):
    rows=[dict(zone=z,**metrics(prices[:,j],target['prices'][:,j])) for j,z in enumerate(zones)]
    eligible=[r for r in rows if r['known_hours']];cor=[r['correlation'] for r in eligible if r['correlation'] is not None]
    quantities=[]
    for t,r in enumerate(monthly):
        for j,c in enumerate(countries):
            for k,f in enumerate(FUELS):
                ref=target['generation'][t,j,k]
                quantities.append(dict(country=c,fuel=f,month=r['month'],reference_twh=float(ref) if np.isfinite(ref) else None,
                    lower_twh=float(r['generation_lower_twh'][j,k]),upper_twh=float(r['generation_upper_twh'][j,k])))
    return dict(equal_zone_mae=float(np.mean([r['mae_eur_mwh'] for r in eligible])),mean_zonal_correlation=float(np.mean(cor)),zones=rows,
                objective_components=loss(prices,monthly,target),generation=quantities)


def immutable_hashes(m,offsets):
    arrays={k:m[k] for k in ['availability','load','link_min','link_max','island_rhs','ratings']}
    arrays.update(offsets=offsets,A_data=m['A'].data,A_indices=m['A'].indices,A_indptr=m['A'].indptr)
    import hashlib
    return {k:hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest() for k,v in arrays.items()}|dict(weights=hashlib.sha256(json.dumps(m['weights'],sort_keys=True).encode()).hexdigest())
