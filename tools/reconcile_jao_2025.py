"""Test a scaled flow-based/LTA convex-hull hypothesis; not market certification."""
import json,gzip
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from hourly_renewable_estimates import digest
ROOT=Path(__file__).resolve().parents[1]

def load_receipt(receipt):
    for p in (ROOT/'data/jao/probe-2025-v1/raw').glob('*.meta.json'):
        m=json.loads(p.read_text())
        if m['sha256']==receipt['sha256'] and m['url']==receipt['url']:
            raw=gzip.decompress(p.with_name(p.name.replace('.meta.json','.json.gz')).read_bytes())
            import hashlib
            if hashlib.sha256(raw).hexdigest()!=m['sha256']:raise ValueError('Cache hash mismatch')
            return json.loads(raw)['data']
    raise ValueError('Missing receipt data')

def hull(constraints,positions,lta):
    hubs=sorted({h for c in constraints for h in c['ptdf']});n=len(hubs)
    if not set(hubs)<=set(positions):raise ValueError('Missing positions')
    A=np.array([[c['ptdf'].get(h,0) for h in hubs] for c in constraints]);ram=np.array([c['ram_mw'] for c in constraints])
    borders=[]
    for k,v in lta.items():
        if not k.startswith('border_') or v is None:continue
        if not isinstance(v,(int,float)) or not np.isfinite(v) or v<0:raise ValueError('Invalid LTA capacity')
        suffix=k[7:];matches=[(a,b) for a in hubs for b in hubs if a+'_'+b==suffix]
        if len(matches)!=1:
            if v!=0:raise ValueError('Unmapped positive LTA border')
            continue
        borders.append((*matches[0],float(v)))
    B=np.zeros((n,len(borders)))
    for j,(a,b,_) in enumerate(borders):B[hubs.index(a),j]=1;B[hubs.index(b),j]=-1
    U=np.zeros((len(ram)+len(borders),n+len(borders)+1));U[:len(ram),:n]=A;U[:len(ram),-1]=-ram
    rhs=np.r_[np.zeros(len(ram)),[v for _,_,v in borders]]
    for j,(_,_,v) in enumerate(borders):U[len(ram)+j,n+j]=1;U[len(ram)+j,-1]=v
    E=np.zeros((n+1,n+len(borders)+1));E[:n,:n]=np.eye(n);E[:n,n:-1]=B;E[-1,:n]=1
    values=np.array([positions[h] for h in hubs]);objective=np.zeros(U.shape[1]);objective[-1]=-1
    result=linprog(objective,A_ub=U,b_ub=rhs,A_eq=E,b_eq=np.r_[values,0],bounds=[(None,None)]*n+[(0,None)]*len(borders)+[(0,1)],method='highs')
    if not result.success:return dict(status='hypothesis_infeasible' if result.status==2 else 'solver_failure',solver_status=int(result.status))
    x=result.x;ineq=float(np.maximum(U@x-rhs,0).max());eq=float(abs(E@x-np.r_[values,0]).max())
    if max(ineq,eq)>1e-6:raise ValueError('Hull witness residual failed')
    return dict(status='hypothesis_feasible_not_market_certified',fb_weight=float(x[-1]),lta_weight=float(1-x[-1]),maximum_inequality_residual_mw=ineq,maximum_equality_residual_mw=eq,scaled_fb_positions_mw=dict(zip(hubs,x[:n])),scaled_lta_flows_mw={a+'>'+b:float(x[n+j]) for j,(a,b,_) in enumerate(borders)})

if __name__=='__main__':
    source=ROOT/'public/research/jao-2025-probes.json';samples=json.loads(source.read_text())['samples'];rows=[]
    for s in samples[:3]:
        bundle=json.loads(gzip.decompress((ROOT/s['bundle_path']).read_bytes()))
        tables={r['url'].split('/data/')[1].split('?')[0]:load_receipt(r) for r in s['auxiliary_request_receipts']}
        for p in tables['netPos']:
            ltas=[r for r in tables['lta'] if r['dateTimeUtc']==p['dateTimeUtc']]
            if not ltas and len(tables['lta'])==1:ltas=tables['lta']
            if len(ltas)!=1:raise ValueError('Ambiguous LTA interval')
            positions={k[4:]:v for k,v in p.items() if k.startswith('hub_') and v is not None}
            constraints=bundle['constraints']
            row=dict(start=p['dateTimeUtc'],direct_max_violation_mw=max(0,max(sum(v*positions[h] for h,v in c['ptdf'].items())-c['ram_mw'] for c in constraints)),sign_flipped_max_violation_mw=max(0,max(-sum(v*positions[h] for h,v in c['ptdf'].items())-c['ram_mw'] for c in constraints)),convex_hull=hull(constraints,positions,ltas[0]))
            rows.append(row);print(row['start'],row['convex_hull']['status'],row['convex_hull'].get('lta_weight'))
    result=dict(status='reconciliation_hypothesis_not_dispatch_ready',probe_sha256=digest(source),producer_sha256=digest(__file__),checks=rows,limitations=['Scaled convex hull of final flow-based domain and directed LTA capacity domain is a tested hypothesis, not an authoritative reconstruction.','Allocation constraints, BEX restrictions, nominations and connector coupling are not imposed in this diagnostic.','Passing relaxed hypothesis feasibility does not validate market clearing or counterfactual investment.','No RAM values, source net positions or PTDF rows changed.'])
    (ROOT/'public/research/jao-2025-reconciliation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
