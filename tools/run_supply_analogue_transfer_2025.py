"""Frozen-checkpoint, price-blind analogue transfer: full February, three rules."""
import fcntl
import json
import time
import traceback
from pathlib import Path
import numpy as np
import run_independent_hourly_transport_2025 as source_study
from supply_analogue_transfer_2025 import features,match,transfer,match_neighbor_days
from independent_hourly_transport_2025 import initialize,physical_clear
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from supply_knot_network_2025 import generation
from run_differentiable_spline_2025 import atomic_json

OUT=ROOT/'data/bidding-zone-network-2025/supply-analogue-transfer-v1'
PLAN=ROOT/'config/supply-analogue-transfer-2025.json'


def setup():
    base,full=source_study.setup()
    assert source_study.provenance(base)==json.loads((source_study.OUT/'provenance.json').read_text())
    return base,full


def provenance(base):
    result=source_study.provenance(base)
    paths=[PLAN,Path(__file__),ROOT/'tools/supply_analogue_transfer_2025.py',ROOT/'tools/test_supply_analogue_transfer_2025.py',
           source_study.OUT/'summary.json',source_study.OUT/'audit.json',source_study.OUT/'history.json',
           source_study.OUT/'iteration-010/parameters.npz',source_study.OUT/'iteration-010/forward.npz']
    result.update({str(p.relative_to(ROOT)):digest(p) for p in paths})
    return result


def run():
    OUT.mkdir(exist_ok=True);lock=(OUT/'job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert not (OUT/'summary.json').exists(),'Completed; do not duplicate'
    assert not (OUT/'failure.json').exists(),'Inspect failure before resuming'
    base,(state,market,_,_)=setup();pinned=provenance(base)
    if (OUT/'provenance.json').exists():assert json.loads((OUT/'provenance.json').read_text())==pinned
    atomic_json(OUT/'provenance.json',pinned)
    plan=json.loads(PLAN.read_text());source,data,_,_,capacity=state;hours=np.arange(744,1416)
    assert plan['source_iteration']==10
    parent=json.loads((source_study.OUT/'audit.json').read_text());assert parent['status'].startswith('passed_')
    history=json.loads((source_study.OUT/'history.json').read_text())
    path=source_study.OUT/'iteration-010/parameters.npz';assert digest(path)==history[10]['parameter_sha256']
    with np.load(path) as z:theta=z['theta']
    neutral,_=initialize(source,data,np.arange(744))
    matrix,meta=features(source,data);base.save(OUT/'features.npz',matrix=matrix);atomic_json(OUT/'features.json',meta)
    with np.load(source_study.OUT/'iteration-010/forward.npz') as z:warm=z['prices']
    cases=[]
    for method in plan['methods']:
        folder=OUT/method;folder.mkdir(exist_ok=True)
        if (folder/'record.json').exists():
            record=json.loads((folder/'record.json').read_text())
            for kind in ['fast','physical']:assert digest(folder/(kind+'.npz'))==record[kind+'_sha256']
            cases.append(record);continue
        began=time.perf_counter()
        if method=='neighbor_zone_day':
            donors,weights,diagnostic=match_neighbor_days(matrix,meta['feature_zone_ids'],market.edges,
                                                         [g['zone_id'] for g in source['groups']],market.nz)
        else:donors,weights,diagnostic=match(matrix,method)
        parameters,fallback=transfer(theta,data['capacity'],donors,weights,neutral[0])
        base.save(folder/'transfer.npz',parameters=parameters,donor_hours=donors,weights=weights)
        frozen=digest(folder/'transfer.npz');matching_seconds=time.perf_counter()-began
        atomic_json(OUT/'progress.json',dict(stage='fast-analogue-forward',method=method,hours=672,zones=48))
        result=market.solve(parameters,hours,p0=warm)
        generated=generation(source,data,capacity,result['quantities_gw']*1000,hours)
        fast_score,_=metric(source,data,result['prices'],generated,hours,2)
        base.save(folder/'fast.npz',hours=hours,prices=result['prices'],quantities_gw=result['quantities_gw'],
                  flows_gw=result['flows_gw'],generation=generated)
        def progress(done,total):
            atomic_json(OUT/'progress.json',dict(stage='physical-analogue-LP100',method=method,done=done,hours=total,zones=48))
        physical,info=physical_clear(state,market,parameters,hours,bins=100,progress=progress)
        gen=generation(source,data,capacity,physical['quantities_gw']*1000,hours)
        physical_score,_=metric(source,data,physical['prices'],gen,hours,2)
        physical['generation']=gen;base.save(folder/'physical.npz',**physical)
        assert digest(folder/'transfer.npz')==frozen
        record=dict(method=method,matching_seconds=matching_seconds,diagnostic=diagnostic,fallback=fallback,
                    transfer_sha256=frozen,fast_metrics=fast_score,fast_seconds=result['seconds'],fast_certificate=result['certificate'],
                    physical_metrics=physical_score,physical_info=info,fast_sha256=digest(folder/'fast.npz'),physical_sha256=digest(folder/'physical.npz'))
        atomic_json(folder/'record.json',record);cases.append(record)
        print('ANALOGUE',method,'FAST',fast_score,'PHYSICAL',physical_score,'TIME',matching_seconds,result['seconds'],info['seconds'],flush=True)
    assert provenance(base)==pinned
    atomic_json(OUT/'summary.json',dict(status='price_blind_analogue_transfer_complete',primary=plan['primary'],
                checkpoint=10,hours=672,zones=48,cases=cases,features_sha256=digest(OUT/'features.npz'),
                feature_metadata_sha256=digest(OUT/'features.json'),independent_audit='pending'))
    atomic_json(OUT/'progress.json',dict(stage='analogue-tests-complete-awaiting-audit'))


if __name__=='__main__':
    try:run()
    except Exception:
        OUT.mkdir(exist_ok=True);atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()));raise
