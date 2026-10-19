"""Two predeclared reconstruction rounds, full-year forward clears; no physics fit."""
import argparse,fcntl,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from bid_calibration_2025 import prepare,immutable_hashes,month_quantities,loss
from hourly_offer_curves_2025 import compile_curves
from seasonal_calendar_bids_2025 import bids
from nve_hydro_diagnostics import branch_offsets
from run_seasonal_calendar_bids_2025 import clear,summary_prices
from inverse_bid_ensemble_2025 import PLAN,zero,proposal,advance,costs,fingerprint,penalty,record_score,best,ensemble,fuel_points


def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda a:a.tolist())+'\n')


def run(out):
    began=time.perf_counter();design=json.loads(PLAN.read_text());write(out/'design.json',design)
    accepted=json.loads((ROOT/'config/research-baseline.json').read_text());root=ROOT/Path(accepted['summary_path']).parent
    s=json.loads((root/'summary.json').read_text());assert digest(root/'summary.json')==accepted['summary_sha256'] and digest(root/'verification-v1/audit.json')==accepted['audit_sha256']
    for p,h in s['source_hashes'].items():assert digest(ROOT/p)==h
    for p,h in s['dependencies'].items():assert digest(ROOT/'tools'/p)==h
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    assert immutable_hashes(base,flow)==s['original_physical_inputs']
    m,ctx,layout=compile_curves(base,prepare(n,base,raw,fixed));assert immutable_hashes(m,flow)==s['expanded_physical_inputs'];assert layout==json.loads((root/'layout.json').read_text())
    with np.load(root/'calendar.npz') as z:full=z['features'];season=z['season'];shares=z['country_shares']
    features=full[:,:,[0,1,2,3,4]]
    p=json.loads((root/'proposal-refit.json').read_text());anchor=bids(m,layout,full,season,np.array(p['beta']),np.array(p['gamma']),shares,s['refit_variant'])
    with np.load(root/'development-targets.npz') as z:target={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z:target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    sources=s['source_hashes'].copy()
    for p in [PLAN,ROOT/'config/research-baseline.json',root/'summary.json',root/'verification-v1/audit.json',root/'layout.json',root/'calendar.npz',root/'proposal-refit.json',root/'development-targets.npz',root/'evaluation-targets.npz',root/accepted['witness']['witness']]:sources[str(p.relative_to(ROOT))]=digest(p)
    records=[];states={};outcomes={};annuals={};attempts=[];proposals=[];cache={};reference=None;prepared=time.perf_counter()-began
    def evaluate(name,state,parent,round_number,step):
        nonlocal reference
        c=costs(m,layout,anchor,features,shares,state,design);key=fingerprint(c)
        if key in cache:return cache[key]
        if name=='baseline':
            path=root/accepted['witness']['witness'];info=accepted['witness']|dict(witness=str(path.relative_to(ROOT)),external=True)
            with np.load(path) as z:x=z['values'];y=z['row_duals']
        else:x,y,_,info=clear(m,flow,c,np.arange(8760),out/(name+'.npz'))
        emergency=float(x[:,:m['ng']][:,m['emergency_mask']].sum());assert abs(emergency)<1e-8
        annuals[name]=info|dict(emergency_mwh=emergency);monthly=month_quantities(ctx,x,0);pr=summary_prices(y[:,:m['nz']],target['prices'],m['zones']);q=loss(y[:,:m['nz']],monthly,target)
        metrics=dict(price=pr['equal_zone_mae'],daily_demeaned_price=pr['mean_demeaned_mae'],generation=q['generation'],trade=q['trade'])
        if reference is None:reference=metrics.copy()
        r=dict(id=name,ordinal=len(records),parent=parent,round=round_number,step=step,bid_sha256=key,metrics=metrics,**record_score(metrics,reference,penalty(m,layout,anchor,c),design))
        records.append(r);states[name]=state;cache[key]=name;outcomes[name]=dict(prices=pr,quantity_errors=q,monthly_quantities=monthly,monthly_fuel_point_twh=fuel_points(ctx,x))
        write(out/(name+'-parameters.json'),state);write(out/'progress.json',dict(records=records,annuals=annuals,attempts=attempts));print(name,metrics,'eligible',r['eligible'],'score',r['score'],flush=True)
        return name
    evaluate('baseline',zero(m['nz'],len(ctx['countries'])),None,0,[0,0,0]);assert abs(reference['price']-accepted['prices']['equal_zone_mae'])<1e-9
    for ri in range(1,design['rounds']+1):
        parent=best(records)['id'];path=ROOT/annuals[parent]['witness'] if annuals[parent].get('external') else out/annuals[parent]['witness']
        with np.load(path) as z:pv=z['values'];py=z['row_duals'][:,:m['nz']]
        pc=costs(m,layout,anchor,features,shares,states[parent],design)
        prop=proposal(m,layout,features,season,pc,pv,py,target['prices'],outcomes[parent]['monthly_quantities'],target,design);write(out/f'round-{ri}-proposal.json',prop);proposals.append(dict(round=ri,parent=parent,sha256=digest(out/f'round-{ri}-proposal.json')))
        del pv,py,pc
        for si,step in enumerate(design['steps']):
            requested=f'r{ri}-s{si+1}';actual=evaluate(requested,advance(states[parent],prop,step,design),parent,ri,step);attempts.append(dict(round=ri,parent=parent,step=step,requested=requested,actual=actual))
    members=ensemble(records,states,design);stack=[]
    for name in members:
        path=ROOT/annuals[name]['witness'] if annuals[name].get('external') else out/annuals[name]['witness']
        with np.load(path) as z:stack.append(z['row_duals'][:,:m['nz']])
    stack=np.array(stack);low=stack.min(axis=0);high=stack.max(axis=0);coverage=[]
    for j,zone in enumerate(m['zones']):
        known=np.isfinite(target['prices'][:,j]);coverage.append(dict(zone=zone,known_hours=int(known.sum()),observed_in_minmax_fraction=float(((target['prices'][known,j]>=low[known,j]-1e-8)&(target['prices'][known,j]<=high[known,j]+1e-8)).mean()) if known.any() else None,mean_width_eur_mwh=float((high[:,j]-low[:,j]).mean())))
    assert immutable_hashes(m,flow)==s['expanded_physical_inputs'];assert len(annuals)-1<=design['maximum_new_annual_solves']
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    write(out/'summary.json',dict(status='bounded_inverse_reconstruction_ensemble_complete_not_promoted',design=design,accepted_folder=str(root.relative_to(ROOT)),zones=m['zones'],countries=ctx['countries'],reference=reference,records=records,attempts=attempts,proposals=proposals,annuals=annuals,outcomes=outcomes,members=members,coverage=coverage,source_hashes=sources,dependencies=dependencies,producer_sha256=digest(__file__),physical_inputs=s['expanded_physical_inputs'],parameter_hashes={k:digest(out/(k+'-parameters.json')) for k in states},preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
    print('Completed; members',members,flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);run(a.out)
