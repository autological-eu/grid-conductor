"""Replay saved original-unit master multipliers; no solver or dispatch call."""
import argparse,json,math
from pathlib import Path
import numpy as np
from scipy import sparse
from monthly_dispatch import digest,save
from grouped_master_dual import support


def audit(path):
    target=path.with_suffix('.dual-replay.json')
    if target.exists():raise ValueError('Preserve prior master support replay')
    receipt=json.loads(path.read_text());witness=path.with_suffix('.witness.npz');tools=Path(__file__).parent
    if not receipt['master_equalities_priced'] or receipt['master_witness_sha256']!=digest(witness) or receipt['producer_sha256']!=digest(tools/'build_submonthly_cut_master.py'):
        raise ValueError('Source master producer/witness differs')
    for name,value in receipt['dependencies'].items():
        if digest(tools/name)!=value:raise ValueError('Master calculation dependency changed')
    with np.load(witness,allow_pickle=False) as saved:data={name:saved[name].copy() for name in saved.files}
    matrices={name:sparse.csr_matrix((data[name+'_data'],data[name+'_indices'],data[name+'_indptr']),shape=tuple(data[name+'_shape'])) for name in ['inequality','equality']}
    result=support(data['cost'],matrices['inequality'],data['inequality_rhs'],matrices['equality'],data['equality_rhs'],
                   [tuple(b) for b in data['bounds']],data['inequality_duals'],data['equality_duals'],int(data['shared_variables']))
    if result['lower_bound_eur']!=receipt['lower_bound_eur']:raise ValueError('Saved original-unit multipliers do not reproduce lower support')
    x=data['primal']
    if x.shape!=data['cost'].shape or not np.isfinite(x).all():raise ValueError('Invalid saved master primal')
    result.update(master_receipt_sha256=digest(path),witness_sha256=digest(witness),input_sha256=receipt['input_sha256'],
       primal_objective_eur=math.fsum(float(c)*float(v) for c,v in zip(data['cost'],x)),
       master_equality_residual=float(np.max(abs(matrices['equality']@x-data['equality_rhs']),initial=0.)),
       master_inequality_violation=float(max(0.,np.max(matrices['inequality']@x-data['inequality_rhs'],initial=0.))),
       tool_sha256=digest(Path(__file__)),support_tool_sha256=digest(tools/'grouped_master_dual.py'),
       status='independently_replayed_master_dual_support',
       scope='Finite-box floating-point lower support replay. Saved master primal may have scaled-solver residuals; neither it nor its inventory proposal is a dispatch witness or interval certificate.')
    if result['lower_bound_eur']>receipt['annual_feasible_cost_eur']+1e-7:raise ValueError('Replayed lower support exceeds verified annual incumbent')
    save(target,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--master',type=Path,required=True)
    result=audit(parser.parse_args().master);print(f"Original-unit master lower support replayed: EUR {result['lower_bound_eur']:.6f}. No dispatch feasibility claim.")
