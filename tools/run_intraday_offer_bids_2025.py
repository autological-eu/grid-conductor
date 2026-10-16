"""Fresh bounded intraday-bid experiment; preserves completed source producers."""
import argparse,fcntl,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets
from bid_calibration_2025 import prepare,month_quantities,summaries,immutable_hashes
from hourly_offer_curves_2025 import compile_curves,offer_costs,period_target,loss4,score,choose,summarize
from run_hourly_offer_curves_2025 import solve_window
from intraday_offer_bids_2025 import FIT,SELECT,GRID,DESIGN,features,fit_proposal,shift,costs,penalty


def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')


def run(out):
    began=time.perf_counter();write(out/'design.json',DESIGN)
    prior=ROOT/'data/bidding-zone-network-2025/hourly-offer-curves-v1'
    ps=json.loads((prior/'summary.json').read_text());pa=json.loads((prior/'verification-v1/audit.json').read_text())
    assert pa['summary_sha256']==digest(prior/'summary.json')
    for p,h in ps['source_hashes'].items():assert digest(ROOT/p)==h
    for p,h in ps['dependencies'].items():assert digest(ROOT/'tools'/p)==h
    selection=json.loads((prior/'selection.json').read_text());assert selection['records'][selection['selected_index']]['params']==[0.,.5,0.]
    sources=ps['source_hashes'].copy()
    for p in [prior/'summary.json',prior/'verification-v1/audit.json',prior/'selection.json',prior/'layout.json',prior/'development-targets.npz']:
        sources[str(p.relative_to(ROOT))]=digest(p)
    (out/'development-targets.npz').write_bytes((prior/'development-targets.npz').read_bytes())
    with np.load(out/'development-targets.npz') as z:half={k:z[k] for k in z.files}
    targets={stage:period_target(half,stage) for stage in ['fit','selection']}
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    assert immutable_hashes(base,flow)==ps['original_physical_inputs']
    m,ctx,layout=compile_curves(base,prepare(n,base,raw,fixed));assert immutable_hashes(m,flow)==ps['expanded_physical_inputs']
    write(out/'layout.json',layout)
    anchor=offer_costs(m,layout,np.zeros((m['nz'],3)),[0,.5,0])
    old=ps['annuals']['combined'];path=prior/old['witness'];assert digest(path)==old['witness_sha256'];sources[str(path.relative_to(ROOT))]=digest(path)
    with np.load(path) as z:assert z['optimal'].all();cx=z['values'];cp=z['row_duals'][:,:m['nz']]
    x,scale,residual=features(m,layout);beta,counts=fit_proposal(x[:FIT],cp[:FIT],targets['fit']['prices'])
    write(out/'proposal.json',dict(coefficients=beta.tolist(),training_hours=counts,residual_scale_mw=scale.tolist()))
    np.savez_compressed(out/'features.npz',features=x,residual=residual,scales=scale)
    control_months=month_quantities(ctx,cx,0)
    baseline={stage:loss4(cp[a:b],control_months[i:j],targets[stage]) for stage,a,b,i,j in [('fit',0,FIT,0,4),('selection',FIT,SELECT,4,6)]}
    prepared=time.perf_counter()-began;records=[]
    prior_info=old|dict(witness=str(path.relative_to(ROOT)),external=True)
    for i,params in enumerate(GRID):
        hourly=shift(x,beta,params);reg=penalty(hourly);record=dict(index=i,params=params,penalty=reg)
        for stage,start,stop in [('fit',0,FIT),('selection',FIT,SELECT)]:
            if i==0:values,prices,info=cx[start:stop],cp[start:stop],prior_info
            else:values,prices,info=solve_window(m,flow,costs(anchor,m,layout,hourly),start,stop,out/f'{stage}-{i:02d}.npz')
            loss=None if info['failures'] else loss4(prices,month_quantities(ctx,values,start),targets[stage])
            record.update({stage:info,stage+'_raw':loss,stage+'_score':None if loss is None else score(loss,baseline[stage],reg)})
        records.append(record);write(out/'progress.json',dict(records=records))
        print('Intraday fit/selection',params,record['fit_score'],record['selection_score'],flush=True)
    winner=choose(records,'selection_score')
    write(out/'selection.json',dict(selected_index=winner['index'],records=records))
    print('Sealed intraday selection',winner['params'],'; opening evaluation targets',flush=True)
    # Only after the selection receipt: evaluation observations cannot affect bids.
    targetfile=prior/'evaluation-targets.npz';assert digest(targetfile)==ps['files']['evaluation-targets.npz']
    sources[str(targetfile.relative_to(ROOT))]=digest(targetfile);(out/'evaluation-targets.npz').write_bytes(targetfile.read_bytes())
    with np.load(out/'evaluation-targets.npz') as z:targets['evaluation']={k:z[k] for k in z.files}
    if winner['index']==0:values,prices,info=cx,cp,prior_info
    else:values,prices,info=solve_window(m,flow,costs(anchor,m,layout,shift(x,beta,winner['params'])),0,8760,out/'intraday.npz')
    if info['failures']:raise ValueError('Selected annual solve incomplete; preserve failures')
    outcomes={};annuals={}
    for name,v,p,inf in [('previous',cx,cp,prior_info),('combined',values,prices,info)]:
        annuals[name]=inf;monthly=month_quantities(ctx,v,0);outcomes[name]={}
        for stage,start,stop,mi,mj in [('fit',0,FIT,0,4),('selection',FIT,SELECT,4,6),('evaluation',SELECT,8760,6,12)]:
            target=targets[stage];mon=monthly[mi:mj]
            outcomes[name][stage]=dict(prices=summarize(p[start:stop],target['prices'],m['zones']),raw=loss4(p[start:stop],mon,target),
                generation=summaries(p[start:stop],target,m['zones'],mon,ctx['countries'])['generation'])
        emergency=v[:,:m['ng']][:,m['emergency_mask']].sum(axis=1)
        annuals[name]=inf|dict(emergency_mwh=float(emergency.sum()),emergency_hours=int((emergency>1e-6).sum()))
    assert immutable_hashes(base,flow)==ps['original_physical_inputs'] and immutable_hashes(m,flow)==ps['expanded_physical_inputs']
    active=np.zeros((m['nz'],3),bool)
    for j,k in enumerate(layout['kinds']):
        if k in ['gas','coal','nuclear'] and m['availability'][:,j].max()>0:active[m['zones'].index(m['offer_zones'][j]),['gas','coal','nuclear'].index(k)]=True
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    files=['design.json','layout.json','proposal.json','features.npz','development-targets.npz','evaluation-targets.npz','selection.json']
    result=dict(status='intraday_offer_bids_retrospective_not_promoted',design=DESIGN,zones=m['zones'],countries=ctx['countries'],active_pairs=active.tolist(),annuals=annuals,outcomes=outcomes,
        original_physical_inputs=ps['original_physical_inputs'],expanded_physical_inputs=ps['expanded_physical_inputs'],source_hashes=sources,dependencies=dependencies,
        producer_sha256=digest(__file__),files={p:digest(out/p) for p in files},preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began,
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
    write(out/'summary.json',result);print('Intraday completed',winner['params'],{k:v['evaluation']['prices']['equal_zone_mae'] for k,v in outcomes.items()},flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);run(a.out)
