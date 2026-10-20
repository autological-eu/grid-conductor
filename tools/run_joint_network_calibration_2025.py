"""Fresh finite full-year joint bid/wind/AC-headroom calibration; prior runs frozen."""
import argparse, fcntl, json, logging, resource, signal, sys, time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT, CARRIER, digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from bid_calibration_2025 import prepare, immutable_hashes, month_quantities, loss
from hourly_offer_curves_2025 import compile_curves
from seasonal_calendar_bids_2025 import bids
from nve_hydro_diagnostics import branch_offsets
from run_seasonal_calendar_bids_2025 import summary_prices
from joint_network_clear_2025 import clear_or_reject
from inverse_bid_ensemble_2025 import costs, fingerprint, penalty, fuel_points
from joint_network_calibration_2025 import PLAN, states, branches, transform, score, choose


def write(p,v): p.write_text(json.dumps(v, indent=2, allow_nan=False, default=lambda x:x.tolist())+'\n')


def run(out):
    began=time.perf_counter(); d=json.loads(PLAN.read_text()); write(out/'design.json',d)
    a=json.loads((ROOT/'config/research-baseline.json').read_text()); root=ROOT/Path(a['summary_path']).parent
    s=json.loads((root/'summary.json').read_text())
    assert digest(root/'summary.json')==a['summary_sha256'] and digest(root/'verification-v1/audit.json')==a['audit_sha256']
    prior=ROOT/'data/bidding-zone-network-2025/inverse-bid-ensemble-v1'; ps=json.loads((prior/'summary.json').read_text()); audit=json.loads((prior/'verification-v1/audit.json').read_text())
    assert audit['summary_sha256']==digest(prior/'summary.json')
    assert audit['status']=='all_inverse_forward_witnesses_proposals_scores_and_finite_ensemble_replayed'
    for manifest in [s,ps]:
        for p,h in manifest['source_hashes'].items(): assert digest(ROOT/p)==h
        for p,h in manifest['dependencies'].items(): assert digest(ROOT/'tools'/p)==h
    interrupted=ROOT/'data/bidding-zone-network-2025/joint-network-calibration-v1'
    previous=json.loads((interrupted/'progress.json').read_text()); interrupted_receipt=json.loads((interrupted/'interrupted.json').read_text())
    assert digest(interrupted/'progress.json')==interrupted_receipt['completed_progress_sha256']
    for name,rel in [('interrupted-producer.py','tools/run_joint_network_calibration_2025.py'),('interrupted-helper.py','tools/joint_network_calibration_2025.py')]:
        assert digest(interrupted/name)==interrupted_receipt['source_hashes'][rel]
    assert digest(ROOT/'tools/joint_network_calibration_2025.py')==interrupted_receipt['source_hashes']['tools/joint_network_calibration_2025.py']
    assert json.loads((interrupted/'design.json').read_text())=={k:v for k,v in d.items() if k!='rejection_policy'}
    n,raw,fixed,*_=build(); base,off=compile_global(n,raw,fixed,'bidding_zone'); flow=branch_offsets(n,off)
    m,ctx,layout=compile_curves(base,prepare(n,base,raw,fixed)); assert immutable_hashes(m,flow)==s['expanded_physical_inputs']
    catalogue=branches(n,d); np.testing.assert_array_equal([r['original_limit_mw'] for r in catalogue],m['ratings']); write(out/'branches.json',catalogue)
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    wind=np.array([CARRIER[c] in ['onshore_wind','offshore_wind'] for c in n.generators.carrier])
    assert wind.any(), 'Missing wind mask'
    with np.load(root/'calendar.npz') as z: full=z['features']; season=z['season']; shares=z['country_shares']
    p=json.loads((root/'proposal-refit.json').read_text()); anchor=bids(m,layout,full,season,np.array(p['beta']),np.array(p['gamma']),shares,s['refit_variant'])
    winner=audit['winning_state']; assert digest(prior/(winner+'-parameters.json'))==ps['parameter_hashes'][winner]; state=json.loads((prior/(winner+'-parameters.json')).read_text()); bidcost={'accepted':anchor,'inverse_joint':costs(m,layout,anchor,full[:,:,[0,1,2,3,4]],shares,state,ps['design'])}
    with np.load(root/'development-targets.npz') as z: target={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z: target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    sources=ps['source_hashes'].copy()
    for path in [PLAN,prior/'summary.json',prior/'verification-v1/audit.json',prior/(winner+'-parameters.json')]: sources[str(path.relative_to(ROOT))]=digest(path)
    for name in ['progress.json','interrupted.json','interrupted-producer.py','interrupted-helper.py','design.json']:
        sources[str((interrupted/name).relative_to(ROOT))]=digest(interrupted/name)
    records=[]; outcomes={}; annuals={}; reference=None; prepared=time.perf_counter()-began
    for ordinal,params in enumerate(states(d)):
        name=params['id']; case,context,factors=transform(m,ctx,layout,av,wind,catalogue,params,d); c=bidcost[params['bid']]
        external=params['network']=='unchanged' and params['wind']==1
        if external:
            info=a['witness'] if params['bid']=='accepted' else ps['annuals'][winner]
            path=root/info['witness'] if params['bid']=='accepted' else prior/info['witness']
            if info.get('external'): path=ROOT/info['witness']
            assert digest(path)==info['witness_sha256']; sources[str(path.relative_to(ROOT))]=digest(path)
            info=info|dict(witness=str(path.relative_to(ROOT)),external=True)
            with np.load(path) as z: x=z['values']; y=z['row_duals']; assert z['optimal'].all()
        elif name=='accepted-unchanged-w90':
            info=previous['annuals'][name]; path=interrupted/info['witness']; assert digest(path)==info['witness_sha256']
            info=info|dict(witness=str(path.relative_to(ROOT)),external=True,reused_interrupted_driver=True)
            sources[str(path.relative_to(ROOT))]=digest(path)
            with np.load(path) as z: x=z['values']; y=z['row_duals']; assert z['optimal'].all()
        else: x,y,_,info=clear_or_reject(case,flow,c,out/(name+'.npz'))
        if x is None:
            annuals[name]=info|dict(emergency_mwh=None)
            record=dict(id=name,ordinal=ordinal,parameters=params,bid_sha256=fingerprint(c),physical_inputs=immutable_hashes(case,flow),metrics=None,score=None,penalty=None,normalized=None,eligible=False)
            records.append(record); outcomes[name]=dict(rejected=info['rejection'])
            write(out/'progress.json',dict(records=records,annuals=annuals)); print('Rejected',name,info['rejection'],'hour',info['failed_hour'],flush=True)
            continue
        emergency=float(x[:,:m['ng']][:,m['emergency_mask']].sum()); annuals[name]=info|dict(emergency_mwh=emergency)
        monthly=month_quantities(context,x,0); pr=summary_prices(y[:,:m['nz']],target['prices'],m['zones']); q=loss(y[:,:m['nz']],monthly,target)
        metrics=dict(price=pr['equal_zone_mae'],daily_demeaned_price=pr['mean_demeaned_mae'],generation=q['generation'],trade=q['trade'])
        if reference is None: reference=metrics.copy(); assert abs(reference['price']-a['prices']['equal_zone_mae'])<1e-9
        result=score(metrics,reference,penalty(m,layout,anchor,c),params,d,info['optimal_hours']==8760 and emergency<=1e-6)
        ax=(case['A']@x.T).T[:,m['nz']+len(m['islands']):]+flow
        binding=np.abs(np.abs(ax)-case['ratings'])<=1e-4
        diagnostics=dict(binding_branch_hours=int(binding.sum()),branch_hours=binding.size,maximum_loading_ratio=float((abs(ax)/case['ratings']).max()),wind_available_twh=float(av[:,wind].sum()*params['wind']/1e6))
        record=dict(id=name,ordinal=ordinal,parameters=params,bid_sha256=fingerprint(c),physical_inputs=immutable_hashes(case,flow),metrics=metrics,**result)
        records.append(record); outcomes[name]=dict(prices=pr,monthly_quantities=monthly,quantity_errors=q,monthly_fuel_point_twh=fuel_points(context,x),network_diagnostics=diagnostics)
        write(out/'progress.json',dict(records=records,annuals=annuals)); print(name,metrics,'eligible',result['eligible'],'score',result['score'],flush=True)
        del x,y,ax,binding,case,context
    assert len(records)==d['maximum_unique_states'] and sum(not v.get('external',False) for v in annuals.values())==d['maximum_new_annual_solves']-1
    assert immutable_hashes(m,flow)==s['expanded_physical_inputs']
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    write(out/'summary.json',dict(status='finite_joint_supply_network_calibration_complete_not_promoted',design=d,accepted_folder=str(root.relative_to(ROOT)),prior_inverse_folder=str(prior.relative_to(ROOT)),bid_parent=winner,zones=m['zones'],countries=ctx['countries'],reference=reference,records=records,annuals=annuals,outcomes=outcomes,winner=choose(records),original_physical_inputs=s['expanded_physical_inputs'],source_hashes=sources,dependencies=dependencies,producer_sha256=digest(__file__),catalogue_sha256=digest(out/'branches.json'),preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
    print('Completed joint trial:',choose(records),flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR); p=argparse.ArgumentParser(); p.add_argument('out',type=Path); a=p.parse_args(); a.out=a.out.resolve(); a.out.mkdir(parents=True,exist_ok=False)
    lock=(a.out/'driver.lock').open('w'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB); resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3)); signal.alarm(3000); run(a.out)
