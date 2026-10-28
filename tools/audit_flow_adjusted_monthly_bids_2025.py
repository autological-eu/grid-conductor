"""Independent replay of saved monthly bids on unchanged source masks."""
import hashlib
import json
from pathlib import Path

import numpy as np

from flow_adjusted_zonal_clearing_2025 import DEST,clear_independent
from monthly_diurnal_splines_2025 import labels
from run_batched_transport_2025 import setup


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(root):
    state,market,_,_=setup();s,d,*_=state
    with np.load(DEST/'witness.npz') as source:
        net=source['net_import_gw'];covered=source['covered']
    records=[];zone_error=np.zeros(market.nz);zone_count=np.zeros(market.nz,dtype=int)
    stamps=np.arange('2025-01-01','2026-01-01',dtype='datetime64[h]')
    ci=np.array([g['country_id'] for g in s['groups']])
    ti=np.array([s['technologies'].index(g['technology']) for g in s['groups']])
    countries=len(s['countries'])
    country_zones=[sorted({g['zone_id'] for g in s['groups'] if g['country_id']==c}) for c in range(countries)]
    for month in range(1,13):
        folder=root/f'month-{month:02d}'
        summary=json.loads((folder/'summary.json').read_text())
        hours=np.flatnonzero(stamps.astype('datetime64[M]')==np.datetime64(f'2025-{month:02d}'))
        with np.load(folder/'curves.npz') as z:weights=z['weights']
        if weights.shape!=(24,market.ng,6) or not np.isfinite(weights).all():raise ValueError('Invalid bid array')
        clock=labels(s['groups'],hours)
        theta=weights[clock,np.arange(market.ng)]
        offers=market.offers(theta,hours)
        target=market.load[hours]-net[hours]
        cap=offers['capacity']@market.Z
        valid=covered[hours]&(target>=0)&(target<=cap)&np.isfinite(d['observed_prices'][hours])
        # Replay with the original vectorized bisection, independently of the
        # compiled price-root implementation used during fitting.
        price,q,cleared,residual=clear_independent(market,theta,net,covered,hours)
        mask=valid&cleared;obs=d['observed_prices'][hours]
        zone_error+=np.where(mask,abs(price-np.where(np.isfinite(obs),obs,0)),0).sum(axis=0)
        zone_count+=mask.sum(axis=0)
        country_ok=np.column_stack([valid[:,zs].all(axis=1) if zs else np.zeros(len(hours),bool) for zs in country_zones])
        sourcegen=d['observed_generation'][hours]/1000
        genmask=np.isfinite(sourcegen)&country_ok[:,:,None]
        modeled=d['fixed_generation'][hours].copy()/1000
        for g in range(market.ng):modeled[:,ci[g],ti[g]]+=q[:,g]
        result=dict(month=month,matched_price_cells=int(mask.sum()),
            price_mae=float(abs(price[mask]-obs[mask]).mean()),
            generation_cells=int(genmask.sum()),
            generation_mae_gw=float(abs(modeled[genmask]-sourcegen[genmask]).mean()),
            max_cleared_balance_mw=float(abs(residual[mask]).max()*1000))
        saved=summary['fitted_cleared']
        for field,value in result.items():
            if field=='month':continue
            if not np.isclose(value,saved[field],atol=1e-7,rtol=1e-8):
                raise ValueError(f'Month {month} {field} changed: {value} != {saved[field]}')
        result['curves_sha256']=digest(folder/'curves.npz');records.append(result)
        print('AUDIT',month,result['price_mae'],flush=True)
    per_zone=[dict(zone=z,matched_hours=int(zone_count[j]),
                   fitted_price_mae_eur_mwh=float(zone_error[j]/zone_count[j]) if zone_count[j] else None)
              for j,z in enumerate(s['zones'])]
    audit=dict(status='replayed',months=len(records),records=records,per_zone=per_zone,
        source_witness_sha256=digest(DEST/'witness.npz'),
        caveat='In-sample observed-exchange conditional fit; not forward or scenario validation.')
    (root/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    return audit


if __name__=='__main__':
    audit(DEST/'monthly-fit-v1-u100-r0.1')
