"""Full-year predeclared wind/fuel/carbon sensitivities on the retained baseline."""
import argparse,fcntl,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from bidding_zone_network_2025 import ROOT,build
from input_sensitivity_2025 import CASES,inputs,compile_case,wind_source_check
from nve_hydro_diagnostics import digest,branch_offsets,solver
from run_regional_water_candidate_2025 import guarded_hour

BASE=ROOT/'data/bidding-zone-network-2025/annual-v7'


def run(out):
    started=time.perf_counter();bs=json.loads((BASE/'summary.json').read_text())
    assert digest(BASE/'annual.npz')==bs['witness_sha256']
    # Write the design before any new clearing or observation-error evaluation.
    (out/'design.json').write_text(json.dumps(dict(cases=CASES,
        metric='All eligible zones; paired common hours; MAE, bias, RMSE, zonal Pearson correlation',
        scope='Sensitivity, not causal error attribution or empirical acceptance',
        wind='Scale weather-limited available MW by +/-10%, capped at existing capacity; solar unchanged',
        fuels='Gas/oil thermal-input prices +/-10%; efficiencies, VOM and other fuel costs unchanged',
        carbon='Assumed EUR80/t becomes EUR72/t or EUR88/t; thermal emissions factors unchanged',
        interaction='Combined +10% case compared with sum of individual +10% price responses',
        fitting='None; 2025 price aggregates already inspected'),indent=2)+'\n')
    n,cost,fixed,mapping,original,old,hp=build();cf=n.get_switchable_as_dense('Generator','p_max_pu').values.copy()
    fuel,assumptions,source=inputs(n);np.testing.assert_array_equal(n.snapshot_weightings.stores,1.)
    wind=wind_source_check(n,cf);prepared=time.perf_counter()-started;records={}
    for name,deltas in CASES.items():
        begin=time.perf_counter();m,off,nc,na=compile_case(n,cost,cf,fixed,deltas,fuel,assumptions)
        assert m['zones']==bs['cases']['bidding_zone']['zones']
        offsets=branch_offsets(n,off);h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
        vals=np.full((8760,m['A'].shape[1]),np.nan);prices=np.full((8760,m['nz']),np.nan)
        obj=np.full(8760,np.nan);valid=np.zeros(8760,bool);fail=[];retries=[];loop=time.perf_counter()
        for day in range(365):
            for t in range(day*24,(day+1)*24):
                r,x=guarded_hour(h,m,t,offsets[t])
                if x is None:
                    first=r.copy();h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
                    r,x=guarded_hour(h,m,t,offsets[t]);retries.append(dict(hour=t,first=first,final=r))
                if x is None:fail.append(dict(hour=t,status=r['status']))
                else:
                    vals[t]=x;prices[t]=h.getSolution().row_dual[:m['nz']];obj[t]=r['objective_eur'];valid[t]=True
        elapsed=time.perf_counter()-loop
        path=out/(name+'.npz');np.savez_compressed(path,values=vals,prices=prices,objectives=obj,optimal=valid)
        records[name]=dict(deltas=deltas,optimal_hours=int(valid.sum()),failures=fail,retries=retries,
            loop_seconds=elapsed,case_seconds=time.perf_counter()-begin,witness_sha256=digest(path),
            cost_sha256=__import__('hashlib').sha256(nc.tobytes()).hexdigest(),
            availability_sha256=__import__('hashlib').sha256(na.tobytes()).hexdigest(),
            emergency_mwh=float(vals[valid,:m['ng']][:,m['emergency_mask']].sum()))
        print(name,records[name]['optimal_hours'],'hours',round(elapsed,3),'seconds','failures',len(fail),flush=True)
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values())
                  if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    summary=dict(status='completed_predeclared_sensitivity_not_error_attribution',cases=records,zones=m['zones'],
        baseline_summary_sha256=digest(BASE/'summary.json'),baseline_witness_sha256=digest(BASE/'annual.npz'),
        mapping_sha256=__import__('hashlib').sha256(json.dumps(mapping,sort_keys=True).encode()).hexdigest(),
        design_sha256=digest(out/'design.json'),producer_sha256=digest(__file__),dependencies=dependencies,
        source=source,wind_observations=wind,preparation_seconds=prepared,
        end_to_end_seconds=time.perf_counter()-started,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        unchanged=['hydro schedules and water','demand','network ratings/topology','GSK/capacity weights','non-target offers/availability'],
        versions={k:__import__(k).__version__ for k in ['numpy','pandas','pypsa','scipy']})
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('saved summary',flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False);lock=(args.out/'driver.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);run(args.out)
