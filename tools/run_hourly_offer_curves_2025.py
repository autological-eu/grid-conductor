"""Bounded joint offer fitting, chronological selection and annual evaluation."""
import argparse,fcntl,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,digest
from bid_calibration_2025 import prepare,month_quantities,summaries,immutable_hashes
from hourly_offer_curves_2025 import FIT,SELECT,DESIGN,NAMES,compile_curves,offer_costs,offset_direction,loss4,penalty,score,choose,period_target,summarize,local_profile
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import solver,branch_offsets
from run_regional_water_candidate_2025 import guarded_hour


def write(path,data):path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def solve_window(m,flow,cost,start,stop,path):
    began=time.perf_counter();case=m|{k:m[k][start:stop] for k in ['availability','load','link_min','link_max','island_rhs']};case['cost']=cost[start:stop]
    h=solver(case);h.setOptionValue('primal_feasibility_tolerance',1e-8);T=stop-start
    x=np.full((T,m['A'].shape[1]),np.nan);y=np.full((T,m['A'].shape[0]),np.nan);obj=np.full(T,np.nan);valid=np.zeros(T,bool);fail=[]
    for day in range(0,T,24):
        for t in range(day,min(day+24,T)):
            r,v=guarded_hour(h,case,t,flow[start+t])
            if v is None:
                h=solver(case);h.setOptionValue('primal_feasibility_tolerance',1e-8);r,v=guarded_hour(h,case,t,flow[start+t])
            if v is None:fail.append(dict(hour=start+t,**r))
            else:x[t]=v;y[t]=h.getSolution().row_dual;obj[t]=r['objective_eur'];valid[t]=True
    seconds=time.perf_counter()-began;np.savez_compressed(path,values=x,row_duals=y,objectives=obj,optimal=valid)
    return x,y[:,:m['nz']],dict(witness=path.name,witness_sha256=digest(path),start=start,stop=stop,optimal_hours=int(valid.sum()),failures=fail,clearing_seconds=seconds)


def run(out):
    began=time.perf_counter();write(out/'design.json',DESIGN)
    prior=ROOT/'data/bidding-zone-network-2025/bid-calibration-v1';old=json.loads((prior/'summary.json').read_text())
    assert json.loads((prior/'verification-v1/audit.json').read_text())['summary_sha256']==digest(prior/'summary.json')
    for name,sha in old['source_hashes'].items():assert digest(ROOT/name)==sha
    for name,sha in old['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    diag=ROOT/'data/bidding-zone-network-2025/hourly-shape-diagnosis-v2';ds=json.loads((diag/'summary.json').read_text())
    assert ds['helper_sha256']==digest(ROOT/'tools/hourly_offer_curves_2025.py') and ds['producer_sha256']==digest(ROOT/'tools/diagnose_hourly_price_shape_2025.py')
    for name,sha in ds['source_hashes'].items():assert digest(ROOT/name)==sha
    sources=old['source_hashes']|ds['source_hashes']
    for p in [prior/'summary.json',prior/'verification-v1/audit.json',prior/'training-targets.npz',prior/'evaluation-targets.npz',diag/'summary.json']:sources[str(p.relative_to(ROOT))]=digest(p)
    assert digest(prior/'training-targets.npz')==old['training_target_sha256']
    (out/'development-targets.npz').write_bytes((prior/'training-targets.npz').read_bytes())
    with np.load(out/'development-targets.npz') as z:half={k:z[k] for k in z.files}
    targets={stage:period_target(half,stage) for stage in ['fit','selection']}
    print('Rebuilding unchanged network; mixed-source groups partitioned before renewable discounts',flush=True)
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    assert immutable_hashes(base,flow)==old['immutable_inputs'];context=prepare(n,base,raw,fixed);m,ctx,layout=compile_curves(base,context)
    assert ctx['countries']==old['countries'] and m['zones']==old['zones']
    write(out/'layout.json',layout);expanded=immutable_hashes(m,flow);prepared=time.perf_counter()-began
    cx,cp,control=solve_window(m,flow,m['cost'],0,8760,out/'control.npz')
    if control['failures']:raise ValueError('Control failed; no calibration')
    direction,evidence=offset_direction(m,layout,cx[:FIT],cp[:FIT],targets['fit']['prices'])
    write(out/'offset-proposal.json',dict(values=direction.tolist(),evidence=evidence))
    active=np.zeros((m['nz'],3),bool)
    for j,k in enumerate(layout['kinds']):
        if k in NAMES and m['availability'][:,j].max()>0:active[m['zones'].index(m['offer_zones'][j]),NAMES.index(k)]=True
    control_months=month_quantities(ctx,cx,0)
    controls={stage:loss4(cp[a:b],control_months[i:j],targets[stage]) for stage,a,b,i,j in [('fit',0,FIT,0,4),('selection',FIT,SELECT,4,6)]}
    records=[];cache={}
    def fit(params):
        params=[float(v) for v in params];key=tuple(params)
        if key in cache:return cache[key]
        index=len(records);reg=penalty(direction,active,params)
        if not any(params):x,p,info=cx[:FIT],cp[:FIT],control
        else:x,p,info=solve_window(m,flow,offer_costs(m,layout,direction,params),0,FIT,out/f'fit-{index:02d}.npz')
        rawloss=None if info['failures'] else loss4(p,month_quantities(ctx,x,0),targets['fit'])
        record=dict(index=index,params=params,penalty=reg,fit=info,fit_raw=rawloss,fit_score=None if rawloss is None else score(rawloss,controls['fit'],reg))
        records.append(record);cache[key]=record;write(out/'progress.json',dict(records=records))
        print('Fit',index,params,'score',record['fit_score'],flush=True);return record
    def select(record):
        if 'selection' in record:return record
        if not any(record['params']):x,p,info=cx[FIT:SELECT],cp[FIT:SELECT],control
        else:x,p,info=solve_window(m,flow,offer_costs(m,layout,direction,record['params']),FIT,SELECT,out/f"selection-{record['index']:02d}.npz")
        rawloss=None if info['failures'] else loss4(p,month_quantities(ctx,x,FIT),targets['selection'])
        record.update(selection=info,selection_raw=rawloss,selection_score=None if rawloss is None else score(rawloss,controls['selection'],record['penalty']))
        return record
    thermal=[fit([a,b,0]) for a in [0.,.5,1.] for b in [0.,.5,1.]]
    nonzero=sorted([r for r in thermal if r['index']!=0 and r['fit_score'] is not None],key=lambda r:(r['fit_score'],r['penalty'],r['index']))[:2]
    shortlist=[records[0]]+nonzero
    write(out/'thermal-shortlist.json',dict(indices=[r['index'] for r in shortlist],fit_records=records.copy(),scope='Sealed before selection losses; best two nonzero fit states plus zero control'))
    thermal_winner=choose([select(r) for r in shortlist],'selection_score')
    write(out/'thermal-selection.json',dict(index=thermal_winner['index'],params=thermal_winner['params'],records=records))
    renewable=[fit(thermal_winner['params'][:2]+[d]) for d in [0.,10.,30.]]
    write(out/'renewable-fit.json',dict(indices=[r['index'] for r in renewable],fit_records=records.copy(),thermal_index=thermal_winner['index']))
    winner=choose([select(r) for r in renewable],'selection_score')
    selection=dict(thermal_index=thermal_winner['index'],selected_index=winner['index'],records=records,shortlist_sha256=digest(out/'thermal-shortlist.json'),
                   thermal_selection_sha256=digest(out/'thermal-selection.json'),renewable_fit_sha256=digest(out/'renewable-fit.json'))
    write(out/'selection.json',selection);print('Sealed May–June selections',thermal_winner['params'],winner['params'],'; opening evaluation targets',flush=True)
    assert digest(prior/'evaluation-targets.npz')==old['evaluation_target_sha256'];(out/'evaluation-targets.npz').write_bytes((prior/'evaluation-targets.npz').read_bytes())
    with np.load(out/'evaluation-targets.npz') as z:targets['evaluation']={k:z[k] for k in z.files}
    def outcome(p,monthly):
        result={}
        for stage,start,stop,mi,mj in [('fit',0,FIT,0,4),('selection',FIT,SELECT,4,6),('evaluation',SELECT,8760,6,12)]:
            target=targets[stage];mon=monthly[mi:mj];legacy=summaries(p[start:stop],target,m['zones'],mon,ctx['countries'])
            result[stage]=dict(prices=summarize(p[start:stop],target['prices'],m['zones']),raw=loss4(p[start:stop],mon,target),generation=legacy['generation'])
        return result
    annuals=dict(control=dict(index=0,**control));outcomes=dict(control=outcome(cp,control_months));done={0:'control'};annual_values={'control':cx}
    for name,r in [('thermal',thermal_winner),('combined',winner)]:
        index=r['index']
        if index in done:
            alias=done[index];annuals[name]=dict(annuals[alias],uses_annual_case=alias);outcomes[name]=outcomes[alias];annual_values[name]=annual_values[alias]
        else:
            x,p,info=solve_window(m,flow,offer_costs(m,layout,direction,r['params']),0,8760,out/(name+'.npz'))
            if info['failures']:raise ValueError('Selected annual case incomplete; preserve witness and failures')
            annuals[name]=dict(index=index,**info);outcomes[name]=outcome(p,month_quantities(ctx,x,0));done[index]=name;annual_values[name]=x
    # Dispatchable headroom is descriptive local availability minus saved output, not deliverable reserve.
    input_inventory=[]
    for zone in m['zones']:
        for family in NAMES:
            ids=[j for j,k in enumerate(layout['kinds']) if k==family and m['offer_zones'][j]==zone]
            if not ids:continue
            available=m['availability'][:,ids].sum(axis=1)
            if available.max()==0:continue
            q=cx[:,ids].sum(axis=1);headroom=available-q
            input_inventory.append(dict(zone=zone,resource=family,available_min_mw=float(available.min()),available_max_mw=float(available.max()),
                                        available_constant=bool(np.ptp(available)<1e-6),control_headroom_median_mw=float(np.median(headroom)),control_headroom_p10_mw=float(np.quantile(headroom,.1))))
    assert immutable_hashes(base,flow)==old['immutable_inputs'] and immutable_hashes(m,flow)==expanded
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    files=['design.json','layout.json','development-targets.npz','evaluation-targets.npz','offset-proposal.json','thermal-shortlist.json','thermal-selection.json','renewable-fit.json','selection.json']
    result=dict(status='hourly_offer_curves_retrospective_not_promoted',design=DESIGN,zones=m['zones'],countries=ctx['countries'],active_pairs=active.tolist(),annuals=annuals,outcomes=outcomes,input_inventory=input_inventory,
                original_physical_inputs=old['immutable_inputs'],expanded_physical_inputs=expanded,source_hashes=sources,dependencies=dependencies,producer_sha256=digest(__file__),files={f:digest(out/f) for f in files},
                preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
    write(out/'summary.json',result)
    print('Completed annual evaluation',json.dumps({k:v['evaluation']['prices']['equal_zone_mae'] for k,v in outcomes.items()}),flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);run(a.out)
