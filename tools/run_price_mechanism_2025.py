"""Capture annual dual witnesses on the unchanged retained baseline."""
import argparse,fcntl,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from bidding_zone_network_2025 import ROOT,build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import digest,branch_offsets,solver
from run_regional_water_candidate_2025 import guarded_hour
from price_mechanism_2025 import offer_members
BASE=ROOT/'data/bidding-zone-network-2025/annual-v7'

def run(out):
    start=time.perf_counter()
    (out/'design.json').write_text(json.dumps(dict(scope='Unchanged baseline dual diagnostic; no candidate or fitted bid',
        marginal='Local interior aggregate offer: dispatch/headroom >0.001 MW; bid/price within 1e-5 EUR/MWh; mixed/tied identities retained',
        network='Price = island-balance term + passive-row term via free zonal injection stationarity. Island term includes HVDC losses/bounds; not a single Europe energy price.',
        caveat='Dual decomposition can depend on degeneracy; witness contributions are not causal error shares or certified market price setters',
        probes='12 calendar-fixed fifteenth-day noon UTC hours; DE-LU, FR, NO1-NO5, SE1-SE4; +/-1 MW demand along the unchanged GSK',
        validation='All eligible observed areas; previously inspected 2025 observations; no held-out acceptance'),indent=2)+'\n')
    bs=json.loads((BASE/'summary.json').read_text());assert digest(BASE/'annual.npz')==bs['witness_sha256']
    n,cost,fixed,mapping,original,old,hp=build();m,off=compile_global(n,cost,fixed,'bidding_zone');offsets=branch_offsets(n,off)
    members=offer_members(n,m,cost);prepared=time.perf_counter()-start
    h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
    values=np.full((8760,m['A'].shape[1]),np.nan);dual=np.full((8760,m['A'].shape[0]),np.nan)
    rc=np.full_like(values,np.nan);objectives=np.full(8760,np.nan);valid=np.zeros(8760,bool);fail=[];began=time.perf_counter()
    for t in range(8760):
        r,x=guarded_hour(h,m,t,offsets[t])
        if x is None:
            first=r.copy();h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8);r,x=guarded_hour(h,m,t,offsets[t])
        if x is None:fail.append(dict(hour=t,status=r['status']))
        else:
            sol=h.getSolution();values[t]=x;dual[t]=sol.row_dual;rc[t]=sol.col_dual;objectives[t]=r['objective_eur'];valid[t]=True
        if t%2000==0:print('hour',t,'valid',int(valid.sum()),'failures',len(fail),flush=True)
    elapsed=time.perf_counter()-began
    np.savez_compressed(out/'annual.npz',values=values,row_duals=dual,col_duals=rc,objectives=objectives,optimal=valid)
    # Fixed calendar probes, never selected by their agreement with observations.
    hours=[int(np.flatnonzero((n.snapshots.month==month)&(n.snapshots.day==15)&(n.snapshots.hour==12))[0]) for month in range(1,13)]
    probes=[];pv={}
    for t in hours:
        if not valid[t]:continue
        for z in ['DE-LU','FR',*[f'NO{i}' for i in range(1,6)],*[f'SE{i}' for i in range(1,5)]]:
            j=m['zones'].index(z);baseline=m['load'][t,j]
            for delta in [-1.,1.]:
                m['load'][t,j]=baseline+delta
                try:
                    worker=solver(m);worker.setOptionValue('primal_feasibility_tolerance',1e-8)
                    r,x=guarded_hour(worker,m,t,offsets[t])
                finally:m['load'][t,j]=baseline
                key=f'{t}_{z}_{delta:+.0f}'
                probes.append(dict(key=key,hour=t,zone=z,delta_mw=delta,**r))
                if x is not None:pv[key]=x
    np.savez_compressed(out/'probes.npz',**pv)
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values())
                  if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    result=dict(status='baseline_price_mechanism_diagnostic',zones=m['zones'],members=members,mapping_sha256=__import__('hashlib').sha256(json.dumps(mapping,sort_keys=True).encode()).hexdigest(),
        optimal_hours=int(valid.sum()),failures=fail,loop_seconds=elapsed,preparation_seconds=prepared,
        end_to_end_seconds=time.perf_counter()-start,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        baseline_summary_sha256=digest(BASE/'summary.json'),baseline_witness_sha256=digest(BASE/'annual.npz'),
        witness_sha256=digest(out/'annual.npz'),probe_witness_sha256=digest(out/'probes.npz'),probes=probes,
        producer_sha256=digest(__file__),dependencies=dependencies,design_sha256=digest(out/'design.json'))
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print('Saved dual diagnostic',int(valid.sum()),'hours',round(elapsed,2),'seconds',flush=True)

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1200);run(a.out)
