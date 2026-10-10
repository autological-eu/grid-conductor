"""Experimental sparse zonal transport/rolling-storage formulation.

This is a simplification of the maintained daily engine, not commercial NTC,
physical load flow, an annual optimum or a replacement browser model.
"""
import numpy as np
from scipy.sparse import coo_matrix, kron, eye
from daily_market_clearing import make_solver, residual, reachable_bounds
import highspy
import time

TOL = 1e-4
FRICTION = .001  # Explicit EUR/MWh charge/discharge bid friction.


def transport_network(n, m):
    """Aggregate cross-area passive ratings; retain every native controllable link.

    Sum of N-0 branch ratings is an optimistic transport envelope, NOT a verified
    commercial capacity. Internal passive constraints and Kirchhoff are omitted.
    Country/AC-island geography is retained; islands are never collapsed together.
    """
    zones = m['zones']; zi = {z:i for i,z in enumerate(zones)}
    links = []
    lower = []; upper = []
    for j, (name, row) in enumerate(n.links.iterrows()):
        links.append(dict(id=str(name), source='original_controllable_link',
                          a=zi[m['buszone'][row.bus0]], b=zi[m['buszone'][row.bus1]],
                          efficiency=float(row.efficiency)))
        lower.append(m['link_min'][:,j]); upper.append(m['link_max'][:,j])
    corridors = {}
    for component in ('Line', 'Transformer'):
        for name, row in n.df(component).iterrows():
            a,b = zi[m['buszone'][row.bus0]],zi[m['buszone'][row.bus1]]
            if a == b:
                continue
            limit = float(row.s_nom*row.s_max_pu)
            if not np.isfinite(limit) or limit <= 0:
                raise ValueError('Invalid branch rating')
            pair = tuple(sorted((a,b)))
            entry = corridors.setdefault(pair, dict(limit=0., branches=[]))
            entry['limit'] += limit; entry['branches'].append(component+':'+str(name))
    hours = len(m['load'])
    for (a,b), row in sorted(corridors.items()):
        links.append(dict(id='transport:'+zones[a]+'--'+zones[b], a=a,b=b,
                          efficiency=1.,source='summed_cross_area_N0_ratings',**row))
        lower.append(np.full(hours,-row['limit'])); upper.append(np.full(hours,row['limit']))
    return dict(zones=zones,links=links,load=m['load'],cost=m['cost'],
                availability=m['availability'],offer_zones=m['offer_zones'],
                emergency_mask=m['emergency_mask'],
                link_min=np.column_stack(lower),link_max=np.column_stack(upper))


def storage_data(n, m, initial, hours, wear=2.):
    s = n.storage_units
    if len(n.stores) or any(not v.empty for k,v in n.storage_units_t.items() if k!='inflow'):
        raise ValueError('Unsupported Stores/time-varying storage physics')
    cap = (s.p_nom*s.max_hours).to_numpy()
    charge = (-s.p_nom*s.p_min_pu).to_numpy(); discharge = (s.p_nom*s.p_max_pu).to_numpy()
    eta_c = s.efficiency_store.to_numpy(); eta_d = s.efficiency_dispatch.to_numpy()
    phi = 1-s.standing_loss.to_numpy()
    inflow = n.get_switchable_as_dense('StorageUnit','inflow').iloc[:hours].to_numpy()
    if (not np.isfinite(np.c_[cap,charge,discharge,eta_c,eta_d,phi,initial]).all()
        or np.any(cap<0) or np.any(charge<0) or np.any(discharge<0)
        or np.any(eta_c<0) or np.any(eta_c>1) or np.any(eta_d<=0) or np.any(eta_d>1)
        or np.any((charge>0)&(eta_c<=0)) or np.any(phi<=0) or np.any(phi>1)
        or not np.isfinite(inflow).all() or np.any(inflow<0)
        or np.any(initial<0) or np.any(initial>cap+1e-6)
        or set(s.carrier)-{'hydro','PHS','battery'}):
        raise ValueError('Invalid storage inputs')
    terminal = initial.copy()
    lo,hi = reachable_bounds(inflow,np.broadcast_to(charge,inflow.shape),
                             np.broadcast_to(discharge,inflow.shape),cap,eta_c,eta_d,phi,terminal)
    if np.any(initial<lo[0]-TOL) or np.any(initial>hi[0]+TOL):
        raise ValueError('Unreachable closing stock')
    # Original arithmetic seasonal target, not a water gift or fixed generation.
    target = initial + np.vstack([np.zeros(len(s)),np.cumsum(inflow,axis=0)])
    target -= np.arange(hours+1)[:,None]/hours*(inflow.sum(axis=0)+initial-terminal)
    target = np.clip(target,0,cap)
    return dict(ids=s.index.tolist(),area=np.array([m['zones'].index(m['buszone'][b]) for b in s.bus]),
                cap=cap,charge=charge,discharge=discharge,eta_c=eta_c,eta_d=eta_d,phi=phi,
                inflow=inflow,initial=initial,terminal=terminal,reachable_lower=lo,reachable_upper=hi,
                target=target,hydro=np.flatnonzero(s.carrier.to_numpy()=='hydro'),
                discharge_cost=s.marginal_cost.to_numpy()+np.where(s.carrier=='battery',wear,0.)+FRICTION)


class Window:
    """Persistent sparse LP, exact zero-mode elimination, changing hourly vectors."""
    def __init__(self, m, s, hours, penalty=40.):
        self.m,self.s,self.hours,self.penalty=m,s,hours,float(penalty)
        ng = m['cost'].shape[1]; nl = len(m['links']); ns = len(s['ids']); nz = len(m['zones'])
        self.charge_ids=np.flatnonzero(s['charge']>0)
        self.spill_ids=np.flatnonzero(np.any(s['inflow']>0,axis=0))
        off = {}; width=0
        for key,count in [('g',ng),('f',nl),('c',len(self.charge_ids)),('d',ns),('e',ns),('p',len(self.spill_ids))]:
            off[key]=slice(width,width+count); width+=count
        self.off,self.width,self.rowwidth=off,width,nz+ns
        rr=[];cc=[];vv=[]
        def add(r,c,v):
            rr.append(r);cc.append(c);vv.append(v)
        for j,z in enumerate(m['offer_zones']):add(m['zones'].index(z),off['g'].start+j,1.)
        for j,e in enumerate(m['links']):
            add(e['a'],off['f'].start+j,-1.);add(e['b'],off['f'].start+j,e['efficiency'])
        for k,j in enumerate(self.charge_ids):
            add(s['area'][j],off['c'].start+k,-1.);add(nz+j,off['c'].start+k,-s['eta_c'][j])
        for j in range(ns):
            add(s['area'][j],off['d'].start+j,1.)
            add(nz+j,off['d'].start+j,1/s['eta_d'][j]);add(nz+j,off['e'].start+j,1.)
        for k,j in enumerate(self.spill_ids):add(nz+j,off['p'].start+k,1.)
        local=coo_matrix((vv,(rr,cc)),shape=(nz+ns,width)).tocsc()
        prev=coo_matrix((-s['phi'],(nz+np.arange(ns),off['e'].start+np.arange(ns))),shape=local.shape).tocsc()
        A=kron(eye(hours,format='csc'),local,format='csc')+kron(eye(hours,k=-1,format='csc'),prev,format='csc')
        # Soft end-window seasonal target for natural reservoirs, not short storage.
        nh=len(s['hydro']);self.soft_start=hours*width
        a=A.tocoo();r=np.r_[a.row,hours*(nz+ns)+np.arange(nh),hours*(nz+ns)+np.arange(nh),hours*(nz+ns)+np.arange(nh)]
        c=np.r_[a.col,(hours-1)*width+off['e'].start+s['hydro'],self.soft_start+np.arange(nh),self.soft_start+nh+np.arange(nh)]
        v=np.r_[a.data,np.ones(nh),np.ones(nh),-np.ones(nh)]
        self.A=coo_matrix((v,(r,c)),shape=(hours*(nz+ns)+nh,hours*width+2*nh)).tocsc()
        self.h=None;self.cols=np.arange(self.A.shape[1],dtype=np.int32);self.rows=np.arange(self.A.shape[0],dtype=np.int32)

    def vectors(self,start,current):
        m,s,H=self.m,self.s,self.hours;end=start+H;ns=len(s['ids']);nz=len(m['zones']);o=self.off
        lower=np.zeros((H,self.width));upper=np.zeros_like(lower);cost=np.zeros_like(lower)
        upper[:,o['g']]=m['availability'][start:end];cost[:,o['g']]=m['cost'][start:end]
        lower[:,o['f']]=m['link_min'][start:end];upper[:,o['f']]=m['link_max'][start:end]
        upper[:,o['c']]=s['charge'][self.charge_ids];cost[:,o['c']]=FRICTION
        upper[:,o['d']]=s['discharge'];cost[:,o['d']]=s['discharge_cost']
        upper[:,o['e']]=s['cap'];upper[:,o['p']]=s['inflow'][start:end,self.spill_ids]
        # Preserve separable year-end reachability at implemented and forecast boundaries.
        for k in sorted({min(24,H)-1,H-1}):
            lower[k,o['e']]=s['reachable_lower'][start+k+1]
            upper[k,o['e']]=s['reachable_upper'][start+k+1]
        rhs=np.c_[m['load'][start:end],s['inflow'][start:end]].copy()
        rhs[0,nz:]+=s['phi']*current
        target=s['target'][end,s['hydro']]
        nh=len(target)
        # Per stored-MWh penalty; declared heuristic, not expected electricity price.
        p=dict(A=self.A,lower=np.r_[lower.ravel(),np.zeros(2*nh)],
               upper=np.r_[upper.ravel(),np.full(2*nh,np.inf)],
               cost=np.r_[cost.ravel(),np.full(2*nh,self.penalty)],
               row_lower=np.r_[rhs.ravel(),target],row_upper=np.r_[rhs.ravel(),target])
        return p

    def clear(self,start,current,limit=60.):
        begin=time.perf_counter();p=self.vectors(start,current)
        if self.h is None:self.h=make_solver(p,limit)
        else:
            self.h.changeColsBounds(len(self.cols),self.cols,p['lower'],p['upper'])
            self.h.changeColsCost(len(self.cols),self.cols,p['cost'])
            self.h.changeRowsBounds(len(self.rows),self.rows,p['row_lower'],p['row_upper'])
        prep=time.perf_counter()-begin;begin=time.perf_counter()
        self.h.setOptionValue('time_limit',self.h.getRunTime()+limit);self.h.run()
        if self.h.getModelStatus()!=highspy.HighsModelStatus.kOptimal:
            raise ValueError('Nonoptimal compact window: '+str(self.h.getModelStatus()))
        seconds=time.perf_counter()-begin;sol=self.h.getSolution();x=np.asarray(sol.col_value)
        error=residual(p,x)
        if error>TOL:raise ValueError('Window LP residual failed')
        return dict(values=x[:self.soft_start].reshape(self.hours,self.width),
                    prices=np.asarray(sol.row_dual)[:self.hours*self.rowwidth].reshape(self.hours,self.rowwidth)[:,:len(self.m['zones'])],
                    objective_eur=float(p['cost']@x),maximum_residual=error,
                    solver_seconds=seconds,preparation_seconds=prep,iterations=self.h.getInfo().simplex_iteration_count,
                    soft=x[self.soft_start:]),p

    def unpack(self,values):
        H=len(values);s=self.s;o=self.off
        charge=np.zeros((H,len(s['ids'])));charge[:,self.charge_ids]=values[:,o['c']]
        spill=np.zeros_like(charge);spill[:,self.spill_ids]=values[:,o['p']]
        return dict(generation=values[:,o['g']],flows=values[:,o['f']],charge=charge,
                    discharge=values[:,o['d']],inventory=values[:,o['e']],spill=spill)


def replay(m,s,data):
    """Independent component equations, NOT an LP matrix multiplication."""
    g,f,c,d,e,p=[data[k] for k in ('generation','flows','charge','discharge','inventory','spill')]
    if any(not np.isfinite(v).all() for v in (g,f,c,d,e,p)):
        raise ValueError('Nonfinite annual witness')
    H=len(g);previous=np.vstack([s['initial'],e[:-1]]);inflow=s['inflow'][:H]
    water=float(np.abs(e-previous*s['phi']-c*s['eta_c']+d/s['eta_d']-inflow+p).max())
    balance=np.zeros((H,len(m['zones'])))
    for j,z in enumerate(m['offer_zones']):balance[:,m['zones'].index(z)]+=g[:,j]
    for j,row in enumerate(m['links']):balance[:,row['a']]-=f[:,j];balance[:,row['b']]+=row['efficiency']*f[:,j]
    for j,z in enumerate(s['area']):balance[:,z]+=d[:,j]-c[:,j]
    residuals=[water,float(np.abs(balance-m['load'][:H]).max())]
    for value,lo,hi in [(g,0,m['availability'][:H]),(f,m['link_min'][:H],m['link_max'][:H]),
                       (c,0,s['charge']),(d,0,s['discharge']),(e,0,s['cap']),(p,0,inflow)]:
        residuals.extend([float(np.maximum(lo-value,0).max(initial=0)),float(np.maximum(value-hi,0).max(initial=0))])
    cycles=int(np.count_nonzero((c>1e-6)&(d>1e-6)))
    closure=float(np.abs(e[-1]-s['terminal']).max())
    error=max(residuals)
    if error>TOL or closure>TOL or cycles:raise ValueError(f'Annual physics failed: residual={error}, closure={closure}, cycles={cycles}')
    cost=float(np.sum(g*m['cost'][:H])+np.sum(d*(s['discharge_cost']-FRICTION)))
    return dict(maximum_residual=error,maximum_water_residual=water,closure_mwh=closure,
                simultaneous_storage_hours=cycles,operating_cost_eur=cost,
                emergency_supply_twh=float(g[:,m['emergency_mask']].sum()/1e6))
