"""Controlled price and Norwegian fixed-injection geography diagnostics."""
import argparse,json,time,logging,resource,signal,fcntl
from pathlib import Path
import numpy as np
from nve_hydro_diagnostics import ROOT,NVE,rebuild,offsets,branch_offsets,point,native_point,solver,digest


def run(out):
    started=time.perf_counter();n,m,hp,mask,water,source=rebuild()
    with np.load(NVE/'resource_bids.npz',allow_pickle=False) as w:prices=w['prices'][:,m['zones'].index('1:NO')].copy();objectives=w['objectives'].copy()
    selected=sorted(set([348,4692,8364,int(np.argmin(prices)),int(np.argmax(prices)),int(np.argsort(prices)[4380])]+[int(a+np.argmin(prices[a:b])) for a,b in [(0,2160),(2160,4344),(4344,6552),(6552,8760)]]))
    checks=[];h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
    for t in selected:
        center,_=point(h,m,t,np.zeros(len(m['ratings'])))
        assert center['status']=='Optimal' and abs(center['objective_eur']-objectives[t])<max(.05,abs(objectives[t])*1e-8)
        slopes=[]
        for step in [.1,1.]:
            minus,_=point(h,m,t,np.zeros(len(m['ratings'])),-step);plus,_=point(h,m,t,np.zeros(len(m['ratings'])),step)
            slopes.append(dict(step_mw=step,downward_eur_mwh=(center['objective_eur']-minus['objective_eur'])/step if minus['status']=='Optimal' else None,upward_eur_mwh=(plus['objective_eur']-center['objective_eur'])/step if plus['status']=='Optimal' else None))
        checks.append(dict(hour=t,utc=str(n.snapshots[t]),saved_price_eur_mwh=float(prices[t]),resolved_price_eur_mwh=center['price_eur_mwh'],slopes=slopes))
    cases={};witness={}
    for case in ['country','hydro_buses','hydro_and_demand_buses']:
        off=offsets(n,m,hp,mask,case);flow=branch_offsets(n,off);h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
        records=[];native=[]
        for t in selected:
            result,x=point(h,m,t,flow[t]);records.append(dict(hour=t,utc=str(n.snapshots[t]),**result))
            if x is not None:
                witness[case+'_'+str(t)]=x
                if case!='country' and t in [selected[0],int(np.argmin(prices))]:native.append(native_point(n,m,t,off.iloc[t],result['objective_eur']))
        cases[case]=dict(records=records,native_checks=native,maximum_flow_offset_mw=float(abs(flow).max()))
        print(case,[(r['hour'],r['status'],round(r.get('price_eur_mwh',0),2)) for r in records],flush=True)
    np.savez_compressed(out/'points.npz',**witness)
    result=dict(status='controlled_input_and_geography_diagnostic_not_baseline',hours=selected,selection='Original Jan/Jul/Dec native hours, worst modeled hour each quarter, global highest modeled price and modeled median; purposive diagnostic, not validation split.',price_checks=checks,cases=cases,nve_summary_sha256=digest(NVE/'summary.json'),nve_audit_sha256=digest(NVE/'audit.json'),producer_sha256=digest(__file__),helper_sha256=digest(ROOT/'tools/nve_hydro_diagnostics.py'),witness_sha256=digest(out/'points.npz'),elapsed_seconds=time.perf_counter()-started,limitations=['Hydro and demand relocation only within Norway; generation offers and other countries unchanged.','Original clustered buses are not verified commercial zones; native parity checks this controlled representation only.','Unchanged fixed water schedule and generation; diagnostic infeasibilities are retained.'])
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Price derivative checks:',[(r['hour'],round(r['saved_price_eur_mwh'],2),r['slopes']) for r in checks],flush=True)

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'data/hydro-observations-2025/price-geography-v1');args=parser.parse_args();args.out.mkdir(exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(900)
    with (args.out/'driver.lock').open('w') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(args.out)
