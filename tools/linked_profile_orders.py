"""Sparse daily profile/linked-order allocation prototype, not EUPHEMIA pricing.

Positive profiles sell MW; negative profiles buy MW. All periods are one hour.
MILP acceptance is followed by a conditional fixed-integer LP and surplus checks.
"""
import time
import numpy as np
import highspy
from scipy.sparse import block_diag,coo_matrix,hstack,vstack


def compile_book(base,orders,reservations=None,storage=None):
    T,n,nr=base['T'],base['A'].shape[1],base['A'].shape[0]
    reservations=reservations or {};storage=storage or {};B=len(orders)
    ids={r['id']:j for j,r in enumerate(orders)}
    if len(ids)!=B:raise ValueError('Duplicate order ID')
    profiles=[];parents=[];binary=[]
    for j,r in enumerate(orders):
        q=np.asarray(r['profile'],float);mar=r.get('minimum_ratio',1.)
        if q.shape!=(T,) or not np.isfinite(q).all() or not np.any(q) or (q.min()<0<q.max()):raise ValueError('Require finite, nonempty, one-sided hourly profile')
        if not 0<=mar<=1 or not np.isfinite(r['price']):raise ValueError('Invalid order price/MAR')
        if not 0<=r['injection_column']<n:raise ValueError('Invalid injection column')
        if r.get('reservation') not in [None,*reservations]:raise ValueError('Unknown physical reservation')
        if r.get('asset') not in [None,*storage]:raise ValueError('Unknown storage asset')
        ps=r.get('parents',[])
        if len(ps)>1 or any(p not in ids or p==r['id'] for p in ps):raise ValueError('Prototype requires a single valid parent (forest), without self-links')
        parents.append([ids[p] for p in ps]);profiles.append(q)
        if mar>0:binary.append(j)
    def visit(j,path):
        if j in path:raise ValueError('Cyclic order links')
        for p in parents[j]:visit(p,path|{j})
    for j in range(B):visit(j,set())
    profiles=np.array(profiles).reshape(B,T)
    lo=np.array(base['lower'],float,copy=True);hi=np.array(base['upper'],float,copy=True)
    used=set()
    for name,res in reservations.items():
        columns=res['columns'];cap=np.asarray(res['mw'],float)
        if cap.shape!=(T,len(columns)) or not np.isfinite(cap).all() or cap.min()<0:raise ValueError('Invalid reserved MW')
        for k,col in enumerate(columns):
            if col in used or not 0<=col<n:raise ValueError('Duplicated/invalid reserved source')
            used.add(col)
            if np.max(cap[:,k]-hi[:,col])>1e-7:raise ValueError('Reservation exceeds original availability')
            hi[:,col]-=cap[:,k]
        for j,r in enumerate(orders):
            if r.get('reservation')==name:
                if profiles[j].min()<0:raise ValueError('Reserved supply cannot be a demand order')
                for col in columns:
                    if (base['A'][:,col]-base['A'][:,r['injection_column']]).nnz:raise ValueError('Reservation changes injection geography')
    # Direction binaries only where the submitted storage profiles overlap.
    directions=[]
    for name,asset in storage.items():
        if not 0<asset['eta_charge']<=1 or not 0<asset['eta_discharge']<=1:raise ValueError('Invalid storage efficiency')
        if asset['energy_mwh']<0 or asset['charge_mw']<0 or asset['discharge_mw']<0 or not 0<=asset['initial_mwh']<=asset['energy_mwh']:raise ValueError('Invalid storage bounds')
        js=[j for j,r in enumerate(orders) if r.get('asset')==name]
        for j in js[1:]:
            if (base['A'][:,orders[j]['injection_column']]-base['A'][:,orders[js[0]]['injection_column']]).nnz:raise ValueError('One storage asset cannot teleport between injection points')
        for t in range(T):
            if any(profiles[j,t]<0 for j in js) and any(profiles[j,t]>0 for j in js):directions.append((name,t))
    N=T*n+B+len(binary)+len(directions);ratio=lambda j:T*n+j
    gate={j:T*n+B+k for k,j in enumerate(binary)}
    direction={key:T*n+B+len(binary)+k for k,key in enumerate(directions)}
    net=block_diag([base['A']]*T,format='csc');rr=[];cc=[];vv=[]
    for j,r in enumerate(orders):
        injection=base['A'][:,r['injection_column']].tocoo()
        for t in np.flatnonzero(profiles[j]):
            rr.extend((t*nr+injection.row).tolist());cc.extend([j]*len(injection.data));vv.extend((profiles[j,t]*injection.data).tolist())
    extra=coo_matrix((vv,(rr,cc)),shape=(T*nr,N-T*n)).tocsc();A=hstack([net,extra],format='csc')
    c=np.r_[np.asarray(base['cost']).ravel(),[r['price']*q.sum() for r,q in zip(orders,profiles,strict=True)],np.zeros(len(binary)+len(directions))]
    lower=np.r_[lo.ravel(),np.zeros(N-T*n)];upper=np.r_[hi.ravel(),np.ones(N-T*n)]
    rlo=np.asarray(base['row_lower']).ravel();rhi=np.asarray(base['row_upper']).ravel();rr=[];cc=[];vv=[];lows=[];highs=[];labels=[]
    def row(terms,low=-np.inf,high=0.,label=''):
        k=len(lows)
        for col,val in terms:
            if val:rr.append(k);cc.append(col);vv.append(val)
        lows.append(low);highs.append(high);labels.append(label)
    for j,r in enumerate(orders):
        if j in gate:
            row([(ratio(j),1),(gate[j],-1)],label='activation_upper')
            row([(ratio(j),1),(gate[j],-r.get('minimum_ratio',1.))],low=0,high=np.inf,label='minimum_acceptance')
        for p in parents[j]:row([(ratio(j),1),(ratio(p),-1)],label='parent_child')
    exclusive=sorted(set(r['exclusive'] for r in orders if r.get('exclusive') is not None))
    for group in exclusive:row([(ratio(j),1) for j,r in enumerate(orders) if r.get('exclusive')==group],high=1,label='exclusive_group')
    for name,res in reservations.items():
        js=[j for j,r in enumerate(orders) if r.get('reservation')==name]
        for t in range(T):row([(ratio(j),profiles[j,t]) for j in js],high=np.asarray(res['mw'])[t].sum(),label='reserved_capacity')
    for name,asset in storage.items():
        js=[j for j,r in enumerate(orders) if r.get('asset')==name]
        energy={j:np.cumsum(np.maximum(-profiles[j],0)*asset['eta_charge']-np.maximum(profiles[j],0)/asset['eta_discharge']) for j in js}
        for t in range(T):
            row([(ratio(j),energy[j][t]) for j in js],low=-asset['initial_mwh'],high=asset['energy_mwh']-asset['initial_mwh'],label='storage_energy')
            charge=[(ratio(j),max(-profiles[j,t],0)) for j in js];discharge=[(ratio(j),max(profiles[j,t],0)) for j in js]
            if (name,t) in direction:
                d=direction[name,t];row(charge+[(d,-asset['charge_mw'])],label='charge_direction');row(discharge+[(d,asset['discharge_mw'])],high=asset['discharge_mw'],label='discharge_direction')
            else:
                row(charge,high=asset['charge_mw'],label='charge_power');row(discharge,high=asset['discharge_mw'],label='discharge_power')
        if asset.get('terminal_mwh') is not None:
            terminal=asset['terminal_mwh']
            if not 0<=terminal<=asset['energy_mwh']:raise ValueError('Invalid terminal energy')
            row([(ratio(j),energy[j][-1]) for j in js],low=terminal-asset['initial_mwh'],high=terminal-asset['initial_mwh'],label='storage_terminal')
    if lows:
        temporal=coo_matrix((vv,(rr,cc)),shape=(len(lows),N)).tocsc();A=vstack([A,temporal],format='csc');rlo=np.r_[rlo,lows];rhi=np.r_[rhi,highs]
    integers=np.array(list(gate.values())+list(direction.values()),int)
    return dict(A=A,c=c,lower=lower,upper=upper,row_lower=rlo,row_upper=rhi,integers=integers,T=T,n=n,nr=nr,orders=orders,profiles=profiles,parents=parents,binary_orders=gate,storage=storage,labels=labels)


def optimize(lp,fixed=None,time_limit=10):
    A=lp['A'];h=highspy.Highs();h.setOptionValue('output_flag',False);h.setOptionValue('threads',1);h.setOptionValue('time_limit',time_limit);h.setOptionValue('mip_rel_gap',0.);h.setOptionValue('mip_abs_gap',1e-6)
    h.setOptionValue('primal_feasibility_tolerance',1e-8);h.setOptionValue('dual_feasibility_tolerance',1e-8)
    model=highspy.HighsLp();model.num_col_=len(lp['c']);model.num_row_=len(lp['row_lower']);model.col_cost_=lp['c'];lower=lp['lower'].copy();upper=lp['upper'].copy();model.row_lower_=lp['row_lower'];model.row_upper_=lp['row_upper']
    if fixed is not None:
        for j in lp['integers']:lower[j]=upper[j]=round(fixed[j])
    elif len(lp['integers']):model.integrality_=[highspy.HighsVarType.kInteger if j in set(lp['integers']) else highspy.HighsVarType.kContinuous for j in range(len(lp['c']))]
    model.col_lower_=lower;model.col_upper_=upper
    small=(lower>upper)&(lower-upper<=1e-7);upper[small]=lower[small];model.col_upper_=upper
    if fixed is not None or not len(lp['integers']):
        h.setOptionValue('solver','ipm');h.setOptionValue('run_crossover','off');h.setOptionValue('ipm_optimality_tolerance',1e-10)
    model.a_matrix_.format_=highspy.MatrixFormat.kColwise;model.a_matrix_.start_=A.indptr;model.a_matrix_.index_=A.indices;model.a_matrix_.value_=A.data
    load_status=h.passModel(model)
    if load_status==highspy.HighsStatus.kError:raise RuntimeError('Order matrix rejected: '+str(load_status))
    began=time.perf_counter();run_status=h.run();elapsed=time.perf_counter()-began
    if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:raise RuntimeError(h.modelStatusToString(h.getModelStatus())+', run='+str(run_status))
    sol=h.getSolution();x=np.asarray(sol.col_value);ax=A@x;value=float(lp['c']@x)
    violation=float(max(np.maximum(lp['row_lower']-ax,0).max(initial=0),np.maximum(ax-lp['row_upper'],0).max(initial=0),np.maximum(np.array(model.col_lower_)-x,0).max(initial=0),np.maximum(x-np.array(model.col_upper_),0).max(initial=0)))
    assert violation<=1e-4 and abs(value-h.getObjectiveValue())<.05
    info=dict(objective_eur=value,seconds=elapsed,primal_mw=violation,integer_count=len(lp['integers']),matrix_load_status=str(load_status))
    if fixed is None and len(lp['integers']):
        info['bound_eur']=float(h.getInfo().mip_dual_bound);info['absolute_gap_eur']=abs(value-info['bound_eur']);assert info['absolute_gap_eur']<.05
        assert abs(x[lp['integers']]-np.rint(x[lp['integers']])).max(initial=0)<1e-6
    else:
        y=np.asarray(sol.row_dual);rc=np.asarray(sol.col_dual);lower=np.array(model.col_lower_);upper=np.array(model.col_upper_)
        finite_lo=np.isfinite(lower);finite_hi=np.isfinite(upper);rl=np.isfinite(lp['row_lower']);rh=np.isfinite(lp['row_upper'])
        dual=float(np.maximum(y[rl],0)@lp['row_lower'][rl]+np.minimum(y[rh],0)@lp['row_upper'][rh]+np.maximum(rc[finite_lo],0)@lower[finite_lo]+np.minimum(rc[finite_hi],0)@upper[finite_hi])
        gap=abs(dual-value);stationarity=float(abs(lp['c']-A.T@y-rc).max(initial=0));assert gap<.05 and stationarity<1e-5
        assert abs(rc[~finite_lo&~finite_hi]).max(initial=0)<1e-5
        complementarity=max(float(abs(np.maximum(y[rl],0)*(ax[rl]-lp['row_lower'][rl])).max(initial=0)),float(abs(np.minimum(y[rh],0)*(ax[rh]-lp['row_upper'][rh])).max(initial=0)),float(abs(np.maximum(rc[finite_lo],0)*(x[finite_lo]-lower[finite_lo])).max(initial=0)),float(abs(np.minimum(rc[finite_hi],0)*(x[finite_hi]-upper[finite_hi])).max(initial=0)))
        assert complementarity<.05
        info|=dict(duality_gap_eur=gap,stationarity_eur_mwh=stationarity,complementarity_eur=complementarity)
        return x,y,info
    return x,None,info


def surplus_groups(lp,ratios):
    groups=[]
    for j in range(len(lp['orders'])):
        if ratios[j]<=1e-7:continue
        descendants={j};todo=[j]
        while todo:
            parent=todo.pop()
            for k,parents in enumerate(lp['parents']):
                if parent in parents and k not in descendants:descendants.add(k);todo.append(k)
        groups.append((j,sorted(descendants)))
    return groups


def price_feasibility(lp,x,time_limit):
    """Find supporting fixed-integer LP duals with nonnegative leaf/subtree surplus.

    Failure concerns this optimal primal/activation pattern, not all EUPHEMIA
    solutions. A market master would need cuts/reoptimization, not an arbitrary
    post-hoc removal of the losing orders.
    """
    from scipy.sparse import eye
    A=lp['A'];R,N=A.shape;ax=A@x;lower=lp['lower'].copy();upper=lp['upper'].copy()
    lower[lp['integers']]=np.rint(x[lp['integers']]);upper[lp['integers']]=lower[lp['integers']]
    tol=1e-6
    dual_lo=np.r_[np.where(np.isfinite(lp['row_upper'])&(lp['row_upper']-ax<=tol),-np.inf,0.),np.where(np.isfinite(upper)&(upper-x<=tol),-np.inf,0.)]
    dual_hi=np.r_[np.where(np.isfinite(lp['row_lower'])&(ax-lp['row_lower']<=tol),np.inf,0.),np.where(np.isfinite(lower)&(x-lower<=tol),np.inf,0.)]
    stationarity=hstack([A.T,eye(N,format='csc')],format='csc');rows=[stationarity];lo=[lp['c']];hi=[lp['c']]
    T,n,nr=lp['T'],lp['n'],lp['nr'];ratios=x[T*n:T*n+len(lp['orders'])]
    for _,js in surplus_groups(lp,ratios):
        coefficients=sum((A[:T*nr,T*n+j]*ratios[j] for j in js),coo_matrix((T*nr,1))).T
        row=hstack([coefficients,coo_matrix((1,R-T*nr+N))],format='csc')
        rhs=sum(ratios[j]*lp['orders'][j]['price']*lp['profiles'][j].sum() for j in js)
        rows.append(row);lo.append([rhs]);hi.append([np.inf])
    feasibility=dict(A=vstack(rows,format='csc'),c=np.zeros(R+N),lower=dual_lo,upper=dual_hi,row_lower=np.concatenate(lo),row_upper=np.concatenate(hi),integers=np.array([],int))
    try:values,_,info=optimize(feasibility,time_limit=time_limit)
    except RuntimeError as error:return None,dict(status=str(error),scope='No supporting prices found for this fixed optimal allocation; no master cuts attempted')
    y,rc=values[:R],values[R:];rl=np.isfinite(lp['row_lower']);rh=np.isfinite(lp['row_upper']);cl=np.isfinite(lower);cu=np.isfinite(upper)
    dual=float(np.maximum(y[rl],0)@lp['row_lower'][rl]+np.minimum(y[rh],0)@lp['row_upper'][rh]+np.maximum(rc[cl],0)@lower[cl]+np.minimum(rc[cu],0)@upper[cu])
    gap=abs(dual-float(lp['c']@x));assert gap<.05
    return y,dict(status='supporting_prices_found',seconds=info['seconds'],fixed_allocation_duality_gap_eur=gap,feasibility_residual=info['primal_mw'])


def clear(lp,time_limit=10):
    x,_,mip=optimize(lp,time_limit=time_limit);fixed,y,pricing=optimize(lp,fixed=x,time_limit=time_limit)
    assert abs(mip['objective_eur']-pricing['objective_eur'])<.05
    supported,price_search=price_feasibility(lp,fixed,time_limit)
    if supported is not None:y=supported
    T,n,nr=lp['T'],lp['n'],lp['nr'];ratios=fixed[T*n:T*n+len(lp['orders'])];surplus=[]
    for j,r in enumerate(lp['orders']):
        # Injection-column dual value includes network effects for that profile.
        hourly=(lp['A'][:T*nr,T*n+j].toarray().ravel()*y[:T*nr]).sum()
        surplus.append(float(ratios[j]*(hourly-r['price']*lp['profiles'][j].sum())))
    checks=[]
    for j,descendants in surplus_groups(lp,ratios):
        r=lp['orders'][j];total=sum(surplus[k] for k in descendants)
        checks.append(dict(order=r['id'],accepted_ratio=float(ratios[j]),own_surplus_eur=surplus[j],subtree_surplus_eur=total,passes=bool(total>=-.05)))
    return dict(values=fixed,row_duals=y,ratios=ratios,mip=mip,conditional_pricing=pricing,price_search=price_search,surplus=checks,conditional_surplus_passed=supported is not None and all(r['passes'] for r in checks),
        pricing_scope='Supporting-price search for one fixed optimal allocation and single-parent forests; no master cuts/reoptimization, MIC or full EUPHEMIA-compliance claim')
