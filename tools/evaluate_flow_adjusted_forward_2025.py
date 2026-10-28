"""Apply each fitted month's local-hour bids to the next month without refit."""
import json
import numpy as np

from fast_independent_price_root_2025 import solve
from flow_adjusted_zonal_clearing_2025 import DEST
from monthly_diurnal_splines_2025 import labels
from run_batched_transport_2025 import setup

ROOT=DEST/'monthly-fit-v1-u100-r0.1'


def main():
    state,market,_,_=setup();s,d,*_=state
    with np.load(DEST/'witness.npz') as z:net=z['net_import_gw'];covered=z['covered']
    stamps=np.arange('2025-01-01','2026-01-01',dtype='datetime64[h]')
    ci=np.array([g['country_id'] for g in s['groups']]);ti=np.array([s['technologies'].index(g['technology']) for g in s['groups']])
    country_zones=[sorted({g['zone_id'] for g in s['groups'] if g['country_id']==c}) for c in range(len(s['countries']))]
    rows=[]
    for month in range(2,13):
        hours=np.flatnonzero(stamps.astype('datetime64[M]')==np.datetime64(f'2025-{month:02d}'))
        with np.load(ROOT/f'month-{month-1:02d}/curves.npz') as z:weights=z['weights']
        clock=labels(s['groups'],hours);theta=weights[clock,np.arange(market.ng)]
        offers=market.offers(theta,hours)
        target=market.load[hours]-net[hours]
        valid=covered[hours]&(target>=0)&(target<=offers['capacity']@market.Z)&np.isfinite(d['observed_prices'][hours])
        price,q,cleared,residual=solve(market,offers,target,valid);mask=valid&cleared
        observed=d['observed_prices'][hours]
        country_ok=np.column_stack([valid[:,zs].all(axis=1) if zs else np.zeros(len(hours),bool) for zs in country_zones])
        source=d['observed_generation'][hours]/1000;genmask=np.isfinite(source)&country_ok[:,:,None]
        modeled=d['fixed_generation'][hours].copy()/1000
        for g in range(market.ng):modeled[:,ci[g],ti[g]]+=q[:,g]
        own=json.loads((ROOT/f'month-{month:02d}/summary.json').read_text())
        row=dict(train_month=month-1,test_month=month,matched_price_cells=int(mask.sum()),
                 price_mae=float(abs(price[mask]-observed[mask]).mean()),
                 generation_cells=int(genmask.sum()),generation_mae_gw=float(abs(modeled[genmask]-source[genmask]).mean()),
                 within_month_price_mae=own['fitted_cleared']['price_mae'],
                 neutral_price_mae=own['initial_cleared']['price_mae'],
                 max_balance_mw=float(abs(residual[mask]).max()*1000))
        rows.append(row);print('FORWARD',month,row['price_mae'],flush=True)
    weights=np.array([r['matched_price_cells'] for r in rows])
    gweights=np.array([r['generation_cells'] for r in rows])
    result=dict(status='same_year_next_month_transfer',rows=rows,
                price_mae=float(np.average([r['price_mae'] for r in rows],weights=weights)),
                within_month_price_mae=float(np.average([r['within_month_price_mae'] for r in rows],weights=weights)),
                neutral_price_mae=float(np.average([r['neutral_price_mae'] for r in rows],weights=weights)),
                generation_mae_gw=float(np.average([r['generation_mae_gw'] for r in rows],weights=gweights)),
                matched_price_cells=int(weights.sum()))
    (ROOT/'forward.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))


if __name__=='__main__':main()
