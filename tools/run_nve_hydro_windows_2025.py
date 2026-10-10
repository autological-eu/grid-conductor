"""Predeclared ±20% rescheduling probes; each 48-hour window keeps its water budget."""
import argparse,json,time,logging,resource,signal,fcntl
from pathlib import Path
import numpy as np
from nve_hydro_diagnostics import ROOT,NVE,rebuild,digest
from nve_hydro_flexibility import solve_window,native_window

ANNUAL=ROOT/'data/hydro-observations-2025/bus-geography-annual-v1'

def run(out):
    begin=time.perf_counter();n,m,hp,mask,water,_=rebuild();source=json.loads((ANNUAL/'summary.json').read_text())
    assert source['witness_sha256']==digest(ANNUAL/'annual.npz')
    with np.load(NVE/'resource_bids.npz',allow_pickle=False) as w:oldprices=w['prices'].copy();oldobj=w['objectives'].copy()
    with np.load(ANNUAL/'annual.npz',allow_pickle=False) as w:geo_prices=w['prices'].copy();geo_obj=w['objectives'].copy()
    j=m['zones'].index('1:NO');targets=[('original_extreme',88),('ordinary_july',4692),('relocated_extreme',int(np.argmin(geo_prices[:,j])))];windows=[]
    for label,t in targets:
        start=max(0,min(8712,(t//24)*24-24));windows.append((label,t,start,start+48))
    records=[];saved={}
    for label,target,start,end in windows:
        for case in ['country','hydro_and_demand_buses']:
            r,w=solve_window(n,m,hp,mask,water,start,end,case,.2)
            r.update(label=label,target_hour=target,case=case)
            if w is not None:
                fixedobj=oldobj if case=='country' else geo_obj;fixedprices=oldprices if case=='country' else geo_prices
                r.update(fixed_objective_eur=float(fixedobj[start:end].sum()),objective_change_eur=float(r['objective_eur']-fixedobj[start:end].sum()),fixed_mean_no_price_eur_mwh=float(fixedprices[start:end,j].mean()),flexible_mean_no_price_eur_mwh=float(w['prices'][:,j].mean()),fixed_negative_hours=int((fixedprices[start:end,j]<-1e-6).sum()),flexible_negative_hours=int((w['prices'][:,j]<-1e-6).sum()),maximum_absolute_power_shift_mw=float(abs(w['power']-hp[start:end][:,mask]).max()))
                if label=='original_extreme':r['native_check']=native_window(n,m,hp,mask,water,start,end,case,.2,r['objective_eur'])
                for key,value in w.items():saved[label+'_'+case+'_'+key]=value
            records.append(r);print('Window:',label,case,r['status'],round(r.get('objective_change_eur',0),2),flush=True)
    np.savez_compressed(out/'windows.npz',**saved)
    su=n.storage_units.query("carrier=='hydro'").loc[n.storage_units.query("carrier=='hydro'").index[mask]]
    demand=n.get_switchable_as_dense('Load','p_set').loc[:,n.loads.index[n.loads.bus.map(n.buses.country)=='NO']].values.sum()/1e6
    result=dict(status='bounded_water_conserving_48h_diagnostics_not_annual_strategy',selection='Original minimum-price hour, original July native hour, relocated annual minimum-price hour; 48 UTC hours starting one day before target day. Selected from model outcomes, not observations.',fraction=.2,records=records,source_no_demand_twh=float(demand),nve_summary_sha256=digest(NVE/'summary.json'),annual_geography_summary_sha256=digest(ANNUAL/'summary.json'),producer_sha256=digest(__file__),helper_sha256=digest(ROOT/'tools/nve_hydro_diagnostics.py'),flexibility_sha256=digest(ROOT/'tools/nve_hydro_flexibility.py'),witness_sha256=digest(out/'windows.npz'),elapsed_seconds=time.perf_counter()-begin,limitations=['These are jointly optimized finite windows, not a daily policy, annual optimum or market equilibrium.','Each reservoir keeps source inflow/efficiency/capacity/zero spill and original opening/closing stocks; output stays within ±20% and original turbine MW.','Schedules use synthetic bids and physical proxies; no observed-price fitting or annual investment acceptance.'])
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'data/hydro-observations-2025/bounded-windows-v1');args=parser.parse_args();args.out.mkdir(exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(900)
    with (args.out/'driver.lock').open('w') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(args.out)
