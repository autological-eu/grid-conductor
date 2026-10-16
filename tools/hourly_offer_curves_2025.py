"""Resource-specific, capacity-conserving offers and hourly price-shape metrics."""
import numpy as np
import pandas as pd
from bid_calibration_2025 import loss
from compare_daily_dispatch_prices import metrics

FIT=2880
SELECT=4344
NAMES=['gas','coal','nuclear']
BOUNDS=np.array([30.,30.,15.])
DESIGN=dict(
    periods=dict(fit='January–April: hours [0,2880)',selection='May–June: [2880,4344)',evaluation='July–December: [4344,8760)'),
    caveat='All 2025 has been inspected; retrospective chronological evaluation, not untouched validation or empirical acceptance',
    blocks='Gas and coal/lignite 50/35/15%; nuclear and other resources unsplit; wind/solar 50/50%. Preserve original physical columns and summed available MW.',
    anchors='Existing plant fuel/efficiency/carbon/VOM profiles. Thermal/nuclear max(0,anchor+offset+block adder); negative adjustment only on renewable lower half.',
    offset='Per zone/resource median observed-minus-control error in Jan–April local interior hours (>0.001 MW from both bounds, cost/price within 1e-5); shrink n/(n+168); bounds gas/coal/nuclear +/-30/30/15 EUR/MWh',
    thermal_grid='Joint Cartesian product offset strength [0,0.5,1] and thermal strength [0,0.5,1], nine fixed tuples; gas top-block maximum 120, coal 90 EUR/MWh; middle adder 35% of top, lower zero. Nuclear has no peaking block.',
    selection='Shortlist best two nonzero thermal tuples by fitting score plus zero control, then select on May–June score; do not refit the proposal. Ties <=1e-12 prefer penalty then earlier index.',
    renewable_grid='Keep selected thermal parameters; test lower-half renewable discounts [0,10,30] EUR/MWh, all fitted and May–June scored; zero remains selectable. These are synthetic effective offers, not measured subsidy entitlements.',
    budget='At most eleven non-control fit solves, four selection solves, and two selected annual solves; identical states reuse witnesses. No adaptive grid expansion.',
    objective='Equal mean of control-normalized price MAE, daily-demeaned price MAE, generation interval error and implied-trade interval error, plus regularization 0.05*(offset mean-square/bounds + thermal strength squared + (renewable discount/30)^2)',
    quantities='Existing monthly country/fuel and implied-generation-minus-demand export intervals/floors, with missing values unknown. Infeasible source generation targets stay soft checks.',
    fixed='No new capacity, hourly availability correction, hydro rescheduling, minimum output, ramping/unit commitment, storage restart, grid/GSK or demand change. Independent hourly LPs grouped by day.',
    diagnostics='All eligible zones; UTC complete-day shape/range/ramp/tail metrics; local-time profiles with DST for ES/FR; residual bands set on Jan–April; input timing/flat availability flags are not proven corrections',
    acceptance='Experimental weights, blocks and bounds, not product acceptance gates; no automatic baseline/browser promotion')


def kind(key):
    if key is None:return 'other'
    return {'Wind':'renewable','Solar':'renewable','Gas':'gas','Coal':'coal','Nuclear':'nuclear'}.get(key[1],'other')


def compile_curves(base,context):
    parent=[];fractions=[];kinds=[];ranks=[];members=[];groups=[];origin=[];shares=[]
    for k,ids in enumerate(context['groups']):
        for family in sorted({kind(context['generation_keys'][i]) for i in ids}):
            source=[i for i in ids if kind(context['generation_keys'][i])==family]
            fs=[.5,.35,.15] if family in ['gas','coal'] else [.5,.5] if family=='renewable' else [1.]
            for rank,fraction in enumerate(fs):
                parent.append(k);fractions.append(fraction);kinds.append(family);ranks.append(rank);members.append(source)
                groups.append(list(range(len(origin),len(origin)+len(source))));origin.extend(source);shares.extend([fraction]*len(source))
    parent=np.array(parent);m=base.copy();m['ng']=len(parent)
    m['A']=base['A'][:,np.r_[parent,np.arange(base['ng'],base['A'].shape[1])]].tocsc()
    m['availability']=np.column_stack([context['availability'][:,ids].sum(axis=1)*f for ids,f in zip(members,fractions)])
    m['cost']=base['cost'][:,parent].copy()
    for field in ['offer_zones','emergency_mask']:m[field]=base[field][parent]
    ctx=context.copy();ctx['groups']=groups;ctx['availability']=context['availability'][:,origin]*shares
    for field in ['generation_keys','country_keys']:ctx[field]=[context[field][i] for i in origin]
    ctx['classes']=[k if k in NAMES else None for k in kinds]
    layout=dict(parent=parent.tolist(),fractions=fractions,kinds=kinds,ranks=ranks,members=members)
    return m,ctx,layout


def offer_costs(m,layout,direction,params):
    a,b,d=map(float,params)
    if a not in [0,.5,1] or b not in [0,.5,1] or d not in [0,10,30]:raise ValueError('Outside declared finite experiment')
    if direction.shape!=(m['nz'],3) or not np.isfinite(direction).all() or (abs(direction)>BOUNDS+1e-9).any():raise ValueError('Invalid zonal direction')
    out=m['cost'].copy()
    for j,(family,rank) in enumerate(zip(layout['kinds'],layout['ranks'])):
        if family in NAMES:
            z=m['zones'].index(m['offer_zones'][j]);shift=a*direction[z,NAMES.index(family)]
            slope=b*{'gas':120.,'coal':90.}.get(family,0.)*[0,.35,1][rank]
            out[:,j]=np.maximum(out[:,j]+shift+slope,0.)
        elif family=='renewable' and rank==0:out[:,j]-=d
    return out


def offset_direction(m,layout,x,p,observed):
    if len(x)!=FIT or observed.shape!=p.shape or len(p)!=FIT:raise ValueError('Proposal must use January–April only')
    result=np.zeros((m['nz'],3));evidence=[]
    for z,zone in enumerate(m['zones']):
        for f,family in enumerate(NAMES):
            ids=[j for j,k in enumerate(layout['kinds']) if k==family and m['offer_zones'][j]==zone]
            good=np.zeros(FIT,bool)
            for j in ids:good|=(x[:,j]>.001)&(m['availability'][:FIT,j]-x[:,j]>.001)&(abs(m['cost'][:FIT,j]-p[:,z])<=1e-5)
            good&=np.isfinite(observed[:,z]);count=int(good.sum())
            value=float(np.clip(np.median(observed[good,z]-p[good,z])*count/(count+168),-BOUNDS[f],BOUNDS[f])) if count else 0.
            result[z,f]=value;evidence.append(dict(zone=zone,resource=family,hours=count,offset_eur_mwh=value))
    return result,evidence


def shape_metrics(model,observed):
    model=np.asarray(model);observed=np.asarray(observed)
    if model.shape!=observed.shape or model.ndim!=1 or len(model)%24:raise ValueError('Require matching whole UTC days')
    out=metrics(model,observed);p=model.reshape(-1,24);o=observed.reshape(-1,24)
    complete=np.isfinite(p).all(axis=1)&np.isfinite(o).all(axis=1);p=p[complete];o=o[complete]
    out['complete_utc_days']=int(complete.sum())
    if not len(p):return out
    pd=p-p.mean(axis=1,keepdims=True);od=o-o.mean(axis=1,keepdims=True);e=p-o;level=np.mean(e.mean(axis=1)**2);total=np.mean(e**2)
    corr=lambda a,b:float(np.corrcoef(a.ravel(),b.ravel())[0,1]) if a.std()>1e-12 and b.std()>1e-12 else None
    out.update(demeaned_mae=float(abs(pd-od).mean()),demeaned_correlation=corr(pd,od),
               model_daily_range_mean=float(np.ptp(p,axis=1).mean()),observed_daily_range_mean=float(np.ptp(o,axis=1).mean()),
               daily_range_mae=float(abs(np.ptp(p,axis=1)-np.ptp(o,axis=1)).mean()),
               model_within_day_sd=float(np.sqrt(np.mean(pd**2))),observed_within_day_sd=float(np.sqrt(np.mean(od**2))),
               within_day_error_mse_share=float(1-level/total) if total>0 else None,
               model_below_5_hours=int((p<5).sum()),observed_below_5_hours=int((o<5).sum()),
               model_material_negative_hours=int((p<-1e-6).sum()),observed_material_negative_hours=int((o<-1e-6).sum()),
               model_above_150_hours=int((p>150).sum()),observed_above_150_hours=int((o>150).sum()))
    ramps=np.isfinite(model[1:])&np.isfinite(model[:-1])&np.isfinite(observed[1:])&np.isfinite(observed[:-1])
    out['ramp_mae']=float(abs(np.diff(model)[ramps]-np.diff(observed)[ramps]).mean()) if ramps.any() else None
    out['model_utc_profile']=model.reshape(-1,24)[complete].mean(axis=0).tolist();out['observed_utc_profile']=observed.reshape(-1,24)[complete].mean(axis=0).tolist()
    return out


def loss4(prices,monthly,target):
    result=loss(prices,monthly,target);errors=[]
    for j in range(prices.shape[1]):
        r=shape_metrics(prices[:,j],target['prices'][:,j])
        if r['complete_utc_days']:errors.append(r['demeaned_mae'])
    if not errors:raise ValueError('No complete-day training price observations')
    return result|dict(shape=float(np.mean(errors)))


def penalty(direction,active,params):
    a,b,d=params
    reg=float(np.mean(((direction/BOUNDS)**2)[active])) if active.any() else 0.
    return float(.05*(a*a*reg+b*b+(d/30.)**2))


def score(raw,control,reg):return float(np.mean([raw[k]/max(control[k],1e-9) for k in ['price','shape','generation','trade']])+reg)


def choose(records,key):
    good=[r for r in records if r.get(key) is not None];minimum=min(r[key] for r in good)
    return min((r for r in good if r[key]<=minimum+1e-12),key=lambda r:(r['penalty'],r['index']))


def period_target(half,stage):
    if stage=='fit':return dict(prices=half['prices'][:FIT],generation=half['generation'][:4],trade=half['trade'][:4],months=half['months'][:4])
    if stage=='selection':return dict(prices=half['prices'][FIT:SELECT],generation=half['generation'][4:],trade=half['trade'][4:],months=half['months'][4:])
    raise ValueError(stage)


def summarize(prices,target,zones):
    rows=[dict(zone=z,**shape_metrics(prices[:,j],target[:,j])) for j,z in enumerate(zones)];known=[r for r in rows if r['known_hours']]
    mean=lambda key:float(np.mean([r[key] for r in known if r.get(key) is not None]))
    return dict(zones=rows,equal_zone_mae=mean('mae_eur_mwh'),mean_correlation=mean('correlation'),mean_demeaned_correlation=mean('demeaned_correlation'),mean_demeaned_mae=mean('demeaned_mae'))


def local_profile(values,start,timezone):
    times=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC')[start:start+len(values)].tz_convert(timezone)
    return dict(timezone=timezone,means=[float(np.mean(values[times.hour==h])) for h in range(24)],counts=[int((times.hour==h).sum()) for h in range(24)])
