"""Full-year fixed-hydro country/zonal control on one boundary-preserving grid."""
import argparse,json,time,logging,resource,signal,fcntl,platform
from pathlib import Path
import numpy as np
import pandas as pd
import pypsa,highspy
from bidding_zone_network_2025 import BASE,ROOT,build,compile_case
from global_bidding_zone_2025 import compile_global,clear_hour
from nve_hydro_diagnostics import digest,branch_offsets,point,native_point,solver
from audit_nve_hydro_diagnostics_2025 import physics
from compare_daily_dispatch_prices import metrics,audit_observations

def observed(m,prices):
    root=ROOT/'data/price-trace/dispatch-validation-2025-v2';manifest=json.loads((root/'manifest.json').read_text());rows=[]
    for zone,meta in sorted(manifest['zones'].items()):
        label=zone if zone!='IE' else 'IE-SEM'
        areas=[z for z in m['zones'] if z==label]
        if not areas:continue
        path=root/(zone+'.json');assert digest(path)==meta['hourly_sha256'];obs=np.array(json.loads(path.read_text()),dtype=float);audit_observations(zone,meta,obs)
        for area in areas:
            model=prices[:,m['zones'].index(area)];common=obs.copy();common[~np.isfinite(model)]=np.nan
            rows.append(dict(zone=zone,model_area=area,scope='Exact label; geographic/physical proxy remains; IE observation is not certified SEM scope' if zone=='IE' else 'Commercial zone label; source boundaries/allocation remain proxies',metrics=metrics(model,common)))
    return rows

def run(out):
    began=time.perf_counter();n,cost,fixed,metadata,original,old,hp=build();prepared=time.perf_counter()-began
    (out/'mapping.json').write_text(json.dumps(metadata,indent=2)+'\n')
    results={};saved={}
    for level in ['country','bidding_zone']:
        m,off=compile_global(n,cost,fixed,level);foff=branch_offsets(n,off);h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
        values=np.full((8760,m['A'].shape[1]),np.nan);prices=np.full((8760,m['nz']),np.nan);objectives=np.full(8760,np.nan);valid=np.zeros(8760,dtype=bool);failures=[];fresh_retries=[];start=time.perf_counter()
        for t in range(8760):
            r,x=clear_hour(h,m,t,foff[t])
            if x is None:
                previous_status=r['status'];h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8);r,x=clear_hour(h,m,t,foff[t]);fresh_retries.append(dict(hour=t,previous_status=previous_status,fresh_status=r['status']))
            if x is None:failures.append(dict(hour=t,status=r['status']))
            else:values[t]=x;prices[t]=h.getSolution().row_dual[:m['nz']];objectives[t]=r['objective_eur'];valid[t]=True
            if t%2000==0:print(level,t,'failures',len(failures),flush=True)
        loop=time.perf_counter()-start
        residual=0.
        # Contiguous blocks permit independent native-component replay of valid
        # hours even when an infeasible fixed-schedule hour is retained.
        ids=np.flatnonzero(valid)
        for group in np.split(ids,np.where(np.diff(ids)!=1)[0]+1):
            if len(group):residual=max(residual,physics(n,m,values[group],m['load'][group],off.iloc[group].reset_index(drop=True).copy(),int(group[0])))
        np.testing.assert_allclose((values[valid,:m['ng']]*m['cost'][valid]).sum(axis=1),objectives[valid],rtol=1e-8,atol=.05)
        native=[native_point(n,m,t,off.iloc[t],objectives[t]) for t in [348,4692,8364] if valid[t]]
        g=values[valid,:m['ng']];emergency=g[:,m['emergency_mask']].sum(axis=1)
        results[level]=dict(zones=m['zones'],optimal_hours=int(valid.sum()),failures=failures,fresh_retries=fresh_retries,loop_seconds=loop,maximum_network_residual_mw=residual,emergency_mwh=float(emergency.sum()),shortage_hours=int((emergency>1e-6).sum()),native_checks=native,observed_price_comparisons=observed(m,prices) if level=='bidding_zone' else [],offer_columns=m['ng'],passive_branches=len(m['ratings']),controllable_links=m['nl'])
        for k,v in dict(values=values,prices=prices,objectives=objectives,optimal=valid).items():saved[level+'_'+k]=v
    np.savez_compressed(out/'annual.npz',**saved)
    result=dict(status='boundary_preserving_zonal_diagnostic_not_market_acceptance',hours=8760,cases=results,preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,mapping_sha256=digest(out/'mapping.json'),witness_sha256=digest(out/'annual.npz'),producer_sha256=digest(__file__),compiler_sha256=digest(ROOT/'tools/bidding_zone_network_2025.py'),dependencies={name:digest(ROOT/'tools'/name) for name in ['global_bidding_zone_2025.py','nve_hydro_diagnostics.py','audit_nve_hydro_diagnostics_2025.py','european_physical_bids_2025.py','european_reservoir_clearing_2025.py','compare_daily_dispatch_prices.py']},observed_manifest_sha256=digest(ROOT/'data/price-trace/dispatch-validation-2025-v2/manifest.json'),versions=dict(python=platform.python_version(),pypsa=pypsa.__version__,highs=highspy.Highs().version()),limitations=metadata['limitations'])
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:{a:v[a] for a in ['optimal_hours','loop_seconds','emergency_mwh','maximum_network_residual_mw']} for k,v in results.items()},indent=2),flush=True)

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=BASE/'annual-v1');args=p.parse_args();args.out.mkdir(exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1200)
    with (args.out/'driver.lock').open('w') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(args.out)
