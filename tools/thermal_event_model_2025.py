"""Daily network dispatch with group ramps and optional continuous thermal states.

All thermal offer tranches share one state. Forty-eight-hour forecast horizon;
only the first24h are implemented. No new event targets enter offer adjustments; inherited calibrated bids stay fixed.
"""
import numpy as np
from scipy.sparse import block_diag,coo_matrix,hstack,vstack
import highspy

HISTORY=16

def options(name):
    return dict(ramp=name in ['ramp','commitment','weather_ramp','weather_commitment','firm_stress'],commitment=name in ['commitment','weather_commitment','firm_stress'],weather=name.startswith('weather') or name=='firm_stress',firm=.7 if name=='firm_stress' else 1.)

def seed(meta,source,design,opt):
    q=np.array([source['initial'][g['columns']].sum()*opt['firm'] for g in meta['groups']]);cap=np.array([g['capacity_mw']*opt['firm'] for g in meta['groups']]);minimum=np.array([design['parameters'][g['carrier']]['minimum_output_fraction'] for g in meta['groups']]);q=np.clip(q,0,cap);online=np.minimum(cap,q/minimum)
    return dict(q=q,online=online,starts=np.zeros((HISTORY,len(q))),stops=np.zeros((HISTORY,len(q))))

def compile_day(A,source,meta,design,name,start,state,horizon=48):
    opt=options(name);ng,nl,nz=meta['ng'],meta['nl'],meta['nz'];ni=meta['islands'];n=A.shape[1];nr=A.shape[0];T=horizon;groups=meta['groups'];G=len(groups)
    sl=slice(start,start+T);av=source['availability'][sl].copy();cost=source['cost'][sl]
    if opt['weather']:
        av+=(design['weather_stress']['solar']-1)*source['solar_components'][sl]+(design['weather_stress']['wind']-1)*source['wind_components'][sl]
        assert av.min()>-1e-7;av=np.maximum(av,0)
    if opt['firm']<1:
        for g in groups:av[:,g['columns']]*=opt['firm']
    clo=np.c_[np.zeros((T,ng)),source['link_min'][sl],np.full((T,nz),-np.inf)].ravel();chi=np.c_[av,source['link_max'][sl],np.full((T,nz),np.inf)].ravel();c=np.c_[cost,np.zeros((T,nl+nz))].ravel()
    rlo=np.c_[source['load'][sl],source['island_rhs'][sl],-source['ratings']-source['flow'][sl]].ravel();rhi=np.c_[source['load'][sl],source['island_rhs'][sl],source['ratings']-source['flow'][sl]].ravel();network=block_diag([A]*T,format='csc')
    caps=np.array([g['capacity_mw']*opt['firm'] for g in groups]);extra=3*T*G if opt['commitment'] else 0
    if extra:
        no_load=np.array([design['parameters'][g['carrier']]['online_eur_per_mw_hour'] for g in groups]);startup=np.array([design['parameters'][g['carrier']]['startup_eur_per_mw'] for g in groups]);c=np.r_[c,np.tile(no_load,T),np.tile(startup,T),np.zeros(T*G)];clo=np.r_[clo,np.zeros(extra)];chi=np.r_[chi,np.tile(caps,3*T)];network=hstack([network,coo_matrix((T*nr,extra))],format='csc')
    rr=[];cc=[];vv=[];lo=[];hi=[];labels=[]
    def row(terms,upper=0.,lower=-np.inf,label=''):
        k=len(lo)
        for j,v in terms:
            if v:rr.append(k);cc.append(j);vv.append(v)
        lo.append(lower);hi.append(upper);labels.append(label)
    def q(h,g,co=1):return [(h*n+j,co) for j in groups[g]['columns']]
    def idx(kind,h,g):return T*n+kind*T*G+h*G+g
    def hist(kind,h,g):
        if h>=0:return [(idx(kind,h,g),1.)],0.
        assert -HISTORY<=h
        return [],float(state['starts' if kind==1 else 'stops'][h,g])
    if opt['ramp']:
        for t in range(T):
            for j,g in enumerate(groups):
                p=design['parameters'][g['carrier']];rate=p['ramp_fraction_per_hour'];minimum=p['minimum_output_fraction'];previous=q(t-1,j,-1) if t else [];prior=0. if t else state['q'][j]
                if not opt['commitment']:
                    row(q(t,j)+previous,rate*caps[j]+prior,label='ramp_up');row(q(t,j,-1)+[(k,-v) for k,v in previous],rate*caps[j]-prior,label='ramp_down');continue
                u=idx(0,t,j);s=idx(1,t,j);d=idx(2,t,j);arrival,known=hist(1,t-p['startup_lead_hours'],j)
                prev_u=[(idx(0,t-1,j),-1.)] if t else [];initial=0. if t else state['online'][j]
                row([(u,1.),(d,1.)]+prev_u+[(k,-v) for k,v in arrival],known+initial,known+initial,'online_state')
                row(q(t,j)+[(u,-1.)],label='online_upper');row(q(t,j,-1)+[(u,minimum)],label='stable_minimum')
                up=q(t,j)+previous+[(k,-minimum*v) for k,v in arrival];rhs=prior+minimum*known
                if t:up.append((idx(0,t-1,j),-rate))
                else:rhs+=rate*state['online'][j]
                row(up,rhs,label='online_ramp_up')
                row(q(t,j,-1)+[(k,-v) for k,v in previous]+[(u,-rate),(d,-minimum)],-prior,label='online_ramp_down')
                up=[(u,-1.)];constant=0.
                for k in range(p['minimum_up_hours']):
                    terms,known=hist(1,t-p['startup_lead_hours']-k,j);up+=terms;constant+=known
                row(up,-constant,label='minimum_up')
                down=[(u,1.)];constant=0.
                for k in range(p['minimum_down_hours']):
                    terms,known=hist(2,t-k,j);down+=terms;constant+=known
                row(down,caps[j]-constant,label='minimum_down')
    if lo:
        temporal=coo_matrix((vv,(rr,cc)),shape=(len(lo),len(c))).tocsc();network=vstack([network,temporal],format='csc');rlo=np.r_[rlo,lo];rhi=np.r_[rhi,hi]
    return dict(A=network,c=c,clo=clo,chi=chi,rlo=rlo,rhi=rhi,n=n,nr=nr,T=T,G=G,extra=extra,labels=labels,availability=av)

def solve(lp,h=None):
    A=lp['A'];n=len(lp['c']);r=len(lp['rlo'])
    if h is None:
        h=highspy.Highs();h.setOptionValue('output_flag',False);h.setOptionValue('threads',1);h.setOptionValue('solver','simplex');h.setOptionValue('primal_feasibility_tolerance',1e-8);h.setOptionValue('dual_feasibility_tolerance',1e-8)
        model=highspy.HighsLp();model.num_col_=n;model.num_row_=r;model.col_cost_=lp['c'];model.col_lower_=lp['clo'];model.col_upper_=lp['chi'];model.row_lower_=lp['rlo'];model.row_upper_=lp['rhi'];model.a_matrix_.format_=highspy.MatrixFormat.kColwise;model.a_matrix_.start_=A.indptr;model.a_matrix_.index_=A.indices;model.a_matrix_.value_=A.data;h.passModel(model)
    else:
        h.changeColsBounds(n,np.arange(n,dtype=np.int32),lp['clo'],lp['chi']);h.changeColsCost(n,np.arange(n,dtype=np.int32),lp['c']);h.changeRowsBounds(r,np.arange(r,dtype=np.int32),lp['rlo'],lp['rhi'])
    # Use the independently bundled IPM for state LPs. Native crossover stalled
    # on this matrix: do not spend unbounded time recovering a warm basis.
    if lp['extra']:
        return scipy_start(lp,h)
    h.setOptionValue('solver','simplex');h.setOptionValue('time_limit',h.getRunTime()+45.);h.run()
    if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:
        return scipy_start(lp,h)
    if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:raise RuntimeError(h.modelStatusToString(h.getModelStatus()))
    sol=h.getSolution();return h,np.asarray(sol.col_value),np.asarray(sol.row_dual),np.asarray(sol.col_dual),float(h.getObjectiveValue())

def scipy_start(lp,h):
    from scipy.optimize import linprog
    A=lp['A'].tocsr();eq=lp['rlo']==lp['rhi'];up=np.isfinite(lp['rhi'])&~eq;down=np.isfinite(lp['rlo'])&~eq
    result=linprog(lp['c'],A_ub=vstack([A[up],-A[down]],format='csc'),b_ub=np.r_[lp['rhi'][up],-lp['rlo'][down]],A_eq=A[eq],b_eq=lp['rlo'][eq],bounds=list(zip(lp['clo'],lp['chi'])),method='highs-ipm',options={'time_limit':180,'primal_feasibility_tolerance':1e-8,'dual_feasibility_tolerance':1e-8})
    if not result.success:raise RuntimeError('Independent backend: '+result.message)
    y=np.zeros(len(eq));y[eq]=result.eqlin.marginals;y[up]+=result.ineqlin.marginals[:up.sum()];y[down]-=result.ineqlin.marginals[up.sum():];rc=result.lower.marginals+result.upper.marginals
    return h,result.x,y,rc,float(result.fun)

def carry(x,lp,meta,state):
    G=lp['G'];n=lp['n'];T=lp['T'];dispatch=x[:T*n].reshape(T,n);q=np.array([dispatch[23,g['columns']].sum() for g in meta['groups']])
    if lp['extra']:
        u,s,d=x[T*n:].reshape(3,T,G);return dict(q=q,online=u[23].copy(),starts=np.r_[state['starts'],s[:24]][-HISTORY:],stops=np.r_[state['stops'],d[:24]][-HISTORY:])
    return state|dict(q=q)
