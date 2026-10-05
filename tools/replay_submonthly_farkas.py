"""Independent zero-objective finite-bound support replay; no solver call."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import OptimizeResult
from monthly_dispatch import digest,save
from disk_storage_blocks import load_block
from check_storage_dual_bounds import objective_support
from submonthly_farkas_support import zero_objective
from audit_submonthly_warm_calendar import primal_checks


def audit(args):
    target=args.folder/'independent-replay.json'
    if target.exists():raise ValueError('Preserve prior feasibility replay')
    path=args.folder/'verified.json';record=json.loads(path.read_text());tools=Path(__file__).parent
    source=digest(args.input);annual_path=args.annual/'verified.json';annual=json.loads(annual_path.read_text())
    if record['status']!='farkas_support_requires_independent_replay' or record['input_sha256']!=source or annual['input_sha256']!=source or record['producer_sha256']!=digest(tools/'audit_submonthly_farkas.py') or record['anchor_audit_sha256']!=digest(annual_path):
        raise ValueError('Source-matched ray and verified annual anchor required')
    for name,value in record['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Ray producer dependency changed')
    index=record['index'];row=next(r for r in annual['rows'] if r['index']==index)
    block_path=args.calendar/f'{index:02d}'/'block.npz';primal_path=args.warm/f"{row['month']:02d}"/f'{index:02d}-primal.npz'
    witness=args.folder/'witness.npz'
    if digest(block_path)!=record['block_sha256'] or row['block_sha256']!=record['block_sha256'] or digest(primal_path)!=record['anchor_primal_sha256'] or row['primal_sha256']!=record['anchor_primal_sha256'] or digest(witness)!=record['witness_sha256']:
        raise ValueError('Ray or verified anchor content changed')
    with np.load(witness,allow_pickle=False) as data:arrays={name:data[name].copy() for name in data.files}
    with np.load(primal_path,allow_pickle=False) as data:primal=data['primal'].copy()
    with np.load(args.annual/'annual-state.npz',allow_pickle=False) as data:anchor=data['inventories_mwh'].copy()
    if annual['annual_state_sha256']!=digest(args.annual/'annual-state.npz') or not np.array_equal(anchor,arrays['anchor_state_mwh']):
        raise ValueError('Ray anchor inventory differs')
    block=load_block(block_path);primal_checks(block,anchor,primal);phase=zero_objective(block)
    ne=phase.equality.shape[0];nu=phase.inequality.shape[0];ray=arrays['ray']
    if ray.shape!=(ne+nu,) or not np.isfinite(ray).all() or not np.any(ray):raise ValueError('Invalid saved native ray')
    norm=float(np.max(abs(ray)))
    if norm!=record['ray_normalisation'] or record['ray_orientation'] not in (-1.,1.):raise ValueError('Ray normalisation differs')
    original=ray*record['ray_orientation']/norm
    if not np.array_equal(original[:ne],arrays['equality_duals']) or not np.array_equal(np.minimum(original[ne:],0.),arrays['inequality_duals']):
        raise ValueError('Saved multipliers do not reproduce normalised ray')
    result=OptimizeResult(eqlin=OptimizeResult(marginals=arrays['equality_duals']),ineqlin=OptimizeResult(marginals=arrays['inequality_duals']),
        lower=OptimizeResult(marginals=np.zeros(len(block.cost))),upper=OptimizeResult(marginals=np.zeros(len(block.cost))))
    state=arrays['candidate_state_mwh'];g,intercept=objective_support(phase,state,result)
    value=float(intercept+g@state);at_anchor=float(intercept+g@anchor)
    if not np.array_equal(g,np.asarray(record['gradient'])) or float(intercept)!=record['intercept'] or value!=record['dual_support'] or at_anchor!=record['anchor_support'] or not np.isfinite(value) or value<=1e-7 or at_anchor>1e-7 or record['feasibility_limit']!=1e-7-intercept:
        raise ValueError('Positive supported feasibility cut/anchor does not reproduce')
    summary=dict(status='independently_replayed_farkas_feasibility_cut',index=index,input_sha256=source,
       producer_receipt_sha256=digest(path),witness_sha256=digest(witness),anchor_audit_sha256=digest(annual_path),block_sha256=record['block_sha256'],
       dual_support=value,gradient=g.tolist(),intercept=float(intercept),feasibility_limit=record['feasibility_limit'],anchor_support=at_anchor,
       tool_sha256=digest(Path(__file__)),dependencies={name:digest(tools/name) for name in ['check_storage_dual_bounds.py','submonthly_farkas_support.py','audit_submonthly_warm_calendar.py']},
       scope='Necessary floating-point zero-objective feasibility cut only; not welfare, market price or an annual objective cut. No interval certification.')
    save(target,summary);return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','calendar','warm','annual','folder']:parser.add_argument('--'+name,type=Path,required=True)
    result=audit(parser.parse_args());print(f"Independently replayed necessary ray cut for block {result['index']}; support {result['dual_support']:.6f}, no economic interpretation.")
