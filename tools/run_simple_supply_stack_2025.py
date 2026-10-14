"""Full-year isolated/coupled controls with unchanged source supply inputs."""
import argparse,fcntl,hashlib,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from bidding_zone_network_2025 import ROOT,build
from nve_hydro_diagnostics import digest
from simple_supply_stack_2025 import prepare,merit_order,transport_solver,clear
BASE=ROOT/'data/bidding-zone-network-2025/annual-v7'

def run(out):
    start=time.perf_counter()
    (out/'design.json').write_text(json.dumps(dict(
        controls=['isolated island/zone merit order','coupled island/zone transport'],
        fixed='Identical demand, generator availability/bids, fixed hydro chronology and controllable-link bounds; no flexible hydro or fitting',
        capacity='Sum existing cross-zone AC ratings; optimistic source-model envelope, not independently validated NTC/JAO',
        islands='Separate island/zone balances. For shared commercial labels, compare the island with greatest annual model demand; never chosen using prices',
        missing='Isolated fixed-hydro surplus requires export; prices stay NaN, no dumping sink or clipping. Source emergency offers remain explicit',
        acceptance='Descriptive paired all-eligible-zone comparison; no native AC feasibility or empirical acceptance inferred'),indent=2)+'\n')
    bs=json.loads((BASE/'summary.json').read_text());assert digest(BASE/'annual.npz')==bs['witness_sha256']
    n,cost,fixed,mapping,original,old,hp=build();m=prepare(n,cost,fixed)
    print('Prepared',len(m['nodes']),'island/zone nodes and',len(m['edges']),'transfers',flush=True)
    np.savez_compressed(out/'inputs.npz',cost=m['cost'],availability=m['availability'],demand=m['demand'],fixed=m['fixed'],lower=m['lower'],upper=m['upper'])
    prepared=time.perf_counter()-start;ng=m['ng'];nn=len(m['nodes']);v=np.full((8760,ng),np.nan);p=np.full((8760,nn),np.nan);valid=np.zeros_like(p,bool);iso_start=time.perf_counter()
    for j in range(nn):
        ids=np.flatnonzero(m['offer_nodes']==j);q,price,good=merit_order(m['cost'][:,ids],m['availability'][:,ids],m['load'][:,j])
        v[:,ids]=q;p[:,j]=price;valid[:,j]=good
    np.savez_compressed(out/'isolated.npz',values=v,prices=p,valid=valid)
    isolated_seconds=time.perf_counter()-iso_start;h=transport_solver(m)
    x=np.full((8760,m['A'].shape[1]),np.nan);prices=np.full((8760,nn),np.nan);obj=np.full(8760,np.nan);good=np.zeros(8760,bool);fail=[];began=time.perf_counter()
    for day in range(365):
        for t in range(day*24,(day+1)*24):
            r,values,price=clear(h,m,t)
            if values is None:h=transport_solver(m);r,values,price=clear(h,m,t)
            if values is None:fail.append(dict(hour=t,**r))
            else:x[t]=values;prices[t]=price;obj[t]=r['objective_eur'];good[t]=True
        if day%90==0:print('day',day,'optimal',int(good.sum()),'failed',len(fail),flush=True)
    loop=time.perf_counter()-began;np.savez_compressed(out/'coupled.npz',values=x,prices=prices,objectives=obj,valid=good)
    metadata={k:m[k] for k in ['nodes','areas','primary','busnode','members','edges']}
    deps={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    summary=dict(status='simpler_supply_stack_diagnostic_not_supported_market_constraints',metadata=metadata,
        isolated_seconds=isolated_seconds,coupled_loop_seconds=loop,preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-start,
        optimal_coupled_hours=int(good.sum()),failures=fail,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        baseline_summary_sha256=digest(BASE/'summary.json'),baseline_witness_sha256=digest(BASE/'annual.npz'),
        witnesses={name:digest(out/name) for name in ['inputs.npz','isolated.npz','coupled.npz']},design_sha256=digest(out/'design.json'),
        mapping_sha256=hashlib.sha256(json.dumps(mapping,sort_keys=True).encode()).hexdigest(),producer_sha256=digest(__file__),dependencies=deps)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('Saved',summary['optimal_coupled_hours'],'hours;',round(loop,3),'seconds clearing',flush=True)

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1200);run(a.out)
