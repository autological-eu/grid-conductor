"""Two training-selected nonzero diagnostics; primary regularized selection unchanged."""
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
from bid_calibration_2025 import ROOT,prepare,bids,month_quantities,summaries,immutable_hashes
from generation_mix_2025 import digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets
from run_bid_calibration_2025 import solve_case


def run(parent,out):
    began=time.perf_counter();s=json.loads((parent/'summary.json').read_text());selection=json.loads((parent/'selection.json').read_text())
    assert digest(parent/'selection.json')==s['selection_sha256']
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    for path,sha in s['source_hashes'].items():assert digest(ROOT/path)==sha
    records=[r for r in selection['training_records'] if r['score'] is not None and any(r['params'])]
    probes=[dict(label='best_nonzero_joint_training',record=min(records,key=lambda r:(r['score'],tuple(r['params'])))),
            dict(label='best_price_training',record=min(records,key=lambda r:(r['raw']['price'],sum(v*v for v in r['params']),tuple(r['params']))))]
    design=dict(scope='Additional training-selected diagnostics, not replacements for the primary regularized decision',
        selectors=['Lowest joint training score among nonzero tuples','Lowest training price MAE among nonzero tuples'],
        reason='Primary criterion selected zero. Expose nonzero bid tradeoffs without silently changing selection weights or using evaluation to choose a winner.',
        evaluation='Same July–December target artifacts; report every probe even if adverse; no promotion or refitting',
        primary_selection_sha256=s['selection_sha256'],training_records_sha256=digest(parent/'selection.json'),
        choices=[dict(label=p['label'],training_record_index=p['record']['index'],params=p['record']['params']) for p in probes])
    (out/'design.json').write_text(json.dumps(design,indent=2)+'\n')
    # Seal choices before loading any evaluation target or solving a diagnostic.
    choice_sha=digest(out/'design.json')
    training_file=parent/'training-targets.npz';evaluation_file=parent/'evaluation-targets.npz'
    assert digest(training_file)==s['training_target_sha256'] and digest(evaluation_file)==s['evaluation_target_sha256']
    with np.load(training_file) as z:training={k:z[k] for k in z.files}
    with np.load(evaluation_file) as z:evaluation={k:z[k] for k in z.files}
    print('Sealed training-selected diagnostic adders',design['choices'],flush=True)
    n,cost,fixed,mapping,original,old,hp=build();m,off=compile_global(n,cost,fixed,'bidding_zone');offsets=branch_offsets(n,off)
    assert immutable_hashes(m,offsets)==s['immutable_inputs']
    context=prepare(n,m,cost,fixed);prepared=time.perf_counter()-began
    results=[];completed={}
    for index,probe in enumerate(probes):
        params=probe['record']['params'];key=tuple(params)
        if key in completed:
            results.append(dict(completed[key],label=probe['label']));continue
        path=out/f'probe-{index}.npz';x,p,record=solve_case(m,offsets,bids(m['cost'],context['classes'],params),8760,path)
        outcomes=None
        if not record['failures']:
            monthly=month_quantities(context,x,0)
            outcomes=dict(training=summaries(p[:4344],training,m['zones'],monthly[:6],context['countries']),
                          evaluation=summaries(p[4344:],evaluation,m['zones'],monthly[6:],context['countries']))
        row=dict(label=probe['label'],params=params,witness=path.name,outcomes=outcomes,**record)
        results.append(row);completed[key]=row
        print('Annual diagnostic',probe['label'],'optimal',record['optimal_hours'],'evaluation MAE',None if outcomes is None else outcomes['evaluation']['equal_zone_mae'],flush=True)
    assert immutable_hashes(m,offsets)==s['immutable_inputs']
    deps={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    result=dict(status='training_selected_bid_diagnostics_not_primary_selection',primary_summary_sha256=digest(parent/'summary.json'),
        choices_sha256=choice_sha,producer_sha256=digest(__file__),dependencies=deps,probes=results,
        preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began)
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    out=a.out or a.parent/'diagnostic-evaluation-v1';out.mkdir(parents=True,exist_ok=False)
    lock=(out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);run(a.parent,out)
