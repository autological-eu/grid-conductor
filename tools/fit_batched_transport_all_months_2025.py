"""Fit all twelve 2025 months with the original LP-free batched price solver."""
import fcntl
import json
import multiprocessing
import os
import traceback
from pathlib import Path

import numpy as np

import fit_monthly_fast_splines_2025 as shared
from batched_transport_newton_recovery_2025 import RecoveredTransportMarket
from monthly_lp_spline_inputs_2025 import aligned, SOLAR
from run_differentiable_spline_2025 import atomic_json
from sigmoid_month_pairs_2025 import ROOT, digest


OUT=ROOT/'data/bidding-zone-network-2025/batched-transport-monthly-100-v2'
RATE=.5
UPDATES=100


def direct_market(source):
    market=RecoveredTransportMarket(source.zones,source.groups,source.lower,source.upper,
        source.edges,source.capacity,source.source,source.load,cost=source.cost,
        thermal_tau=source.thermal_tau,renewable_tau=source.renewable_tau,
        flow_tau=source.flow_tau)
    market.reference=np.maximum(market.capacity.max(axis=0),.001)
    return market


def main():
    OUT.mkdir(exist_ok=True)
    with (OUT/'job.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (OUT/'failure.json').exists() or (OUT/'complete.json').exists():
            raise ValueError('Inspect previous terminal receipt; no implicit restart')
        base,state,source,_,_=aligned()
        market=direct_market(source)
        shared.OUT=OUT
        shared.RATE=RATE
        shared.UPDATES=UPDATES
        shared.FACTORS=(1.,)  # Original direct solver: no coefficient-step retry.
        sources=base.provenance()
        for path in (Path(__file__),ROOT/'tools/fit_monthly_fast_splines_2025.py',
                     ROOT/'tools/batched_transport_dispatch_2025.py',
                     ROOT/'tools/batched_transport_newton_recovery_2025.py',
                     ROOT/'tools/monthly_lp_spline_inputs_2025.py',
                     ROOT/'tools/hour_table_conditioner_2025.py',
                     ROOT/'tools/run_supply_knots_lp_2025.py',SOLAR):
            sources[str(path.relative_to(ROOT))]=digest(path)
        if (OUT/'sources.json').exists():
            if json.loads((OUT/'sources.json').read_text())!=sources:
                raise ValueError('Changed source during saved monthly fits')
        else:atomic_json(OUT/'sources.json',sources)
        if not (OUT/'pilot.json').exists():
            atomic_json(OUT/'pilot.json',shared.pilot_gradient(state[0],state[1],market))

        def worker(months):
            for month in months:
                try:shared.month_fit(base,state,market,month)
                except Exception:
                    atomic_json(OUT/f'failure-month-{month:02d}.json',
                        dict(month=month,traceback=traceback.format_exc()))
                    raise

        context=multiprocessing.get_context('fork')
        workers=[context.Process(target=worker,args=(months,))
                 for months in (range(1,13,2),range(2,13,2))]
        for process in workers:process.start()
        for process in workers:process.join()
        if any(process.exitcode!=0 for process in workers):
            raise RuntimeError('Direct batched monthly fit failed; inspect month receipt')
        if any(digest(ROOT/path)!=sha for path,sha in sources.items()):
            raise ValueError('Changed source during fit')
        atomic_json(OUT/'complete.json',dict(status='twelve_direct_batched_fits_complete',
            months=list(range(1,13)),updates_per_month=UPDATES,rate=RATE,
            fast_network='independent corridor transport',annual_physical_lp=False,
            source_sha256=digest(OUT/'sources.json'),
            caveat='Within-month in-sample fit; no forward-month or physical LP evaluation'))


if __name__=='__main__':
    try:main()
    except Exception:
        OUT.mkdir(exist_ok=True)
        atomic_json(OUT/'failure.json',dict(traceback=traceback.format_exc()))
        raise
