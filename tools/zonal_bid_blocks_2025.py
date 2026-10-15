"""Training-only zonal bid proposals and capacity-conserving thermal blocks."""
import numpy as np
from bid_calibration_2025 import NTRAIN, NAMES

OFFSET_BOUNDS=np.array([30.,30.,15.])
SPREAD_BOUNDS=np.array([60.,60.,30.])
STRENGTHS=[0.,.5,1.]
DESIGN=dict(
    training='January–June 2025 UTC, 4344 hours; monthly generation/trade months 1–6',
    evaluation='July–December 2025 UTC, 4416 hours; retrospective, already inspected; no evaluation-driven selection',
    stages=['Zonal gas/coal/nuclear constant offset', 'Keep training-selected offset; add zonal resource upper-block spread'],
    offset_bounds_eur_mwh=OFFSET_BOUNDS.tolist(),spread_bounds_eur_mwh=SPREAD_BOUNDS.tolist(),
    blocks='70%/30% of each original thermal aggregate availability; identical physical columns; no added capacity',
    evidence='Local interior offer >0.001 MW from either bound, original resource bid within 1e-5 EUR/MWh of local clearing price; not a unique real marginal generator',
    offset_estimator='Median observed-minus-control price on local-interior resource hours, multiplied by n/(n+168), clipped to resource bounds; no evidence gives zero',
    spread_estimator='On stage-one local-interior hours, difference of median price residuals at resource utilization >=70% versus <70%; require 24 hours in each cohort; multiply by min(n_high,n_low)/(min(n_high,n_low)+168); clip to [0, bound]',
    search='One proposal per stage; exactly strengths 0, 0.5, 1 in each stage, evaluated inside coupled network on all training hours; no coordinate/global optimum claim',
    objective='Equal mean of price/generation/trade training errors normalized by fresh control; plus 0.05 times mean squared normalized offsets and 0.05 times mean squared normalized spreads over physically present zone/resource pairs',
    quantities='Same country/fuel/month conditional allocation intervals and implied net-export errors/floors as bid-calibration-v1; missing references unknown; impossible targets remain soft checks',
    ties='Within 1e-12 prefer smaller squared normalized parameters, then earlier trial; zero-change control remains selectable',
    annual='Evaluate control and both training-selected stage winners over 8760 hours; no choice between them based on July–December outcomes',
    fixed='Original hourly availability/demand/fixed hydro/GSK/PTDF/islands/HVDC constraints; independent hourly clears batched by day, no intertemporal storage restart',
    floor='Final offer max(0, original fuel/efficiency/carbon/VOM anchor + zonal offset + upper-block spread)',
    scope='Effective synthetic bids, not recovered orders or measured zone production costs; bounds/shrinkage/weights are experimental, not acceptance gates')


def split_model(m,context):
    """Duplicate thermal columns, partitioning their original capacity exactly."""
    parent=[];share=[];upper=[];groups=[];origin=[];virtual_share=[]
    for k,ids in enumerate(context['groups']):
        for fraction,is_upper in ([(.7,False),(.3,True)] if context['classes'][k] else [(1.,False)]):
            parent.append(k);share.append(fraction);upper.append(is_upper)
            groups.append(list(range(len(origin),len(origin)+len(ids))))
            origin.extend(ids);virtual_share.extend([fraction]*len(ids))
    parent=np.array(parent);share=np.array(share);upper=np.array(upper)
    case=m.copy();case['ng']=len(parent)
    case['A']=m['A'][:,np.r_[parent,np.arange(m['ng'],m['A'].shape[1])]].tocsc()
    case['availability']=m['availability'][:,parent]*share
    case['cost']=m['cost'][:,parent].copy()
    for key in ['offer_zones','emergency_mask']:case[key]=m[key][parent]
    ctx=context.copy();ctx['groups']=groups
    ctx['availability']=context['availability'][:,origin]*virtual_share
    for key in ['generation_keys','country_keys']:ctx[key]=[context[key][i] for i in origin]
    ctx['classes']=[context['classes'][k] for k in parent]
    layout=dict(parent=parent.tolist(),share=share.tolist(),upper=upper.tolist())
    return case,ctx,layout


def collapse(values,m,layout):
    parent=np.array(layout['parent']);g=np.zeros((len(values),m['ng']))
    for j,k in enumerate(parent):g[:,k]+=values[:,j]
    return np.c_[g,values[:,len(parent):]]


def active_pairs(m,context):
    active=np.zeros((m['nz'],3),bool)
    for j,kind in enumerate(context['classes']):
        if kind and m['availability'][:,j].max()>0:active[m['zones'].index(m['offer_zones'][j]),NAMES.index(kind)]=True
    return active


def parameters(m,context,offsets,spreads):
    shape=(m['nz'],3)
    for x,b in [(offsets,OFFSET_BOUNDS),(spreads,SPREAD_BOUNDS)]:
        if np.shape(x)!=shape or not np.isfinite(x).all() or (abs(x)>b+1e-9).any():raise ValueError('Outside declared zonal bid bounds')
    if (spreads<0).any():raise ValueError('Upper block must not undercut lower block')


def costs(m,context,layout,offsets,spreads):
    parameters(m,context,offsets,spreads);result=m['cost'].copy()
    for j,kind in enumerate(context['classes']):
        if kind:
            z=m['zones'].index(m['offer_zones'][j]);f=NAMES.index(kind)
            result[:,j]=np.maximum(0,result[:,j]+offsets[z,f]+layout['upper'][j]*spreads[z,f])
    return result


def evidence(m,context,x,p,observed):
    if len(x)!=NTRAIN or p.shape!=observed.shape or len(observed)!=NTRAIN:raise ValueError('Only declared training period allowed')
    result=[]
    for z,zone in enumerate(m['zones']):
        for f,kind in enumerate(NAMES):
            ids=[j for j,c in enumerate(context['classes']) if c==kind and m['offer_zones'][j]==zone]
            local=np.zeros(NTRAIN,bool);cap=np.zeros(NTRAIN);output=np.zeros(NTRAIN)
            for j in ids:
                a=m['availability'][:NTRAIN,j];q=x[:,j]
                local|=(q>.001)&(a-q>.001)&(abs(m['cost'][:NTRAIN,j]-p[:,z])<=1e-5)
                cap+=a;output+=q
            local&=np.isfinite(observed[:,z])
            util=np.divide(output,cap,out=np.zeros(NTRAIN),where=cap>0)
            result.append((z,f,local,util,observed[:,z]-p[:,z]))
    return result


def proposal(m,context,x,p,observed,stage):
    result=np.zeros((m['nz'],3));counts=[]
    for z,f,local,util,error in evidence(m,context,x,p,observed):
        count=int(local.sum());lo=local&(util<.7);hi=local&(util>=.7);nl=int(lo.sum());nh=int(hi.sum())
        if stage=='offset':value=float(np.median(error[local]))*count/(count+168) if count else 0.;bound=OFFSET_BOUNDS[f];value=float(np.clip(value,-bound,bound))
        elif stage=='spread':
            sample=min(nl,nh);value=(float(np.median(error[hi])-np.median(error[lo]))*sample/(sample+168)) if sample>=24 else 0.
            value=float(np.clip(value,0,SPREAD_BOUNDS[f]))
        else:raise ValueError('Unknown proposal stage')
        result[z,f]=value;counts.append(dict(zone=m['zones'][z],resource=NAMES[f],local_hours=count,low_utilization_hours=nl,high_utilization_hours=nh,proposal_eur_mwh=value))
    return result,counts


def regularization(offsets,spreads,active):
    if not active.any():return 0.
    return float(.05*np.mean(((offsets/OFFSET_BOUNDS)**2)[active])+.05*np.mean(((spreads/SPREAD_BOUNDS)**2)[active]))


def objective(raw,baseline,offsets,spreads,active):
    return float(np.mean([raw[k]/max(baseline[k],1e-9) for k in ['price','generation','trade']])+regularization(offsets,spreads,active))


def choose(records):
    good=[r for r in records if r['score'] is not None];minimum=min(r['score'] for r in good)
    return min((r for r in good if r['score']<=minimum+1e-12),key=lambda r:(r['penalty'],r['index']))


def canonical_parameters(offsets,spreads):
    """Signed zero is the same bid; use one cache entry and earliest tie index."""
    return tuple(np.where(x==0,0.,x) for x in [offsets,spreads])
