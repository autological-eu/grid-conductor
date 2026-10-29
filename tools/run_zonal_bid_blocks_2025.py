"""Finite two-stage zonal calibration; every proposal clears the physical network."""
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
from generation_mix_2025 import ROOT,digest
from bid_calibration_2025 import NTRAIN,prepare,month_quantities,loss,summaries,immutable_hashes
from zonal_bid_blocks_2025 import DESIGN,STRENGTHS,split_model,active_pairs,costs,proposal,objective,regularization,choose,canonical_parameters
from run_bid_calibration_2025 import solve_case
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets


def write(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')


def run(out):
    began=time.perf_counter();write(out/'design.json',DESIGN)
    previous=ROOT/'data/bidding-zone-network-2025/bid-calibration-v1'
    prior=json.loads((previous/'summary.json').read_text());audit=json.loads((previous/'verification-v1/audit.json').read_text())
    assert audit['summary_sha256']==digest(previous/'summary.json')
    for file,sha in prior['dependencies'].items():assert digest(ROOT/'tools'/file)==sha
    for file,sha in prior['source_hashes'].items():assert digest(ROOT/file)==sha
    sources=prior['source_hashes'].copy()
    for file in ['summary.json','verification-v1/audit.json','training-targets.npz','evaluation-targets.npz']:
        p=previous/file;sources[str(p.relative_to(ROOT))]=digest(p)
    assert digest(previous/'training-targets.npz')==prior['training_target_sha256']
    (out/'training-targets.npz').write_bytes((previous/'training-targets.npz').read_bytes())
    with np.load(out/'training-targets.npz') as z:training={k:z[k] for k in z.files}
    print('Rebuilding fixed physical network, then partitioning thermal offers 70/30',flush=True)
    n,raw,fixed,mapping,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    assert immutable_hashes(base,flow)==prior['immutable_inputs']
    context=prepare(n,base,raw,fixed);m,ctx,layout=split_model(base,context);active=active_pairs(m,ctx)
    assert m['zones']==prior['zones'] and context['countries']==prior['countries']
    write(out/'layout.json',layout);physical=immutable_hashes(m,flow)
    prepared=time.perf_counter()-began
    control_x,control_p,control=solve_case(m,flow,m['cost'],8760,out/'control.npz')
    if control['failures']:raise ValueError('Control incomplete; preserve witness, no calibration')
    with np.load(previous/'control.npz') as z:control['original_unsplit_price_max_difference']=float(abs(control_p-z['row_duals'][:,:m['nz']]).max())
    monthly=month_quantities(ctx,control_x,0);baseline=loss(control_p[:NTRAIN],monthly[:6],training)
    zeros=np.zeros((m['nz'],3));records=[];cache={};stages=[]
    def evaluate(offset,spread):
        offset,spread=canonical_parameters(offset,spread)
        key=json.dumps([offset.tolist(),spread.tolist()])
        if key in cache:return cache[key]
        i=len(records);control_case=not offset.any() and not spread.any();filename='control.npz' if control_case else f'train-{i:02d}.npz'
        if control_case:x,p,info=control_x[:NTRAIN],control_p[:NTRAIN],control
        else:x,p,info=solve_case(m,flow,costs(m,ctx,layout,offset,spread),NTRAIN,out/filename)
        if info['failures']:raw_loss=None;score=None
        else:raw_loss=loss(p,month_quantities(ctx,x,0),training);score=objective(raw_loss,baseline,offset,spread,active)
        record=dict(index=i,offsets=offset.tolist(),spreads=spread.tolist(),raw=raw_loss,score=score,
                    penalty=regularization(offset,spread,active),witness=filename,**info)
        records.append(record);cache[key]=record
        write(out/'training-progress.json',dict(records=records,stages=stages))
        print('Training trial',i,'score',score,'nonzero offsets/spreads',int(np.count_nonzero(offset)),int(np.count_nonzero(spread)),flush=True)
        return record
    def training_witness(record):
        with np.load(out/record['witness']) as z:return z['values'][:NTRAIN],z['row_duals'][:NTRAIN,:m['nz']]
    evaluate(zeros,zeros)
    direction,counts=proposal(m,ctx,control_x[:NTRAIN],control_p[:NTRAIN],training['prices'],'offset')
    write(out/'offset-proposal.json',dict(values=direction.tolist(),evidence=counts,training_target_sha256=digest(out/'training-targets.npz')))
    alternatives=[evaluate(strength*direction,zeros) for strength in STRENGTHS];offset_winner=choose(alternatives)
    stages.append(dict(stage='offset',candidates=[r['index'] for r in alternatives],selected_index=offset_winner['index']))
    fitted_offset=np.array(offset_winner['offsets']);x,p=training_witness(offset_winner)
    adjusted=m|dict(cost=costs(m,ctx,layout,fitted_offset,zeros))
    direction,counts=proposal(adjusted,ctx,x,p,training['prices'],'spread')
    write(out/'spread-proposal.json',dict(values=direction.tolist(),evidence=counts,training_source_index=offset_winner['index'],training_target_sha256=digest(out/'training-targets.npz')))
    alternatives=[evaluate(fitted_offset,strength*direction) for strength in STRENGTHS];block_winner=choose(alternatives)
    stages.append(dict(stage='spread',candidates=[r['index'] for r in alternatives],selected_index=block_winner['index']))
    selection=dict(stages=stages,training_records=records,design_sha256=digest(out/'design.json'),training_target_sha256=digest(out/'training-targets.npz'),
                   offset_proposal_sha256=digest(out/'offset-proposal.json'),spread_proposal_sha256=digest(out/'spread-proposal.json'))
    write(out/'selection.json',selection);print('Sealed both training selections; opening evaluation targets',flush=True)
    assert digest(previous/'evaluation-targets.npz')==prior['evaluation_target_sha256']
    (out/'evaluation-targets.npz').write_bytes((previous/'evaluation-targets.npz').read_bytes())
    with np.load(out/'evaluation-targets.npz') as z:evaluation={k:z[k] for k in z.files}
    def outcome(p,mon):return dict(training=summaries(p[:NTRAIN],training,m['zones'],mon[:6],ctx['countries']),
                                  evaluation=summaries(p[NTRAIN:],evaluation,m['zones'],mon[6:],ctx['countries']))
    annuals=dict(control=dict(training_index=0,witness='control.npz',**control));outcomes=dict(control=outcome(control_p,monthly));done={0:('control',control_x,control_p,monthly)}
    for name,winner in [('zonal_offsets',offset_winner),('zonal_blocks',block_winner)]:
        index=winner['index']
        if index in done:
            other,x,p,mon=done[index];annuals[name]=dict(annuals[other],uses_annual_case=other);outcomes[name]=outcomes[other]
        else:
            cost=costs(m,ctx,layout,np.array(winner['offsets']),np.array(winner['spreads']));filename=name+'.npz'
            x,p,info=solve_case(m,flow,cost,8760,out/filename)
            annuals[name]=dict(training_index=index,witness=filename,**info)
            if info['failures']:raise ValueError('Annual selected-stage evaluation incomplete; preserve failure witness')
            mon=month_quantities(ctx,x,0);outcomes[name]=outcome(p,mon);done[index]=(name,x,p,mon)
    assert immutable_hashes(m,flow)==physical and immutable_hashes(base,flow)==prior['immutable_inputs']
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    result=dict(status='two_stage_zonal_bid_experiment_not_promoted',design=DESIGN,zones=m['zones'],countries=ctx['countries'],active_pairs=active.tolist(),
                source_hashes=sources,dependencies=dependencies,producer_sha256=digest(__file__),original_physical_inputs=prior['immutable_inputs'],expanded_physical_inputs=physical,
                annuals=annuals,outcomes=outcomes,training_trials=len(records),preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began,
                peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                files={f:digest(out/f) for f in ['design.json','layout.json','training-targets.npz','evaluation-targets.npz','selection.json','offset-proposal.json','spread-proposal.json']})
    write(out/'summary.json',result)
    print('Completed:',json.dumps({k:dict(mae=v['evaluation']['equal_zone_mae'],r=v['evaluation']['mean_zonal_correlation']) for k,v in outcomes.items()}),flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False);lock=(args.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);run(args.out)
