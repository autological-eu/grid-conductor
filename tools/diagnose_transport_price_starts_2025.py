"""Test fixed-bid price initializations on archived stalled transport hours."""
import json
import re
import time
from itertools import combinations
from pathlib import Path

import numpy as np

from fit_batched_transport_all_months_2025 import direct_market
from forward_hourly_splines_2025 import month_hours
from hour_table_conditioner_2025 import feature_rows
from monthly_lp_spline_inputs_2025 import aligned
from run_differentiable_spline_2025 import atomic_json
from sigmoid_month_pairs_2025 import ROOT,digest


OUT=ROOT/'data/bidding-zone-network-2025/transport-price-starts-v1'
ROOTS=(ROOT/'data/bidding-zone-network-2025/batched-transport-monthly-100-v2',
       ROOT/'data/bidding-zone-network-2025/batched-transport-multistart-10-v1')


def cases():
    for root in ROOTS:
        for receipt in sorted(root.glob('**/rejected-update-*.json')):
            folder=receipt.parent
            month=int(folder.name[-2:])
            rejected=json.loads(receipt.read_text())
            hours=sorted(set(int(v) for entry in rejected for v in
                re.findall(r'\d+',entry['reason'].split('hours=')[-1])))
            if 'hours=' not in rejected[0]['reason']:
                raise ValueError('Cannot identify stalled hour in '+str(receipt))
            for hour in hours:
                yield root,folder,receipt,month,hour


def probe():
    OUT.mkdir(exist_ok=True)
    _,state,source,_,_=aligned();s,d,*_=state
    market=direct_market(source)
    rows=[];source_hashes={}
    for root,folder,receipt,month,hour in cases():
        resume=folder/'resume.npz'
        for file in (receipt,resume):source_hashes[str(file.relative_to(ROOT))]=digest(file)
        with np.load(resume) as saved:
            weights=saved['weights'].copy()
            previous_prices=saved['prices'].copy()
            step=int(saved['step'])
        index=int(np.flatnonzero(month_hours(month)==hour)[0])
        X,_=feature_rows(s['groups'],d,np.array([hour]),market.reference)
        theta=np.einsum('tgf,gfk->tgk',X,weights)
        offers=market.offers(theta,np.array([hour]))
        cold=market.initial_prices(offers)
        starts=dict(cold=cold,flat_0=np.zeros_like(cold),
            flat_50=np.full_like(cold,50),flat_100=np.full_like(cold,100),
            cold_minus_25=cold-25,cold_plus_25=cold+25,
            coordinate_cold=market.coordinate(cold,offers))
        if step:starts['previous_hour_price']=previous_prices[index:index+1]
        label=str(folder.relative_to(ROOT))
        case=dict(case=label,hour=hour,month=month,failed_update=step,
                  sources=dict(rejected_sha256=digest(receipt),resume_sha256=digest(resume)),
                  starts=[])
        valid=[]
        for name,p0 in starts.items():
            began=time.perf_counter()
            try:
                result=market.solve(theta,np.array([hour]),p0=p0,tolerance=1e-9)
                residual=market.evaluate(result['prices'],offers)[0]
                eigen=np.linalg.eigvalsh(result['jacobian'][0])
                row=dict(start=name,status='certified',seconds=time.perf_counter()-began,
                    max_balance_mw=float(abs(residual).max()*1000),
                    max_generation_bound_mw=result['certificate']['generation_bound_mw'],
                    max_flow_bound_mw=result['certificate']['flow_bound_mw'],
                    iterations=int(result['iterations'][0]),
                    unidentified_eigendirections=int((eigen<=np.maximum(1e-12,eigen[-1]*1e-12)).sum()),
                    min_jacobian_eigenvalue=float(eigen[0]),
                    prices_eur_mwh=result['prices'][0].tolist())
                if abs(residual).max()>1e-9:
                    raise ValueError('Uncertified balance')
                valid.append(np.asarray(result['prices'][0]))
            except (RuntimeError,ValueError) as exc:
                row=dict(start=name,status='failed',seconds=time.perf_counter()-began,
                         reason=str(exc))
            case['starts'].append(row)
        pair=[float(abs(a-b).max()) for a,b in combinations(valid,2)]
        case['certified_starts']=len(valid)
        case['max_price_difference_between_certified_roots_eur_mwh']=max(pair,default=0.)
        rows.append(case)
        atomic_json(OUT/'progress.json',dict(cases_completed=len(rows),last_case=label,last_hour=hour))
        print('CASE',label,hour,len(valid),'of',len(starts),'max_price_delta',case['max_price_difference_between_certified_roots_eur_mwh'],flush=True)
    atomic_json(OUT/'results.json',dict(status='complete',cases=rows,
        sources=source_hashes,original_market_tolerance_gw=1e-9,
        note='No observed price used as a numerical starting guess; fixed bids and bounds throughout'))


if __name__=='__main__':probe()
