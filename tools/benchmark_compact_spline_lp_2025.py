"""Full Jan/Feb like-for-like LP timing after the gradient test is audited."""
import json
from pathlib import Path
import time
import numpy as np
from forward_hourly_splines_2025 import clear_lp as original,month_hours,polynomials,clock_slots,interval_bids
from compact_spline_lp_2025 import clear_lp as compact
from supply_knot_network_2025 import load,generation
from spline_europe_2025 import ZERO_TECH
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from run_differentiable_spline_2025 import atomic_json

OUT=ROOT/'data/bidding-zone-network-2025/spline-performance-jan-feb-v1'


def run():
    # Wait only for the existing one-off audit, never start another fit/audit.
    while not (OUT/'audit.json').exists():
        if (OUT/'failure.json').exists():raise ValueError('Upstream test failed')
        pid=json.loads((OUT/'execution.json').read_text())['pid']
        try:state=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0]
        except FileNotFoundError:state='X'
        if state in ['Z','X']:raise ValueError('Upstream stopped without audit')
        time.sleep(5)
    if json.loads((OUT/'audit.json').read_text())['status']!='passed':raise ValueError('Upstream audit required')
    summary=json.loads((OUT/'summary.json').read_text())
    selected=summary['best_iteration'];stage=OUT/f'month-01/iteration-{selected:03d}'
    s,d,A,emergency,capacity=load()
    theta=np.load(stage/'parameters.npy')
    with np.load(stage/'frozen-profile.npz') as z:profile=z['coefficients']
    zero=np.array([g['technology'] in ZERO_TECH for g in s['groups']])
    rows=[]
    for month in [1,2]:
        hours=month_hours(month)
        curves=polynomials(theta,zero) if month==1 else profile[clock_slots(s['groups'],hours),np.arange(len(zero))]
        bids=interval_bids(curves)
        if month==1:
            # Exclude one-off imports/initialization from both timed passes.
            original(s,d,A,emergency,hours[:1],bids[:1])
            compact(s,d,A,emergency,hours[:1],bids[:1])
        began=time.perf_counter();old,oldcert=original(s,d,A,emergency,hours,bids);old_seconds=time.perf_counter()-began
        began=time.perf_counter();new,newinfo=compact(s,d,A,emergency,hours,bids);new_seconds=time.perf_counter()-began
        price_difference=float(abs(old['row_duals'][:,:s['nz']]-new['row_duals'][:,:s['nz']]).max())
        objective_difference=float(abs(old['objectives']-new['objectives']).max())
        if objective_difference>=.05:raise ValueError('Compacted LP objective mismatch')
        oldgen=generation(s,d,capacity,old['quantities'],hours)
        newgen=generation(s,d,capacity,new['quantities'],hours)
        oldmetric,_=metric(s,d,old['row_duals'][:,:s['nz']],oldgen,hours,month)
        newmetric,_=metric(s,d,new['row_duals'][:,:s['nz']],newgen,hours,month)
        witness=OUT/f'compact-month-{month:02d}.npz'
        np.savez_compressed(witness,**new,generation=newgen)
        row=dict(month=month,hours=len(hours),original_seconds=old_seconds,compact_seconds=new_seconds,speedup=old_seconds/new_seconds,
            max_price_difference_eur_mwh=price_difference,max_objective_difference_eur=objective_difference,
            max_curve_quantity_difference_mw=float(abs(old['quantities']-new['quantities']).max()),
            original_metrics=oldmetric,compact_metrics=newmetric,original_certificate=oldcert,compact_info=newinfo,witness_sha256=digest(witness))
        rows.append(row);print(json.dumps(row),flush=True)
    sources=[Path(__file__),ROOT/'tools/compact_spline_lp_2025.py',ROOT/'tools/test_compact_spline_lp_2025.py',stage/'parameters.npy',stage/'frozen-profile.npz',OUT/'audit.json']
    atomic_json(OUT/'compact-lp-benchmark.json',dict(status='passed_original_equations',selected_iteration=selected,months=rows,sources={str(p.relative_to(ROOT)):digest(p) for p in sources},note='Identical zero-bid tranche collapse; unchanged feasible projection/objective, generation allocations can be nonunique. No annual timing extrapolated.'))


if __name__=='__main__':run()
