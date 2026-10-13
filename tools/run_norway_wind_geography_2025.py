"""Fresh, bounded annual geography candidate; no baseline promotion."""
import argparse,fcntl,hashlib,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from bidding_zone_network_2025 import ROOT,build
from norway_wind_geography_2025 import apply
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import digest,branch_offsets,solver
from run_regional_water_candidate_2025 import guarded_hour

BASE=ROOT/'data/bidding-zone-network-2025/annual-v7'

def run(out):
    started=time.perf_counter()
    (out/'design.json').write_text(json.dumps(dict(
        change='NVE dated onshore wind zone shares, with national hourly availability conserved',
        metric='All eligible observed zones; paired valid hours; MAE/bias/RMSE/correlation and seasonal errors',
        fitting='None; 2025 price aggregates already inspected; descriptive comparison, no held-out acceptance',
        baseline='annual-v7; unchanged hydro, demand, fuel costs, offshore wind and grid',
        scope='Geography isolation, not site-weather or national available-energy correction'),indent=2)+'\n')
    n,cost,fixed,mapping,original,old,hp=build();source=apply(n)
    m,off=compile_global(n,cost,fixed,'bidding_zone');offset=branch_offsets(n,off)
    prepared=time.perf_counter()-started;h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
    values=np.full((8760,m['A'].shape[1]),np.nan);prices=np.full((8760,m['nz']),np.nan)
    objectives=np.full(8760,np.nan);valid=np.zeros(8760,bool);fail=[];retries=[];start=time.perf_counter()
    for day in range(365):
        for t in range(day*24,(day+1)*24):
            r,x=guarded_hour(h,m,t,offset[t])
            if x is None:
                first=r.copy();h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
                r,x=guarded_hour(h,m,t,offset[t]);retries.append(dict(hour=t,first=first,final=r))
            if x is None:fail.append(dict(hour=t,status=r['status']))
            else:
                values[t]=x;prices[t]=h.getSolution().row_dual[:m['nz']];objectives[t]=r['objective_eur'];valid[t]=True
    elapsed=time.perf_counter()-start
    np.savez_compressed(out/'annual.npz',values=values,prices=prices,objectives=objectives,optimal=valid)
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values())
                  if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    summary=dict(status='geography_candidate_not_accepted',source=source,zones=m['zones'],
        optimal_hours=int(valid.sum()),failures=fail,retries=retries,
        emergency_mwh=float(values[valid,:m['ng']][:,m['emergency_mask']].sum()),
        preparation_seconds=prepared,loop_seconds=elapsed,end_to_end_seconds=time.perf_counter()-started,
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        producer_sha256=digest(__file__),dependencies=dependencies,
        witness_sha256=digest(out/'annual.npz'),design_sha256=digest(out/'design.json'),
        baseline_summary_sha256=digest(BASE/'summary.json'),baseline_witness_sha256=digest(BASE/'annual.npz'))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['optimal_hours','failures','emergency_mwh','loop_seconds','end_to_end_seconds']},indent=2),flush=True)

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1200);run(a.out)
