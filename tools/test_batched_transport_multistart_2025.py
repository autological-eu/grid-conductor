"""Parallel ten-update bid-curve starts on the saved difficult 2025 months."""
import fcntl
import json
import multiprocessing
import traceback
from pathlib import Path

import numpy as np

import fit_monthly_fast_splines_2025 as shared
from fit_batched_transport_all_months_2025 import direct_market
from monthly_lp_spline_inputs_2025 import aligned, SOLAR
from run_differentiable_spline_2025 import atomic_json
from sigmoid_month_pairs_2025 import ROOT, digest


OUT=ROOT/'data/bidding-zone-network-2025/batched-transport-multistart-10-v1'
MARKET_FACTORY=direct_market
EXTRA_SOURCES=()
MONTHS=(1,4)
STARTS=('neutral','flatter','steeper','higher_midpoint')
UPDATES=10
RATE=.5


def starting_weights(market,name):
    weights=shared.initial_weights(market.ng)
    if name=='neutral':return weights
    if name in ('flatter','steeper'):
        factor=.75 if name=='flatter' else 1.5
        raw=weights[:,0,1:]
        increments=.001+20*np.logaddexp(0,raw)
        changed=np.maximum(.00100001,increments*factor)
        weights[:,:24,1:]=np.log(np.expm1((changed-.001)/20))[:,None,:]
    elif name=='higher_midpoint':
        weights[:,:24,0]=4*np.arctanh(10/80)
    else:raise ValueError('Unknown declared start')
    # Zero-bid technologies ignore their economic parameters in the market.
    weights[market.zero]=shared.initial_weights(market.ng)[market.zero]
    return weights


def worker(job,base,state,market):
    month,name=job
    folder=OUT/f'{name}-month-{month:02d}'
    folder.mkdir(parents=True,exist_ok=True)
    shared.OUT=folder
    shared.UPDATES=UPDATES
    shared.RATE=RATE
    shared.FACTORS=(1.,)
    try:
        initial=starting_weights(market,name)
        shared.month_fit(base,state,market,month,initial_override=initial)
        receipt=json.loads((folder/f'month-{month:02d}/complete.json').read_text())
        atomic_json(folder/'complete.json',dict(month=month,start=name,
            initial_sha256=digest(folder/f'month-{month:02d}/state-000.npz'),
            **receipt))
    except Exception:
        folder.mkdir(parents=True,exist_ok=True)
        atomic_json(folder/'failure.json',dict(month=month,start=name,
            traceback=traceback.format_exc()))


def main():
    OUT.mkdir(exist_ok=True)
    with (OUT/'job.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        base,state,source,_,_=aligned()
        market=MARKET_FACTORY(source)
        sources=base.provenance()
        for path in (Path(__file__),ROOT/'tools/fit_monthly_fast_splines_2025.py',
                     ROOT/'tools/fit_batched_transport_all_months_2025.py',
                     ROOT/'tools/batched_transport_dispatch_2025.py',
                     ROOT/'tools/batched_transport_newton_recovery_2025.py',
                     ROOT/'tools/monthly_lp_spline_inputs_2025.py',
                     ROOT/'tools/hour_table_conditioner_2025.py',SOLAR,*EXTRA_SOURCES):
            sources[str(path.relative_to(ROOT))]=digest(path)
        if (OUT/'sources.json').exists():
            if json.loads((OUT/'sources.json').read_text())!=sources:
                raise ValueError('Changed experiment source')
        else:atomic_json(OUT/'sources.json',sources)
        jobs=[(month,name) for month in MONTHS for name in STARTS]
        context=multiprocessing.get_context('fork')
        for index in range(0,len(jobs),3):
            children=[context.Process(target=worker,args=(job,base,state,market))
                      for job in jobs[index:index+3]]
            for child in children:child.start()
            for child in children:child.join()
            if any(child.exitcode!=0 for child in children):
                raise RuntimeError('Unexpected worker termination; inspect receipts')
        rows=[]
        for month,name in jobs:
            folder=OUT/f'{name}-month-{month:02d}'
            row=dict(month=month,start=name,status='complete' if (folder/'complete.json').exists() else 'failed')
            if row['status']=='complete':
                history=json.loads((folder/f'month-{month:02d}/history.json').read_text())
                row.update(initial_price_mae=history[0]['price_mae'],
                    final_price_mae=history[-1]['price_mae'],
                    initial_generation_mae_twh=history[0]['generation_mae_twh'],
                    final_generation_mae_twh=history[-1]['generation_mae_twh'],
                    final_joint_data_loss=history[-1]['price_loss']+history[-1]['generation_loss'],
                    seconds=sum(x['seconds'] for x in history),
                    excluded_gradient_directions=sum(x.get('excluded_gradient_directions',0) for x in history),
                    fallback_hours=sum(x.get('price_root_recovery',{}).get('fallback_hours',0) for x in history),
                    max_certified_root_spread_eur_mwh=max(
                        (x.get('price_root_recovery',{}).get('max_price_spread_eur_mwh',0) for x in history),default=0))
            rows.append(row)
        selected={}
        for month in MONTHS:
            eligible=[row for row in rows if row['month']==month and row['status']=='complete']
            selected[str(month)]=min(eligible,key=lambda row:row['final_joint_data_loss'])['start'] if eligible else None
        atomic_json(OUT/'summary.json',dict(status='multistart_pilot_complete',
            months=list(MONTHS),starts=list(STARTS),updates=UPDATES,rate=RATE,
            network='LP-free independent corridors',cases=rows,
            selected_by_in_sample_price_plus_generation_loss=selected,
            source_sha256=digest(OUT/'sources.json'),
            caveat='Two-month in-sample numerical pilot, not annual fit or forward validation'))
        print(json.dumps(rows,indent=2),flush=True)


if __name__=='__main__':main()
