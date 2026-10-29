"""Strict, solar-aligned monthly transport fits with fresh provenance and locks."""
import argparse
import fcntl
import hashlib
import json
import resource
import time
import traceback

import numpy as np

from batched_transport_newton_recovery_2025 import RecoveredTransportMarket
from fit_identified_mixed_flow_2025 import fit
from flow_adjusted_zonal_clearing_2025 import DEST, observed_exchanges
from generation_mix_2025 import ROOT,digest
from monthly_lp_spline_inputs_2025 import SOLAR,aligned
from solar_country_fit_2025 import write


def identity(updates,rate):
    source=[ROOT/'config/active-research-baseline.json',SOLAR,
            ROOT/'tools/fit_identified_mixed_flow_2025.py',
            ROOT/'tools/monthly_lp_spline_inputs_2025.py',
            ROOT/'tools/batched_transport_dispatch_2025.py',
            ROOT/'tools/batched_transport_newton_recovery_2025.py',
            ROOT/'tools/fit_identified_aligned_mixed_flow_2025.py']
    return dict(protocol='aligned_solar_identifiable_price_exact_gradient',updates=updates,
        adam_rate=rate,allow_projected_gradient=False,
        sources={str(p.relative_to(ROOT)):digest(p) for p in source})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--months',nargs='+',type=int,required=True)
    parser.add_argument('--updates',type=int,choices=[20,100],required=True)
    parser.add_argument('--rate',type=float,default=1.)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    if not args.months or any(not 1<=m<=12 for m in args.months) or len(set(args.months))!=len(args.months):
        raise ValueError('Require unique valid months')
    if args.rate!=1.:raise ValueError('This declared trial uses Adam rate 1.0')
    root=DEST/f'aligned-mixed-flow-identified-v1-u{args.updates}-r1'
    root.mkdir(exist_ok=True)
    lock=(root/'job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    proposed=identity(args.updates,args.rate);manifest=root/'inputs.json'
    if manifest.exists():
        if json.loads(manifest.read_text())!=proposed:raise ValueError('Changed source/protocol for existing checkpoint')
        if not args.resume:raise ValueError('Existing run requires explicit --resume after job inspection')
    else:
        if args.resume:raise ValueError('No matching run to resume')
        write(manifest,proposed)
    _,state,old,_,_=aligned();s,d,*_=state
    market=RecoveredTransportMarket(old.zones,old.groups,old.lower,old.upper,
        old.edges,old.capacity,old.source,old.load,cost=old.cost,
        thermal_tau=old.thermal_tau,renewable_tau=old.renewable_tau,
        flow_tau=old.flow_tau)
    np.testing.assert_allclose(market.capacity,d['capacity']/1000,atol=1e-9,rtol=0)
    _,covered,_,observed_flow=observed_exchanges(s['zones'],market.edges,return_edges=True)
    known=np.isfinite(observed_flow)
    flow_mask=known&(observed_flow>=market.lower-1e-8)&(observed_flow<=market.upper+1e-8)
    print('ALIGNED',len(s['zones']),market.ng,'groups',len(market.edges),'edges',flush=True)
    for month in args.months:
        path=root/f'month-{month:02d}'
        if path.exists() and not args.resume:raise ValueError('Existing monthly folder')
        path.mkdir(exist_ok=True)
        if (path/'summary.json').exists():
            with np.load(path/'curves.npz') as z:
                if z['weights'].shape!=(24,market.ng,6):raise ValueError('Changed completed curves')
            print('COMPLETE',month,flush=True);continue
        if (path/'failure.json').exists() and not args.resume:
            raise ValueError('Inspect failure before resuming')
        started=time.perf_counter()
        try:
            summary,weights,history=fit(month,args.updates,args.rate,market,s,d,
                observed_flow,flow_mask,~covered,path,allow_projected_gradient=False)
            np.savez_compressed(path/'curves.npz',weights=weights)
            write(path/'summary.json',summary|dict(curves_sha256=digest(path/'curves.npz'),
                inputs_sha256=digest(manifest),wall_seconds=time.perf_counter()-started))
            print('MONTH_COMPLETE',month,summary['final']['all_price_mae'],flush=True)
        except Exception:
            write(path/'failure.json',dict(month=month,traceback=traceback.format_exc(),
                inputs_sha256=digest(manifest),wall_seconds=time.perf_counter()-started))
            raise


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
    main()
