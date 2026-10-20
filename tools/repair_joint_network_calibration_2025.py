"""Numerical retries of unchanged declared states; no parameter/grid expansion."""
import argparse,json,logging,resource,signal,sys,time
from pathlib import Path
import highspy,numpy as np
from generation_mix_2025 import ROOT,CARRIER,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets,solver
from run_regional_water_candidate_2025 import guarded_hour
from bid_calibration_2025 import prepare,immutable_hashes,month_quantities,loss
from hourly_offer_curves_2025 import compile_curves
from seasonal_calendar_bids_2025 import bids
from run_seasonal_calendar_bids_2025 import summary_prices
from inverse_bid_ensemble_2025 import costs,fingerprint,penalty,fuel_points
from joint_network_calibration_2025 import transform,score,choose


def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda a:a.tolist())+'\n')


def reliable_clear(case,flow,c,path):
    start=time.perf_counter();case=case|dict(cost=c)
    highspy.Highs.resetGlobalScheduler(True)
    h=solver(case);h.setOptionValue('primal_feasibility_tolerance',1e-8);h.setOptionValue('presolve','off');h.setOptionValue('output_flag',True)
    values=np.empty((8760,case['A'].shape[1]));duals=np.empty((8760,case['A'].shape[0]));obj=np.empty(8760)
    for t in range(8760):
        r,x=guarded_hour(h,case,t,flow[t])
        if t==0:h.setOptionValue('output_flag',False)
        if x is None:
            np.savez_compressed(path,values=values[:t],row_duals=duals[:t],objectives=obj[:t],optimal=np.ones(t,bool),hours=np.arange(t))
            raise RuntimeError('Numerical retry unresolved at hour '+str(t)+' '+str(r))
        values[t]=x;duals[t]=h.getSolution().row_dual;obj[t]=r['objective_eur']
    np.savez_compressed(path,values=values,row_duals=duals,objectives=obj,optimal=np.ones(8760,bool),hours=np.arange(8760))
    return values,duals,dict(witness=path.name,witness_sha256=digest(path),hours=8760,optimal_hours=8760,complete_year=True,failures=[],clearing_seconds=time.perf_counter()-start,source_external=False,numerical_retry=True)


def run(source,out):
    began=time.perf_counter();s=json.loads((source/'summary.json').read_text());d=s['design']
    assert s['producer_sha256']==digest(ROOT/'tools/run_joint_network_calibration_2025.py')
    for p,h in s['source_hashes'].items():assert digest(ROOT/p)==h
    for p,h in s['dependencies'].items():assert digest(ROOT/'tools'/p)==h
    todo=[r['id'] for r in s['records'] if s['annuals'][r['id']].get('rejection')=='unresolved_solver_failure'];assert todo
    original=json.loads(json.dumps(s));root=ROOT/s['accepted_folder'];old=json.loads((root/'summary.json').read_text());prior=ROOT/s['prior_inverse_folder'];ps=json.loads((prior/'summary.json').read_text())
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off);m,ctx,layout=compile_curves(base,prepare(n,base,raw,fixed));assert immutable_hashes(m,flow)==s['original_physical_inputs']
    catalogue=json.loads((source/'branches.json').read_text());(out/'branches.json').write_bytes((source/'branches.json').read_bytes());write(out/'design.json',d)
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values;wind=np.array([CARRIER[c] in ['onshore_wind','offshore_wind'] for c in n.generators.carrier])
    with np.load(root/'calendar.npz') as z:full=z['features'];season=z['season'];shares=z['country_shares']
    p=json.loads((root/'proposal-refit.json').read_text());anchor=bids(m,layout,full,season,np.array(p['beta']),np.array(p['gamma']),shares,old['refit_variant']);state=json.loads((prior/(s['bid_parent']+'-parameters.json')).read_text())
    bidcost={'accepted':anchor,'inverse_joint':costs(m,layout,anchor,full[:,:,[0,1,2,3,4]],shares,state,ps['design'])}
    with np.load(root/'development-targets.npz') as z:target={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z:target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    prepared=time.perf_counter()-began
    for k,info in s['annuals'].items():
        path=ROOT/info['witness'] if info.get('external') else source/info['witness'];assert digest(path)==info['witness_sha256']
        s['source_hashes'][str(path.relative_to(ROOT))]=digest(path)
        s['annuals'][k]=info|dict(witness=str(path.relative_to(ROOT)),external=True,source_external=bool(info.get('external')),reused_source_trial=True)
    for r in s['records']:
        k=r['id']
        if k not in todo:continue
        params=r['parameters'];case,context,f=transform(m,ctx,layout,av,wind,catalogue,params,d);c=bidcost[params['bid']]
        assert immutable_hashes(case,flow)==r['physical_inputs'] and fingerprint(c)==r['bid_sha256']
        # A relaxed-rating case must contain a same-bid/same-wind feasible witness.
        control=f"{params['bid']}-unchanged-w{int(round(params['wind']*100))}";info=s['annuals'][control]
        with np.load(ROOT/info['witness']) as z:x=z['values']
        ax=(case['A']@x.T).T;lo=np.c_[case['load'],case['island_rhs'],-case['ratings']-flow];hi=np.c_[case['load'],case['island_rhs'],case['ratings']-flow]
        feasible=max(float(np.maximum(lo-ax,0).max()),float(np.maximum(ax-hi,0).max()),float(np.maximum(x[:,:m['ng']]-case['availability'],0).max()))
        assert feasible<=1e-4;print('Verified contained feasible control',k,feasible,flush=True)
        x,y,inf=reliable_clear(case,flow,c,out/(k+'.npz'));emergency=float(x[:,:m['ng']][:,m['emergency_mask']].sum());s['annuals'][k]=inf|dict(emergency_mwh=emergency)
        monthly=month_quantities(context,x,0);pr=summary_prices(y[:,:m['nz']],target['prices'],m['zones']);q=loss(y[:,:m['nz']],monthly,target)
        metrics=dict(price=pr['equal_zone_mae'],daily_demeaned_price=pr['mean_demeaned_mae'],generation=q['generation'],trade=q['trade']);r.update(metrics=metrics,**score(metrics,s['reference'],penalty(m,layout,anchor,c),params,d,emergency<=1e-6))
        flows=(case['A']@x.T).T[:,m['nz']+len(m['islands']):]+flow;binding=abs(abs(flows)-case['ratings'])<=1e-4
        diagnostics=dict(binding_branch_hours=int(binding.sum()),branch_hours=binding.size,maximum_loading_ratio=float((abs(flows)/case['ratings']).max()),wind_available_twh=float(av[:,wind].sum()*params['wind']/1e6))
        s['outcomes'][k]=dict(prices=pr,monthly_quantities=monthly,quantity_errors=q,monthly_fuel_point_twh=fuel_points(context,x),network_diagnostics=diagnostics)
        write(out/'progress.json',dict(records=s['records'],annuals=s['annuals']));print('Repaired',k,metrics,r['eligible'],flush=True)
    s['source_hashes'][str((source/'summary.json').relative_to(ROOT))]=digest(source/'summary.json');s['source_hashes'][str((source/'branches.json').relative_to(ROOT))]=digest(source/'branches.json')
    s['winner']=choose(s['records']);s['repair_producer_sha256']=digest(__file__);s['source_trial_folder']=str(source.relative_to(ROOT));s['repairs']=todo
    s['retry_protocol']=dict(solver='HiGHS simplex',global_scheduler='reset before each retry model',presolve='off',primal_feasibility_tolerance=1e-8,parameter_grid='unchanged',feasible_control_checked=True)
    s['stage_timings']=dict(source_driver_seconds=original['end_to_end_seconds'],retry_preparation_seconds=prepared,retry_driver_seconds=time.perf_counter()-began)
    s['verified_fresh_loop_seconds']=sum(v['clearing_seconds'] for v in original['annuals'].values() if not v.get('external'))+sum(s['annuals'][k]['clearing_seconds'] for k in todo)
    s['end_to_end_seconds']=original['end_to_end_seconds']+s['stage_timings']['retry_driver_seconds'];s['peak_rss_mib']=max(original['peak_rss_mib'],resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
    s['status']='joint_calibration_with_independent_numerical_retries_complete_not_promoted';write(out/'summary.json',s);print('Completed numerical repairs; winner',s['winner'],flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('out',type=Path);a=p.parse_args();a.source=a.source.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);run(a.source,a.out)
