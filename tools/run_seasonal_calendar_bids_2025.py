"""Season-spanning nested month evaluation plus separately labelled annual refit."""
import argparse,fcntl,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,MONTH,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets,solver
from run_regional_water_candidate_2025 import guarded_hour
from bid_calibration_2025 import prepare,month_quantities,loss,immutable_hashes
from hourly_offer_curves_2025 import compile_curves,shape_metrics,summarize
from seasonal_calendar_bids_2025 import DESIGN,calendar,fold_months,interior,proposals,country_shares,bids


def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')


def clear(m,flow,cost,hours,path):
    start=time.perf_counter();case=m|{k:m[k][hours] for k in ['availability','load','island_rhs','link_min','link_max']};case['cost']=cost[hours]
    h=solver(case);h.setOptionValue('primal_feasibility_tolerance',1e-8)
    x=np.full((len(hours),m['A'].shape[1]),np.nan);y=np.full((len(hours),m['A'].shape[0]),np.nan);obj=np.full(len(hours),np.nan);ok=np.zeros(len(hours),bool);failed=[]
    for t,hour in enumerate(hours):
        r,v=guarded_hour(h,case,t,flow[hour])
        if v is None:
            h=solver(case);h.setOptionValue('primal_feasibility_tolerance',1e-8);r,v=guarded_hour(h,case,t,flow[hour])
        if v is None:failed.append(dict(hour=int(hour),**r))
        else:x[t]=v;y[t]=h.getSolution().row_dual;obj[t]=r['objective_eur'];ok[t]=True
    seconds=time.perf_counter()-start
    np.savez_compressed(path,values=x,row_duals=y,objectives=obj,optimal=ok,hours=hours)
    info=dict(witness=path.name,witness_sha256=digest(path),optimal_hours=int(ok.sum()),hours=len(hours),failures=failed,clearing_seconds=seconds)
    if failed:raise ValueError('Incomplete seasonal case; preserve failure witness '+str(info))
    return x,y,obj,info


def monthly_selected(ctx,x,hours):
    result=[]
    for month in sorted(set(MONTH[hours])):
        ids=np.flatnonzero(MONTH[hours]==month);original=hours[ids]
        assert np.array_equal(original,np.flatnonzero(MONTH==month))
        result+=month_quantities(ctx,x[ids],int(original[0]))
    return result


def score_case(ctx,x,p,hours,observed,target,months):
    mon=monthly_selected(ctx,x,hours);target_subset=dict(prices=observed[hours],generation=target['generation'][np.array(months)-1],trade=target['trade'][np.array(months)-1],months=np.array(months))
    r=loss(p,mon,target_subset)
    good=interior(months)[hours];eligible=[];shape=[]
    for j in range(p.shape[1]):
        q=shape_metrics(p[good,j],observed[hours[good],j])
        if q['known_hours']:eligible.append(q['mae_eur_mwh'])
        if q['complete_utc_days']:shape.append(q['demeaned_mae'])
    r['price']=float(np.mean(eligible));r['shape']=float(np.mean(shape));return r


def summary_prices(p,o,zones,folds=None,hours=None):
    r=summarize(p,o,zones)
    if folds is not None or hours is not None:
        for j,row in enumerate(r['zones']):
            valid=np.isfinite(o[:-1,j])&np.isfinite(o[1:,j])
            if folds is not None:valid&=folds[:-1]==folds[1:]
            if hours is not None:valid&=np.diff(hours)==1
            row['ramp_mae']=float(abs(np.diff(p[:,j])[valid]-np.diff(o[:,j])[valid]).mean()) if valid.any() else None
    return r


def run(out):
    began=time.perf_counter();write(out/'design.json',DESIGN)
    prior=ROOT/'data/bidding-zone-network-2025/hourly-offer-curves-v1';ps=json.loads((prior/'summary.json').read_text())
    assert json.loads((prior/'verification-v1/audit.json').read_text())['summary_sha256']==digest(prior/'summary.json')
    for p,h in ps['source_hashes'].items():assert digest(ROOT/p)==h
    for p,h in ps['dependencies'].items():assert digest(ROOT/'tools'/p)==h
    sources=ps['source_hashes'].copy()
    for name in ['summary.json','verification-v1/audit.json','development-targets.npz','evaluation-targets.npz']:
        p=prior/name;sources[str(p.relative_to(ROOT))]=digest(p)
    # File names retained for independent raw-source replay, NOT the new folds.
    for source,dest in [('development-targets.npz','development-targets.npz'),('evaluation-targets.npz','evaluation-targets.npz')]:
        (out/dest).write_bytes((prior/source).read_bytes())
    with np.load(out/'development-targets.npz') as z:a={k:z[k] for k in z.files}
    with np.load(out/'evaluation-targets.npz') as z:b={k:z[k] for k in z.files}
    target={k:np.concatenate([a[k],b[k]]) for k in a};observed=target['prices']
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    assert immutable_hashes(base,flow)==ps['original_physical_inputs']
    m,ctx,layout=compile_curves(base,prepare(n,base,raw,fixed));assert immutable_hashes(m,flow)==ps['expanded_physical_inputs']
    write(out/'layout.json',layout)
    info=ps['annuals']['control'];path=prior/info['witness'];assert digest(path)==info['witness_sha256'];sources[str(path.relative_to(ROOT))]=digest(path)
    with np.load(path) as z:assert z['optimal'].all();cx=z['values'];cy=z['row_duals'];co=z['objectives']
    cp=cy[:,:m['nz']];control_info=info|dict(witness=str(path.relative_to(ROOT)),external=True)
    monthly=month_quantities(ctx,cx,0);x,season=calendar(m['zones']);shares=country_shares(n,layout,ctx['countries'])
    np.savez_compressed(out/'calendar.npz',features=x,season=season,country_shares=shares)
    prepared=time.perf_counter()-began;folds=[];ox=np.full_like(cx,np.nan);oy=np.full_like(cy,np.nan);oo=np.full_like(co,np.nan);owners=np.full(8760,-1,int)
    for f in range(3):
        split=fold_months(f);beta,gamma,counts,used=proposals(x,season,cp,observed,monthly,target,split['fit'])
        write(out/f'proposal-{f}.json',dict(beta=beta.tolist(),gamma=gamma.tolist(),price_training_hours=counts,ember_training_months=used.tolist()))
        ids=np.flatnonzero(np.isin(MONTH,split['selection']));records=[]
        baseline=score_case(ctx,cx[ids],cp[ids],ids,observed,target,split['selection'])
        for variant in range(3):
            c=bids(m,layout,x,season,beta,gamma,shares,variant)
            if variant==0:v,p,inf=cx[ids],cp[ids],control_info
            else:
                v,y,_,inf=clear(m,flow,c,ids,out/f'selection-{f}-{variant}.npz');p=y[:,:m['nz']]
            r=score_case(ctx,v,p,ids,observed,target,split['selection'])
            active_columns=np.array([k in ['gas','coal','nuclear'] and m['availability'][:,j].max()>0 for j,k in enumerate(layout['kinds'])])
            reg=.01*float(np.mean(((c-m['cost'])[interior(split['fit'])][:,active_columns]/30)**2)) if variant else 0.
            value=float(np.mean([r[k]/max(baseline[k],1e-9) for k in ['price','shape','generation','trade']])+reg)
            records.append(dict(variant=variant,raw=r,penalty=reg,score=value,case=inf))
            print('Seasonal selection',f,DESIGN['variants'][variant],value,flush=True)
        minimum=min(r['score'] for r in records);winner=min(r['variant'] for r in records if r['score']<=minimum+1e-12)
        write(out/f'selection-{f}.json',dict(split=split,winner=winner,records=records))
        ids=np.flatnonzero(np.isin(MONTH,split['test']))
        if winner==0:v,y,obj,inf=cx[ids],cy[ids],co[ids],control_info
        else:v,y,obj,inf=clear(m,flow,bids(m,layout,x,season,beta,gamma,shares,winner),ids,out/f'test-{f}.npz')
        ox[ids]=v;oy[ids]=y;oo[ids]=obj;owners[ids]=f
        folds.append(dict(index=f,split=split,winner=winner,records=records,test=inf,test_metrics=summary_prices(y[:,:m['nz']],observed[ids],m['zones'],hours=ids),test_raw=score_case(ctx,v,y[:,:m['nz']],ids,observed,target,split['test'])))
        write(out/'progress.json',dict(folds=folds));print('Sealed fold',f,'winner',winner,flush=True)
    assert (owners>=0).all() and np.isfinite(ox).all()
    np.savez_compressed(out/'out-of-fold.npz',values=ox,row_duals=oy,objectives=oo,optimal=np.ones(8760,bool),fold=owners)
    winner=int(np.argmax(np.bincount([f['winner'] for f in folds],minlength=3)))
    write(out/'refit-selection.json',dict(winner=winner,rule=DESIGN['refit']))
    beta,gamma,counts,used=proposals(x,season,cp,observed,monthly,target,list(range(1,13)))
    write(out/'proposal-refit.json',dict(beta=beta.tolist(),gamma=gamma.tolist(),price_training_hours=counts,ember_training_months=used.tolist()))
    if winner==0:rx,ry,ro,refit_info=cx,cy,co,control_info
    else:rx,ry,ro,refit_info=clear(m,flow,bids(m,layout,x,season,beta,gamma,shares,winner),np.arange(8760),out/'refit.npz')
    outcomes={};annuals={}
    for name,v,y,inf in [('control',cx,cy,control_info),('combined',ox,oy,dict(witness='out-of-fold.npz',witness_sha256=digest(out/'out-of-fold.npz'),optimal_hours=8760,failures=[],clearing_seconds=sum(f['test']['clearing_seconds'] for f in folds))),('refit',rx,ry,refit_info)]:
        e=v[:,:m['ng']][:,m['emergency_mask']].sum(axis=1);annuals[name]=inf|dict(emergency_mwh=float(e.sum()),emergency_hours=int((e>1e-6).sum()))
        outcomes[name]=dict(prices=summary_prices(y[:,:m['nz']],observed,m['zones'],owners if name in ['control','combined'] else None),raw=score_case(ctx,v,y[:,:m['nz']],np.arange(8760),observed,target,list(range(1,13))))
    active=np.zeros((m['nz'],3),bool)
    for j,k in enumerate(layout['kinds']):
        if k in ['gas','coal','nuclear'] and m['availability'][:,j].max()>0:active[m['zones'].index(m['offer_zones'][j]),['gas','coal','nuclear'].index(k)]=True
    assert immutable_hashes(base,flow)==ps['original_physical_inputs'] and immutable_hashes(m,flow)==ps['expanded_physical_inputs']
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    files=['design.json','layout.json','calendar.npz','development-targets.npz','evaluation-targets.npz','refit-selection.json','proposal-refit.json']+[f'{k}-{f}.json' for k in ['proposal','selection'] for f in range(3)]
    result=dict(status='seasonal_calendar_oof_and_separate_insample_refit_not_promoted',design=DESIGN,zones=m['zones'],countries=ctx['countries'],folds=folds,refit_variant=winner,annuals=annuals,outcomes=outcomes,
        active_pairs=active.tolist(),original_physical_inputs=ps['original_physical_inputs'],expanded_physical_inputs=ps['expanded_physical_inputs'],source_hashes=sources,dependencies=dependencies,producer_sha256=digest(__file__),files={p:digest(out/p) for p in files},
        preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
    write(out/'summary.json',result);print('Seasonal completed',[(f['index'],f['winner']) for f in folds],{k:v['prices']['equal_zone_mae'] for k,v in outcomes.items()},flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);run(a.out)
