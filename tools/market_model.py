"""Paired, linked-period dispatch experiments. Not an EUPHEMIA implementation."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
def _init_solver():
    # Prefer the active environment; fall back to the vendored cp312 wheels
    # only when an import is missing so mixed-ABI wheels never shadow a
    # compatible install.
    try:
        import numpy as np
        from scipy.optimize import linprog
        from scipy.sparse import coo_matrix
    except ImportError:
        deps = ROOT/'data/carbon-pilot/solver-deps'
        if not deps.exists():
            raise
        sys.path.insert(0,str(deps))
        import numpy as np
        from scipy.optimize import linprog
        from scipy.sparse import coo_matrix
    return np,linprog,coo_matrix
np,linprog,coo_matrix=_init_solver()

VERSION='linked-dispatch-v1'


def validate(data):
    h=len(data['timestamps'])
    if not h or len(set(data['timestamps']))!=h:
        raise ValueError('Missing or duplicate intervals')
    from carbon_pilot import timestamp
    times=[timestamp(t) for t in data['timestamps']]
    dt=data['interval_hours']
    if not math.isfinite(dt) or dt<=0:
        raise ValueError('Invalid interval duration')
    if any(abs((b-a).total_seconds()/3600-dt)>1e-8 for a,b in zip(times,times[1:])):
        raise ValueError('Intervals must be consecutive')
    def vector(xs,negative=False):
        if len(xs)!=h or any(not isinstance(x,(int,float)) or not math.isfinite(x) or (not negative and x<0) for x in xs):
            raise ValueError('Invalid or incomplete input series')
    zones=data['zones']
    if not zones or len(zones)!=len(set(zones)):
        raise ValueError('Invalid zones')
    for z in zones:
        vector(data['load_mw'][z]);vector(data['external_net_import_mw'][z],True)
    ids=[]
    for g in data['generators']:
        ids.append(g['id'])
        if g['zone'] not in zones:
            raise ValueError('Unknown generator zone')
        vector(g['max_mw']);vector(g.get('min_mw',[0]*h))
        if not math.isfinite(g['cost_eur_mwh']):raise ValueError('Invalid cost')
        if any(a>b for a,b in zip(g.get('min_mw',[0]*h),g['max_mw'])):raise ValueError('Inverted generator limits')
        for k in ['energy_budget_mwh','ramp_mw_per_hour']:
            if k in g and (not math.isfinite(g[k]) or g[k]<0):raise ValueError('Invalid generator restriction')
        if g.get('co2_t_per_mwh') is not None and (not math.isfinite(g['co2_t_per_mwh']) or g['co2_t_per_mwh']<0):
            raise ValueError('Invalid emission factor')
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate generator IDs')
    ids=[]
    for e in data['edges']:
        ids.append(e['id'])
        if e['a'] not in zones or e['b'] not in zones or e['a']==e['b']:raise ValueError('Invalid edge')
        vector(e['ab_mw']);vector(e['ba_mw'])
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate edge IDs')
    ids=[]
    for s in data.get('storage',[]):
        ids.append(s['id'])
        if s['zone'] not in zones:raise ValueError('Unknown storage zone')
        for k in ['power_mw','energy_mwh','initial_mwh','terminal_mwh','throughput_cost_eur_mwh']:
            if not math.isfinite(s[k]) or s[k]<0:raise ValueError('Invalid storage parameter')
        if max(s['initial_mwh'],s['terminal_mwh'])>s['energy_mwh']:raise ValueError('Invalid inventory')
        if not 0<s['charge_efficiency']<=1 or not 0<s['discharge_efficiency']<=1:raise ValueError('Invalid efficiency')
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate storage IDs')
    if not math.isfinite(data['unserved_cost_eur_mwh']) or data['unserved_cost_eur_mwh']<=0:raise ValueError('Invalid shortage penalty')


def dispatch(data):
    validate(data)
    H=len(data['timestamps']);dt=data['interval_hours'];zones=data['zones']
    c=[];bounds=[];ix={};hour_of=[]
    def var(key,cost,lo,hi,t=None):
        ix[key]=len(c);c.append(cost);bounds.append((lo,hi));hour_of.append(t)
        return ix[key]
    for g in data['generators']:
        for t in range(H):var(('g',g['id'],t),g['cost_eur_mwh']*dt,g.get('min_mw',[0]*H)[t],g['max_mw'][t],t)
    for e in data['edges']:
        for t in range(H):var(('f',e['id'],t),0,-e['ba_mw'][t],e['ab_mw'][t],t)
    for z in zones:
        for t in range(H):
            var(('u',z,t),data['unserved_cost_eur_mwh']*dt,0,None,t)
            var(('spill',z,t),0,0,None,t)
    for s in data.get('storage',[]):
        for t in range(H):
            for kind in ['charge','discharge']:var((kind,s['id'],t),s['throughput_cost_eur_mwh']*dt,0,s['power_mw'],t)
        for t in range(H+1):
            fixed=s['initial_mwh'] if t==0 else s['terminal_mwh'] if t==H else None
            var(('soc',s['id'],t),0,fixed if fixed is not None else 0,fixed if fixed is not None else s['energy_mwh'])
    equations=[];rhs=[];inequalities=[];limits=[]
    for z in zones:
        for t in range(H):
            row={ix['u',z,t]:1,ix['spill',z,t]:-1}
            for g in data['generators']:
                if g['zone']==z:row[ix['g',g['id'],t]]=1
            for e in data['edges']:
                if z in (e['a'],e['b']):row[ix['f',e['id'],t]]=-1 if z==e['a'] else 1
            for s in data.get('storage',[]):
                if s['zone']==z:
                    row[ix['charge',s['id'],t]]=-1;row[ix['discharge',s['id'],t]]=1
            equations.append(row);rhs.append(data['load_mw'][z][t]-data['external_net_import_mw'][z][t])
    for s in data.get('storage',[]):
        for t in range(H):
            equations.append({ix['soc',s['id'],t+1]:1,ix['soc',s['id'],t]:-1,
                ix['charge',s['id'],t]:-dt*s['charge_efficiency'],ix['discharge',s['id'],t]:dt/s['discharge_efficiency']});rhs.append(0)
    for g in data['generators']:
        if 'energy_budget_mwh' in g:
            inequalities.append({ix['g',g['id'],t]:dt for t in range(H)});limits.append(g['energy_budget_mwh'])
        if 'ramp_mw_per_hour' in g:
            for t in range(1,H):
                for sign in [1,-1]:
                    inequalities.append({ix['g',g['id'],t]:sign,ix['g',g['id'],t-1]:-sign});limits.append(g['ramp_mw_per_hour']*dt)
    def matrix(rows):
        rr=[];cc=[];vv=[]
        for i,row in enumerate(rows):
            for j,v in row.items():rr.append(i);cc.append(j);vv.append(v)
        return coo_matrix((vv,(rr,cc)),shape=(len(rows),len(c))).tocsr()
    A=matrix(equations)
    result=linprog(c,A_eq=A,b_eq=rhs,A_ub=matrix(inequalities) if inequalities else None,
        b_ub=limits if inequalities else None,bounds=bounds,method='highs',options={'time_limit':120})
    if not result.success:raise ValueError(f'Optimization did not reach optimum: {result.message}')
    residual=float(np.max(np.abs(A@result.x-rhs)))
    if residual>1e-5:raise ValueError('Energy conservation check failed')
    hourly_cost=np.bincount([h for h in hour_of if h is not None],
        weights=[result.x[i]*c[i] for i,h in enumerate(hour_of) if h is not None],minlength=H)
    rows=[]
    co2_gens=[g for g in data['generators'] if g.get('co2_t_per_mwh') is not None]
    co2_available=bool(co2_gens)
    for t,stamp in enumerate(data['timestamps']):
        costs=hourly_cost[t]
        generation={g['id']:float(result.x[ix['g',g['id'],t]]) for g in data['generators']}
        storage={s['id']:dict(charge_mw=float(result.x[ix['charge',s['id'],t]]),discharge_mw=float(result.x[ix['discharge',s['id'],t]]),
            start_mwh=float(result.x[ix['soc',s['id'],t]]),end_mwh=float(result.x[ix['soc',s['id'],t+1]])) for s in data.get('storage',[])}
        co2_t=sum(float(result.x[ix['g',g['id'],t]])*g['co2_t_per_mwh']*dt for g in co2_gens)
        rows.append(dict(start=stamp,cost_eur=float(costs),generation_mw=generation,
            price_eur_mwh={z:float(result.eqlin.marginals[j*H+t]/dt) for j,z in enumerate(zones)},
            flow_mw={e['id']:float(result.x[ix['f',e['id'],t]]) for e in data['edges']},storage=storage,
            co2_t=co2_t if co2_available else None,
            unserved_mwh=sum(float(result.x[ix['u',z,t]])*dt for z in zones),
            spill_mwh=sum(float(result.x[ix['spill',z,t]])*dt for z in zones)))
    if abs(sum(r['cost_eur'] for r in rows)-result.fun)>max(1e-4,abs(result.fun)*1e-9):raise ValueError('Hourly cost reconciliation failed')
    simultaneous=sum(v['charge_mw']>1e-6 and v['discharge_mw']>1e-6 for r in rows for v in r['storage'].values())
    return dict(total_cost_eur=float(result.fun),total_co2_t=sum(r['co2_t'] for r in rows) if co2_available else None,
        max_balance_residual=residual,simultaneous_storage_intervals=simultaneous,
        unserved_mwh=sum(r['unserved_mwh'] for r in rows),hourly=rows)


def experiment(data,edge_id,additional_mw):
    if not math.isfinite(additional_mw) or additional_mw<0:raise ValueError('Relaxation must be finite and nonnegative')
    patched=copy.deepcopy(data)
    edge=next((e for e in patched['edges'] if e['id']==edge_id),None)
    if edge is None:raise ValueError('Unknown experiment edge')
    for k in ['ab_mw','ba_mw']:edge[k]=[v+additional_mw for v in edge[k]]
    baseline=dispatch(data);scenario=dispatch(patched)
    gain=baseline['total_cost_eur']-scenario['total_cost_eur']
    if gain < -max(.01,abs(baseline['total_cost_eur'])*1e-8):raise ValueError('Relaxation increased optimized cost')
    obs=data.get('observed_price_eur_mwh',{})
    validation={}
    for z,prices in obs.items():
        pairs=[(r['price_eur_mwh'][z],v) for r,v in zip(baseline['hourly'],prices) if v is not None]
        validation[z]=dict(matched_hours=len(pairs),price_mae_eur_mwh=sum(abs(a-b) for a,b in pairs)/len(pairs) if pairs else None)
    co2_change_t=baseline['total_co2_t']-scenario['total_co2_t'] if baseline['total_co2_t'] is not None and scenario['total_co2_t'] is not None else None
    return dict(version=VERSION,input_sha256=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),
        status='experimental_not_validated',annual_opportunity_meur=None,period_opportunity_meur=gain/1e6,
        interval_count=len(data['timestamps']),interval_hours=data['interval_hours'],
        constraint_patch=dict(edge=edge_id,both_directions_added_mw=additional_mw),
        validation=validation,assumptions=data.get('assumptions',[]),provenance=data.get('provenance',{}),
        emission_basis=data.get('emission_basis'),co2_change_t=co2_change_t,
        baseline=baseline,scenario=scenario,
        hourly_difference=[dict(start=a['start'],benefit_eur=a['cost_eur']-b['cost_eur'],
            co2_benefit_t=a['co2_t']-b['co2_t'] if a['co2_t'] is not None and b['co2_t'] is not None else None)
            for a,b in zip(baseline['hourly'],scenario['hourly'])])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True,type=Path);p.add_argument('--edge',required=True)
    p.add_argument('--add-mw',type=float,default=100);p.add_argument('--output',type=Path,default=ROOT/'public/research/market-experiment.json')
    args=p.parse_args();result=experiment(json.loads(args.input.read_text()),args.edge,args.add_mw)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['status','interval_count','period_opportunity_meur','annual_opportunity_meur','validation']},indent=2))


if __name__=='__main__':main()
