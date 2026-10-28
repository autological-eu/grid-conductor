"""Replay saved bids and independently recalculate 2025 joint-market metrics."""
import hashlib
import json

import numpy as np

from batched_transport_newton_recovery_2025 import RecoveredTransportMarket
from flow_adjusted_zonal_clearing_2025 import DEST,observed_exchanges
from fit_mixed_flow_monthly_bids_2025 import solve_with_neighbor_starts
from monthly_diurnal_splines_2025 import labels
from run_batched_transport_2025 import setup

OUT=DEST/'mixed-flow-monthly-v1-u20-r0.05'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def array_digest(array):return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def replay():
    state,base,_,_=setup();s,d,*_=state
    market=RecoveredTransportMarket(base.zones,base.groups,base.lower,base.upper,
        base.edges,base.capacity,base.source,base.load,cost=base.cost,
        thermal_tau=base.thermal_tau,renewable_tau=base.renewable_tau,flow_tau=base.flow_tau)
    _,covered,_,observed_flow=observed_exchanges(s['zones'],market.edges,return_edges=True)
    missing=~covered
    ci=np.array([g['country_id'] for g in s['groups']]);ti=np.array([s['technologies'].index(g['technology']) for g in s['groups']])
    stamps=np.arange('2025-01-01','2026-01-01',dtype='datetime64[h]')
    edge_metadata=dict(schema='mixed-flow-monthly-v1',
        direction='Positive flows_gw run from from_zone to to_zone; negative means reverse.',
        net_import='inferred_net_import_gw is positive for net imports into zone.',
        flow_kind='Inferred by bounded independent-corridor transport clearing; not observed ENTSO-E exchange.',
        observation_kind='observed_a09_gw is ENTSO-E day-ahead commercial exchange, NaN when unavailable; observed_within_model_bounds identifies comparable cells.',
        time='hour_start_utc is int64 hours since 1970-01-01 00:00 UTC; power is hourly mean GW.',
        from_zone=[s['zones'][i] for i,j in market.edges],
        to_zone=[s['zones'][j] for i,j in market.edges],
        zones=s['zones'],
        corridor_count=len(market.edges),
        market_parameters=dict(transport_cost=float(market.cost),thermal_tau=float(market.thermal_tau),
                               renewable_tau=float(market.renewable_tau),flow_tau=float(market.flow_tau)),
        network_edges_sha256=array_digest(market.edges),
        network_lower_sha256=array_digest(market.lower),
        network_upper_sha256=array_digest(market.upper),
        source_witness_sha256=digest(DEST/'witness.npz'))
    (OUT/'flow-metadata.json').write_text(json.dumps(edge_metadata,indent=2)+'\n')
    records=[]
    for month in range(1,13):
        folder=OUT/f'month-{month:02d}'
        summary=json.loads((folder/'summary.json').read_text())
        hours=np.flatnonzero(stamps.astype('datetime64[M]')==np.datetime64(f'2025-{month:02d}'))
        with np.load(folder/'curves.npz') as z:weights=z['weights']
        if weights.shape!=(24,market.ng,6) or not np.isfinite(weights).all():raise ValueError('Bad curve shape')
        clock=labels(s['groups'],hours);theta=weights[clock,np.arange(market.ng)]
        previous_modeled_prices=None
        if (folder/'resume.npz').exists():
            with np.load(folder/'resume.npz') as checkpoint:
                previous_modeled_prices=checkpoint['prior'] if bool(checkpoint['has_prior']) else None
        result=solve_with_neighbor_starts(market,theta,hours,p0=previous_modeled_prices)
        offers=market.offers(theta,hours)
        residual,_,q,f=market.evaluate(result['prices'],offers)
        if abs(residual).max()>1e-7 or np.any(q<-1e-7) or np.any(q-offers['capacity']>1e-7):
            raise ValueError('Primal replay failed')
        if np.any(f<market.lower[hours]-1e-7) or np.any(f>market.upper[hours]+1e-7):
            raise ValueError('Flow bound replay failed')
        if abs((f@market.M).sum(axis=1)).max()>1e-10:
            raise ValueError('Inferred net imports do not conserve power')
        observed_price=d['observed_prices'][hours];pm=np.isfinite(observed_price)
        diff=abs(result['prices'][pm]-observed_price[pm]);mm=pm&missing[hours]
        flow_observed=observed_flow[hours]
        flow_known=np.isfinite(flow_observed)
        flow_compatible=flow_known&(flow_observed>=market.lower[hours]-1e-8)&(flow_observed<=market.upper[hours]+1e-8)
        np.savez_compressed(folder/'inferred-flows.npz',
            hour_start_utc=stamps[hours].astype('datetime64[h]').astype('int64'),
            flows_gw=f,inferred_net_import_gw=f@market.M,
            lower_gw=market.lower[hours],upper_gw=market.upper[hours],
            observed_a09_gw=flow_observed,observed_within_model_bounds=flow_compatible)
        modeled=d['fixed_generation'][hours].copy()/1000
        for g in range(market.ng):modeled[:,ci[g],ti[g]]+=q[:,g]
        observed=d['observed_generation'][hours]/1000;gm=np.isfinite(observed)
        # Same source-covered category denominator as training, computed anew.
        mt=np.where(gm,modeled,0);ot=np.where(gm,observed,0)
        mt_sum=mt.sum(axis=2,keepdims=True);ot_sum=ot.sum(axis=2,keepdims=True)
        share_mask=gm&(mt_sum>1e-6)&(ot_sum>1e-6)
        ms=np.divide(mt,mt_sum,out=np.zeros_like(mt),where=mt_sum>1e-6)
        os=np.divide(ot,ot_sum,out=np.zeros_like(ot),where=ot_sum>1e-6)
        row=dict(month=month,price_cells=int(pm.sum()),price_mae=float(diff.mean()),
            missing_flow_price_cells=int(mm.sum()),
            missing_flow_price_mae=float(abs(result['prices'][mm]-observed_price[mm]).mean()),
            observed_flow_cells=int(flow_compatible.sum()),
            observed_flow_mae_gw=float(abs(f[flow_compatible]-flow_observed[flow_compatible]).mean()),
            incompatible_observed_flow_cells=int((flow_known&~flow_compatible).sum()),
            generation_cells=int(gm.sum()),generation_mae_gw=float(abs(modeled[gm]-observed[gm]).mean()),
            mix_cells=int(share_mask.sum()),mix_share_mae=float(abs(ms[share_mask]-os[share_mask]).mean()),
            max_balance_mw=float(abs(residual).max()*1000),
            replay_start='previous modeled update' if previous_modeled_prices is not None else 'model-only copperplate',
            curves_sha256=digest(folder/'curves.npz'),
            inferred_flows_sha256=digest(folder/'inferred-flows.npz'))
        if month==8:
            k=int(np.flatnonzero(hours==5447)[0])
            cold=solve_with_neighbor_starts(market,theta[k:k+1],hours[k:k+1])
            warm=solve_with_neighbor_starts(market,theta[k:k+1],hours[k:k+1],
                p0=previous_modeled_prices[k:k+1])
            max_flow=float(abs(cold['flows_gw']-warm['flows_gw']).max())
            max_generation=float(abs(cold['quantities_gw']-warm['quantities_gw']).max())
            if max(max_flow,max_generation)>1e-8:raise ValueError('Ambiguous root changes dispatch or flow')
            affected=['EE','LV','LT']
            row['root_start_price_ambiguity']=dict(hour_utc='2025-08-15T23:00:00Z',
                zones=affected,cold_prices={z:float(cold['prices'][0,market.zones.index(z)]) for z in affected},
                previous_model_prices={z:float(warm['prices'][0,market.zones.index(z)]) for z in affected},
                max_price_difference_eur_mwh=float(abs(cold['prices']-warm['prices']).max()),
                max_flow_difference_gw=max_flow,max_generation_difference_gw=max_generation,
                cold_balance_mw=cold['certificate']['balance_mw'],
                warm_balance_mw=warm['certificate']['balance_mw'])
        for key in ('price_cells','price_mae','missing_flow_price_cells','missing_flow_price_mae',
                    'generation_cells','generation_mae_gw','mix_cells','mix_share_mae',
                    'observed_flow_cells','observed_flow_mae_gw'):
            if not np.isclose(row[key],summary['final'][key],atol=1e-6,rtol=1e-8):
                raise ValueError(f'{month} {key} metric replay mismatch')
        records.append(row);print('AUDIT',month,row['price_mae'],row['missing_flow_price_mae'],flush=True)
    counts=np.array([r['price_cells'] for r in records]);mc=np.array([r['missing_flow_price_cells'] for r in records])
    gc=np.array([r['generation_cells'] for r in records]);sc=np.array([r['mix_cells'] for r in records])
    fc=np.array([r['observed_flow_cells'] for r in records])
    audit=dict(status='replayed',months=len(records),records=records,
        price_cells=int(counts.sum()),price_mae=float(np.average([r['price_mae'] for r in records],weights=counts)),
        missing_flow_price_cells=int(mc.sum()),missing_flow_price_mae=float(np.average([r['missing_flow_price_mae'] for r in records],weights=mc)),
        generation_cells=int(gc.sum()),generation_mae_gw=float(np.average([r['generation_mae_gw'] for r in records],weights=gc)),
        mix_cells=int(sc.sum()),mix_share_mae=float(np.average([r['mix_share_mae'] for r in records],weights=sc)),
        observed_flow_cells=int(fc.sum()),
        observed_flow_mae_gw=float(np.average([r['observed_flow_mae_gw'] for r in records],weights=fc)),
        incompatible_observed_flow_cells=sum(r['incompatible_observed_flow_cells'] for r in records),
        source_witness_sha256=digest(DEST/'witness.npz'),
        caveat='In-sample reconstructed prices with model-inferred flows; not a physical LP or investment scenario certificate.')
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    return audit


if __name__=='__main__':replay()
