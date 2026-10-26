"""Independently score final ten-step curve/price multistart witnesses."""
import json
from pathlib import Path

import numpy as np

from monthly_lp_spline_inputs_2025 import aligned
from run_differentiable_spline_2025 import atomic_json
from sigmoid_month_pairs_2025 import ROOT,digest,metric
from supply_knot_network_2025 import generation


OUT=ROOT/'data/bidding-zone-network-2025/curve-price-multistart-10-v1'
STARTS=('neutral','flatter','steeper','higher_midpoint')


def run():
    sources=json.loads((OUT/'sources.json').read_text())
    changed=[path for path,sha in sources.items() if digest(ROOT/path)!=sha]
    if changed:raise ValueError('Fitting sources changed: '+str(changed[:4]))
    _,state,_,_,_=aligned()
    s,d,_,_,sourcecap=state
    rows=[]
    for month in (1,4):
        for name in STARTS:
            folder=OUT/f'{name}-month-{month:02d}'/f'month-{month:02d}'
            receipt=json.loads((folder/'complete.json').read_text())
            history=json.loads((folder/'history.json').read_text())
            if len(history)!=11 or [h['update'] for h in history]!=list(range(11)):
                raise ValueError('Incomplete ten-update fit '+str(folder))
            final=folder/'state-010.npz'
            if digest(final)!=receipt['final_state_sha256']:
                raise ValueError('Final state hash mismatch '+str(folder))
            with np.load(final) as z:
                hours=z['hours'];prices=z['prices'];q=z['quantities_gw']
            generated=generation(s,d,sourcecap,q*1000,hours)
            measured,_=metric(s,d,prices,generated,hours,month)
            saved=history[-1]
            if abs(measured['price_mae']-saved['price_mae'])>1e-8 or abs(
                measured['generation_mae_twh']-saved['generation_mae_twh'])>1e-8:
                raise ValueError('Independent price/generation score mismatch '+str(folder))
            for endpoint in (history[0],history[-1]):
                certificate=endpoint['certificate']
                if certificate['balance_mw']>=1e-4 or certificate['emergency_mwh']!=0:
                    raise ValueError('Fast endpoint feasibility failed '+str(folder))
            rows.append(dict(month=month,start=name,initial_price_mae=history[0]['price_mae'],
                final_price_mae=saved['price_mae'],
                final_generation_mae_twh=saved['generation_mae_twh'],
                final_joint_data_loss=saved['price_loss']+saved['generation_loss'],
                solve_seconds=sum(h['seconds'] for h in history),
                fallback_hours=sum(h.get('price_root_recovery',{}).get('fallback_hours',0) for h in history),
                max_certified_root_spread_eur_mwh=max(
                    h.get('price_root_recovery',{}).get('max_price_spread_eur_mwh',0) for h in history),
                excluded_gradient_directions=sum(h.get('excluded_gradient_directions',0) for h in history),
                final_state_sha256=digest(final)))
    selected={str(month):min((row for row in rows if row['month']==month),
        key=lambda row:row['final_joint_data_loss'])['start'] for month in (1,4)}
    atomic_json(OUT/'independent-audit.json',dict(status='complete',cases=rows,
        selected_by_in_sample_joint_data_loss=selected,
        source_sha256=digest(OUT/'sources.json'),
        caveat='Numerical Jan/Apr in-sample pilot; roots chosen without observed-price labels'))
    print(json.dumps(dict(selected=selected,cases=rows),indent=2))


if __name__=='__main__':run()
