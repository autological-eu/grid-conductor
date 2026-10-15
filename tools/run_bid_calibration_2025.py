"""Finite bid calibration with chronological fitting/evaluation and unchanged physics."""
import argparse
import fcntl
import json
import logging
import resource
import signal
import sys
import time
from pathlib import Path
import numpy as np
from bid_calibration_2025 import (ROOT,NTRAIN,NAMES,LEVELS,DESIGN,FUELS,prepare,bids,targets,
    month_quantities,loss,score,choose,summaries,immutable_hashes)
from generation_mix_2025 import MONTH,digest,ember_rows
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import solver,branch_offsets
from run_regional_water_candidate_2025 import guarded_hour
from compare_daily_dispatch_prices import audit_observations


def solve_case(m,offsets,cost,hours,path):
    began=time.perf_counter();case=m|dict(cost=cost);h=solver(case);h.setOptionValue('primal_feasibility_tolerance',1e-8)
    x=np.full((hours,m['A'].shape[1]),np.nan);dual=np.full((hours,m['A'].shape[0]),np.nan)
    obj=np.full(hours,np.nan);good=np.zeros(hours,bool);failures=[]
    for start in range(0,hours,24):
        for t in range(start,min(start+24,hours)):
            r,v=guarded_hour(h,case,t,offsets[t])
            if v is None:
                h=solver(case);h.setOptionValue('primal_feasibility_tolerance',1e-8);r,v=guarded_hour(h,case,t,offsets[t])
            if v is None:failures.append(dict(hour=t,**r))
            else:x[t]=v;dual[t]=h.getSolution().row_dual;obj[t]=r['objective_eur'];good[t]=True
    loop=time.perf_counter()-began
    np.savez_compressed(path,values=x,row_duals=dual,objectives=obj,optimal=good)
    return x,dual[:,:m['nz']],dict(optimal_hours=int(good.sum()),failures=failures,clearing_seconds=loop,witness_sha256=digest(path))


def run(out):
    started=time.perf_counter();(out/'design.json').write_text(json.dumps(DESIGN,indent=2)+'\n')
    base=ROOT/'data/bidding-zone-network-2025/annual-v7';bs=json.loads((base/'summary.json').read_text())
    assert digest(base/'annual.npz')==bs['witness_sha256']
    mix=ROOT/'data/bidding-zone-network-2025/generation-mix-v1'
    ma=json.loads((mix/'verification-v2/audit.json').read_text());assert ma['summary_sha256']==digest(mix/'summary.json')
    sources={str(p.relative_to(ROOT)):digest(p) for p in [base/'summary.json',base/'annual.npz',base/'mapping.json',mix/'summary.json',mix/'verification-v2/audit.json']}
    print('Rebuilding unchanged physical source and bid anchors',flush=True)
    n,raw_cost,fixed,mapping,original,old,hp=build();assert mapping==json.loads((base/'mapping.json').read_text())
    m,off=compile_global(n,raw_cost,fixed,'bidding_zone');offsets=branch_offsets(n,off);context=prepare(n,m,raw_cost,fixed)
    sealed=immutable_hashes(m,offsets);base_cost=m['cost'].copy()
    price_root=ROOT/'data/price-trace/dispatch-validation-2025-v2';manifest=json.loads((price_root/'manifest.json').read_text())
    sources[str((price_root/'manifest.json').relative_to(ROOT))]=digest(price_root/'manifest.json')
    prices=np.full((8760,m['nz']),np.nan)
    for z,meta in sorted(manifest['zones'].items()):
        area='IE-SEM' if z=='IE' else z
        if area not in m['zones']:continue
        path=price_root/(z+'.json');assert digest(path)==meta['hourly_sha256']
        values=np.array(json.loads(path.read_text()),float);audit_observations(z,meta,values)
        prices[:,m['zones'].index(area)]=values;sources[str(path.relative_to(ROOT))]=digest(path)
    ember=ROOT/'data/pypsa-eur/ember-current-release/monthly.csv';receipt=ember.parent/'receipt.json'
    assert digest(ember)==json.loads(receipt.read_text())['sha256'];bank=ember_rows(ember)
    for p in [ember,receipt]:sources[str(p.relative_to(ROOT))]=digest(p)
    training=targets(prices,context['countries'],list(range(1,7)),bank)
    np.savez_compressed(out/'training-targets.npz',**training)
    # No evaluation targets or losses are passed to the finite fitting procedure.
    prepared=time.perf_counter()-started
    records=[];cache={};steps=[]
    control_x,control_prices,control=solve_case(m,offsets,base_cost,8760,out/'control.npz')
    if control['failures']:raise ValueError('Uncalibrated control failed; no fitting')
    with np.load(base/'annual.npz') as b:
        control['legacy_maximum_price_difference']=float(abs(control_prices-b['bidding_zone_prices']).max())
    control_months=month_quantities(context,control_x,0)
    baseline=loss(control_prices[:NTRAIN],control_months[:6],training)
    def evaluate(params):
        key=tuple(params)
        if key in cache:return cache[key]
        index=len(records);path=out/f'train-{index:02d}.npz'
        if params==[0.,0.,0.]:
            record=dict(index=index,params=params.copy(),raw=baseline,score=score(baseline,baseline,params),control=True)
        else:
            cost=bids(base_cost,context['classes'],params)
            x,p,r=solve_case(m,offsets,cost,NTRAIN,path)
            if r['failures']:record=dict(index=index,params=params.copy(),raw=None,score=None,**r)
            else:
                monthly=month_quantities(context,x,0);raw=loss(p,monthly,training)
                record=dict(index=index,params=params.copy(),raw=raw,score=score(raw,baseline,params),**r)
        records.append(record);cache[key]=record
        (out/'training-progress.json').write_text(json.dumps(dict(records=records,completed_steps=steps),indent=2)+'\n')
        print('Training trial',index,'adders',params,'score',record['score'],flush=True)
        return record
    current=evaluate([0.,0.,0.])
    for sweep in range(2):
        for axis,name in enumerate(NAMES):
            candidates=[]
            for value in LEVELS[axis]:
                params=current['params'].copy();params[axis]=value;candidates.append(evaluate(params))
            current=choose(candidates)
            steps.append(dict(sweep=sweep+1,axis=name,candidates=[r['index'] for r in candidates],selected_index=current['index']))
    selected=choose(records)
    selection=dict(params=selected['params'],selected_index=selected['index'],training_records=records,steps=steps,
        training_target_sha256=digest(out/'training-targets.npz'),design_sha256=digest(out/'design.json'),
        score=selected['score'],scope='Sealed before evaluation targets/losses; retrospective chronological split')
    (out/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
    selection_sha=digest(out/'selection.json')
    print('Selected training-only adders',selected['params'],'; opening evaluation targets',flush=True)
    evaluation=targets(prices,context['countries'],list(range(7,13)),bank)
    np.savez_compressed(out/'evaluation-targets.npz',**evaluation)
    selected_cost=bids(base_cost,context['classes'],selected['params'])
    if selected['params']==[0.,0.,0.]:
        fit_x,fit_prices,annual=control_x,control_prices,dict(control,uses_control_witness=True)
    else:
        fit_x,fit_prices,annual=solve_case(m,offsets,selected_cost,8760,out/'selected.npz')
    if annual['failures']:raise ValueError('Selected annual evaluation failed; retain failure witness')
    fitted_months=month_quantities(context,fit_x,0)
    outcomes={}
    for name,p,monthly in [('control',control_prices,control_months),('calibrated',fit_prices,fitted_months)]:
        outcomes[name]=dict(training=summaries(p[:NTRAIN],training,m['zones'],monthly[:6],context['countries']),
            evaluation=summaries(p[NTRAIN:],evaluation,m['zones'],monthly[6:],context['countries']))
    assert immutable_hashes(m,offsets)==sealed
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    # Availability-envelope flags are diagnostics, not constraints or omitted targets.
    available=[]
    for month in range(1,7):
        mask=MONTH==month;rows=[]
        for c,f in context['generation_labels']:
            ids=[j for j,key in enumerate(context['generation_keys']) if key==(c,f)]
            rows.append(float(context['availability'][mask][:,ids].sum()/1e6))
        available.append(np.array(rows).reshape(len(context['countries']),len(FUELS)))
    available=np.stack(available);known=np.isfinite(training['generation'])
    flags=dict(known_generation_targets=int(known.sum()),above_original_available_energy_targets=int((known&(training['generation']>available+.001)).sum()),
        excess_reference_twh=float(np.maximum(training['generation'][known]-available[known],0).sum()),retained_in_training_objective=True)
    result=dict(status='bounded_train_only_bid_calibration_not_accepted',design=DESIGN,zones=m['zones'],countries=context['countries'],
        classes=context['classes'],immutable_inputs=sealed,control=control,annual=annual,outcomes=outcomes,selection_sha256=selection_sha,
        training_target_sha256=digest(out/'training-targets.npz'),evaluation_target_sha256=digest(out/'evaluation-targets.npz'),
        source_hashes=sources,dependencies=dependencies,producer_sha256=digest(__file__),helper_sha256=digest(ROOT/'tools/bid_calibration_2025.py'),
        design_sha256=digest(out/'design.json'),preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-started,
        training_quantity_flags=flags,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        limitations=['Training objective weights/bounds are experimental; only two coordinate sweeps, not a global optimum.',
            '2025 is already inspected; chronological evaluation is retrospective, not untouched validation.',
            'Country allocation ranges conditional on saved offer totals; national generation and trade scope unresolved.',
            'Same fixed hydro and all input/constraint proxies; fitting may absorb their errors. No inferred actual order books or investment acceptance.'])
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('Completed calibration:',json.dumps({k:dict(mae=v['evaluation']['equal_zone_mae'],r=v['evaluation']['mean_zonal_correlation']) for k,v in outcomes.items()}),flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);run(a.out)
