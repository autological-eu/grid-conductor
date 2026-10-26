"""One annual joint LP pass after twelve independently fitted fast-market months."""
import fcntl
import json
import resource
from pathlib import Path

import numpy as np

from monthly_lp_spline_inputs_2025 import aligned
from monthly_fast_lp_costs_2025 import transferred_costs
from fit_monthly_fast_splines_2025 import OUT as FIT
from joint_network_clear_2025 import clear_or_reject
from generation_mix_2025 import ROOT,digest
from solar_country_fit_2025 import write

OUT=ROOT/'data/bidding-zone-network-2025/monthly-fast-lp-v2'


def run():
    OUT.mkdir(exist_ok=True)
    lock=(OUT/'job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (OUT/'annual.npz').exists() or (OUT/'failure.json').exists():
        raise ValueError('Inspect prior annual witness before any restart')
    complete=json.loads((FIT/'complete.json').read_text())
    if complete['status']!='twelve_monthly_fits_completed':raise ValueError('Monthly fits incomplete')
    base,state,market,_,_=aligned()
    schema,data,A,emergency,sourcecap=state
    from solar_anchor_bids_2025 import model
    parameters,accepted,lp=model()
    costs,transfer=transferred_costs(schema,data,market,accepted,lp,FIT)
    sources=json.loads((FIT/'sources.json').read_text())
    for relative,sha in sources.items():
        if digest(ROOT/relative)!=sha:raise ValueError('Changed fitted source: '+relative)
    for month in range(1,13):
        path=FIT/f'month-{month:02d}/state-100.npz'
        sources[str(path.relative_to(ROOT))]=digest(path)
    for path in [Path(__file__),ROOT/'tools/monthly_fast_lp_costs_2025.py']:
        sources[str(path.relative_to(ROOT))]=digest(path)
    write(OUT/'inputs.json',dict(status='frozen_fast_fits_and_original_799_column_lp',
        sources=sources,transfer=transfer,offer_columns=lp['ng'],
        all_hours=8760,no_forward_validation=True))
    # Exactly one annual physical clear, with its native 799 offer columns.
    x,y,obj,info=clear_or_reject(lp|dict(cost=costs),accepted['flow'],costs,OUT/'annual.npz')
    if x is None:
        write(OUT/'failure.json',dict(status='annual_lp_failed_original_gates',market=info))
        return
    emergency_mwh=float(np.maximum(x[:,:lp['ng']][:,accepted['emergency_mask']],0).sum())
    if emergency_mwh>1e-6:
        write(OUT/'failure.json',dict(status='no_emergency_gate_failed',market=info,
            emergency_mwh=emergency_mwh,witness_sha256=digest(OUT/'annual.npz')))
        return
    with np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz') as z:observed=z['prices']
    known=np.isfinite(observed).all(axis=0)
    if known.sum()!=41:raise ValueError('Changed hourly price coverage')
    price_mae=float(abs(y[:,:lp['nz']][:,known]-observed[:,known]).mean())
    write(OUT/'summary.json',dict(status='annual_lp_completed_pending_independent_audit',
        market=info,price_mae=price_mae,emergency_mwh=emergency_mwh,
        witness_sha256=digest(OUT/'annual.npz'),inputs_sha256=digest(OUT/'inputs.json'),
        limitations=['Same-year monthly fitting is in-sample reconstruction.',
            'Original LP offers sample learned six-node curves at existing tranche midpoints.',
            'Mixed renewable and geothermal bids retain the accepted LP values.']))
    print('ANNUAL LP',price_mae,info['clearing_seconds'],flush=True)


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
    run()
