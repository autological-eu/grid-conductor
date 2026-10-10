"""Controlled annual fixed hydro+demand bus placement, unchanged country offer GSK."""
import argparse,json,time,logging,resource,signal,fcntl
from pathlib import Path
import numpy as np,pandas as pd
from nve_hydro_diagnostics import ROOT,NVE,rebuild,offsets,branch_offsets,point,native_point,solver,digest
from compare_daily_dispatch_prices import model_area,metrics,audit_observations


def replay(n,m,values,offset,valid):
    x=values[valid];ng,nl=m['ng'],m['nl'];g=x[:,:ng];f=x[:,ng:ng+nl];q=x[:,ng+nl:]
    supply=np.zeros((len(x),m['nz']))
    for j,z in enumerate(m['offer_zones']):supply[:,m['zones'].index(z)]+=g[:,j]
    worst=float(abs(supply-m['load'][valid]-q).max())
    for value,lo,hi in [(g,0,m['availability'][valid]),(f,m['link_min'][valid],m['link_max'][valid])]:
        worst=max(worst,float(np.maximum(lo-value,0).max()),float(np.maximum(value-hi,0).max()))
    injection=offset.iloc[np.flatnonzero(valid)].copy()
    for z,weights in m['weights'].items():
        for b,w in weights.items():injection[b]+=q[:,m['zones'].index(z)]*w
    for j,(_,e) in enumerate(n.links.iterrows()):injection[e.bus0]-=f[:,j];injection[e.bus1]+=e.efficiency*f[:,j]
    flow_error=island_error=0.
    for _,row in n.sub_networks.iterrows():
        sn=row.obj;island_error=max(island_error,float(abs(injection[sn.buses_i()].sum(axis=1)).max()))
        if len(sn.buses_i())<2:continue
        sn.calculate_PTDF();flows=injection[sn.buses_o].values@np.asarray(sn.PTDF).T
        limits=np.array([n.df(c).loc[name].s_nom*n.df(c).loc[name].s_max_pu for c,name in sn.branches_i()])
        flow_error=max(flow_error,float(np.maximum(abs(flows)-limits,0).max()))
    worst=max(worst,flow_error,island_error)
    if worst>1e-4:raise ValueError('Independent relocated flow replay failed')
    emergency=g[:,m['emergency_mask']].sum(axis=1)
    return dict(optimal_hours_replayed=int(valid.sum()),maximum_residual_mw=worst,passive_limit_excess_mw=flow_error,island_residual_mw=island_error,emergency_mwh=float(emergency.sum()),shortage_hours=int((emergency>1e-6).sum()))


def observations(m,prices,original):
    root=ROOT/'data/price-trace/dispatch-validation-2025-v2';manifest=json.loads((root/'manifest.json').read_text());rows=[]
    for zone,meta in sorted(manifest['zones'].items()):
        area,scope=model_area(zone)
        if area not in m['zones']:continue
        path=root/(zone+'.json');assert digest(path)==meta['hourly_sha256']
        obs=np.array([np.nan if v is None else v for v in json.loads(path.read_text())]);audit_observations(zone,meta,obs)
        j=m['zones'].index(area);matched=np.isfinite(prices[:,j]);common=obs.copy();common[~matched]=np.nan
        rows.append(dict(zone=zone,scope=scope,all_original_hours=metrics(original[:,j],obs),original_same_available_hours=metrics(original[:,j],common),relocated=metrics(prices[:,j],common)))
    return rows,digest(root/'manifest.json')


def run(out):
    begin=time.perf_counter();n,m,hp,mask,water,source=rebuild()
    off=offsets(n,m,hp,mask,'hydro_and_demand_buses');flow=branch_offsets(n,off);prepared=time.perf_counter()-begin
    h=solver(m);h.setOptionValue('primal_feasibility_tolerance',1e-8)
    values=np.full((8760,m['A'].shape[1]),np.nan);prices=np.full((8760,m['nz']),np.nan);obj=np.full(8760,np.nan);valid=np.zeros(8760,dtype=bool);failures=[];start=time.perf_counter()
    for t in range(8760):
        r,x=point(h,m,t,flow[t])
        if x is None:failures.append(dict(hour=t,status=r['status']))
        else:
            valid[t]=True;values[t]=x;prices[t]=np.asarray(h.getSolution().row_dual[:m['nz']]);obj[t]=r['objective_eur']
        if t%2000==0:print('Relocated annual',t,'failed',len(failures),flush=True)
    loop=time.perf_counter()-start;np.savez_compressed(out/'annual.npz',values=values,prices=prices,objectives=obj,optimal=valid)
    physics=replay(n,m,values,off,valid)
    reconstructed=np.sum(values[valid,:m['ng']]*m['cost'][valid],axis=1)
    np.testing.assert_allclose(reconstructed,obj[valid],rtol=1e-8,atol=.05)
    native=[native_point(n,m,t,off.iloc[t],obj[t]) for t in [88,348,4692,8364] if valid[t]]
    with np.load(NVE/'resource_bids.npz',allow_pickle=False) as w:oldprices=w['prices'].copy()
    comparisons,obs_sha=observations(m,prices,oldprices);no=prices[:,m['zones'].index('1:NO')]
    result=dict(status='annual_original_bus_placement_diagnostic_not_market_acceptance',hours=8760,optimal_hours=int(valid.sum()),failures=failures,physics=physics,native_checks=native,observed_price_comparisons=comparisons,observed_manifest_sha256=obs_sha,nve_summary_sha256=digest(NVE/'summary.json'),nve_water_sha256=digest(NVE/'water.npz'),nve_audit_sha256=digest(NVE/'audit.json'),producer_sha256=digest(__file__),helper_sha256=digest(ROOT/'tools/nve_hydro_diagnostics.py'),witness_sha256=digest(out/'annual.npz'),preparation_seconds=prepared,loop_seconds=loop,elapsed_seconds=time.perf_counter()-begin,no_negative_price_hours=int((no<-.000001).sum()),no_above_1000_hours=int((no>1000).sum()),no_mean_price_eur_mwh=float(np.nanmean(no)),fixed_no_hydro_twh=source['total_hydro_bounds_twh'],limitations=['Only Norway fixed hydro and demand relocate, hourly volumes/water/other countries/bids unchanged.','Country generation GSK, original clustered buses, unverified commercial zones and demand scope remain proxies.','No withheld water, spill, changed wind/solar availability or observed-price fitting.','Fixed schedule does not respond to investment. Any failures retained and matched coverage disclosed.'])
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['optimal_hours','physics','no_negative_price_hours','no_mean_price_eur_mwh','loop_seconds']},indent=2),flush=True)

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'data/hydro-observations-2025/bus-geography-annual-v1');args=parser.parse_args();args.out.mkdir(exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(900)
    with (args.out/'driver.lock').open('w') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(args.out)
