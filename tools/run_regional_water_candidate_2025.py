"""Evaluate a fresh five-region water candidate on the frozen European backbone."""
import argparse, fcntl, json, logging, resource, signal, time
from pathlib import Path
import numpy as np
from bidding_zone_network_2025 import ROOT, build
from regional_water_candidate_2025 import prepare
from global_bidding_zone_2025 import compile_global, clear_hour
from nve_hydro_diagnostics import digest, branch_offsets, solver
from run_bidding_zone_network_2025 import observed
from compare_daily_dispatch_prices import metrics

BASELINE=ROOT/'data/bidding-zone-network-2025/annual-v7'


def guarded_hour(h,m,t,offset):
    """Reject, rather than publish, an Optimal solution outside primal tolerance."""
    try:
        return clear_hour(h,m,t,offset)
    except ValueError as error:
        if str(error) != 'Zonal primal replay failed':
            raise
        x=np.array(h.getSolution().col_value);ax=m['A']@x
        lo=np.r_[np.zeros(m['ng']),m['link_min'][t]]
        hi=np.r_[m['availability'][t],m['link_max'][t]]
        rowlo=np.r_[m['load'][t],m['island_rhs'][t],-m['ratings']-offset]
        rowhi=np.r_[m['load'][t],m['island_rhs'][t],m['ratings']-offset]
        residual=max(float(np.maximum(lo-x[:len(lo)],0).max(initial=0)),
                     float(np.maximum(x[:len(lo)]-hi,0).max(initial=0)),
                     float(np.maximum(rowlo-ax,0).max(initial=0)),
                     float(np.maximum(ax-rowhi,0).max(initial=0)))
        return dict(status='Optimal_rejected_primal_guard',maximum_residual_mw=residual),None


def run(out):
    begin=time.perf_counter()
    baseline=json.loads((BASELINE/'summary.json').read_text())
    assert digest(BASELINE/'annual.npz')==baseline['witness_sha256']
    n,cost,fixed,mapping,original,old,hp=build()
    newfixed,water,source=prepare(n,fixed,original,mapping)
    m,off=compile_global(n,cost,newfixed,'bidding_zone');foff=branch_offsets(n,off)
    h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
    preparation=time.perf_counter()-begin
    values=np.full((8760,m['A'].shape[1]),np.nan);prices=np.full((8760,m['nz']),np.nan)
    objectives=np.full(8760,np.nan);valid=np.zeros(8760,dtype=bool);failures=[]
    began=time.perf_counter()
    # Daily orchestration, independent hourly clears; no intertemporal auction claim.
    for day in range(365):
        for t in range(day*24,(day+1)*24):
            r,x=guarded_hour(h,m,t,foff[t]);first=r.copy()
            if x is None:
                h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
                r,x=guarded_hour(h,m,t,foff[t])
            if x is None:failures.append(dict(hour=t,status=r['status'],first_attempt=first,
                                             final_attempt=r))
            else:
                values[t]=x;prices[t]=h.getSolution().row_dual[:m['nz']]
                objectives[t]=r['objective_eur'];valid[t]=True
        if day%60==0:print('day',day,'optimal',int(valid.sum()),'failures',len(failures),flush=True)
    loop=time.perf_counter()-began
    comparisons=observed(m,prices)
    with np.load(BASELINE/'annual.npz') as a:reference=a['bidding_zone_prices'].copy()
    paired=[]
    for row in comparisons:
        if row['metrics']['known_hours']==0:continue
        zone=row['zone'];j=m['zones'].index(row['model_area'])
        assert m['zones']==baseline['cases']['bidding_zone']['zones']
        obs=np.array(json.loads((ROOT/'data/price-trace/dispatch-validation-2025-v2'/(zone+'.json')).read_text()),float)
        obs[~valid]=np.nan
        paired.append(dict(zone=zone,baseline=metrics(reference[:,j],obs),candidate=metrics(prices[:,j],obs),
                           baseline_material_negative_hours=int((reference[valid,j]<-1e-6).sum()),
                           candidate_material_negative_hours=int((prices[valid,j]<-1e-6).sum())))
    np.savez_compressed(out/'annual.npz',values=values,prices=prices,objectives=objectives,optimal=valid,
                        fixed=newfixed.values,**{'water_'+k:v for k,v in water.items()})
    (out/'mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
    summary=dict(status='regional_water_candidate_not_empirically_accepted',hours=8760,days=365,
        optimal_hours=int(valid.sum()),failures=failures,zones=m['zones'],hydro_source=source,
        loop_seconds=loop,preparation_seconds=preparation,end_to_end_seconds=time.perf_counter()-begin,
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        emergency_mwh=float(values[valid,:m['ng']][:,m['emergency_mask']].sum()),
        observations=comparisons,paired=paired,baseline_summary_sha256=digest(BASELINE/'summary.json'),
        baseline_witness_sha256=digest(BASELINE/'annual.npz'),witness_sha256=digest(out/'annual.npz'),
        mapping_sha256=digest(out/'mapping.json'),producer_sha256=digest(__file__),
        dependencies={p.name:digest(p) for p in (ROOT/'tools').glob('*.py')},
        evaluation='No tuning. Previously inspected 2025 observations; descriptive paired comparison, not held-out acceptance.',
        unchanged=['demand','weather availability outside Norwegian ROR','fuel/resource bids','grid and GSK','non-Norwegian fixed hydro'],
        daily_policy='365 UTC days, independent hourly clears, precomputed fixed water schedules')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('completed',summary['optimal_hours'],'hours',round(loop,3),'seconds',flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    lock=(args.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1200)
    run(args.out)
