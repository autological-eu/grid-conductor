"""Evaluate solar-aligned 20-update fitted bids in the original 2025 joint LP."""
import fcntl
import json
import resource
import time
import traceback

import numpy as np

from clear_monthly_fast_lp_2025 import clear_or_reject
from flow_adjusted_zonal_clearing_2025 import DEST
from forward_hourly_splines_2025 import month_hours
from generation_mix_2025 import ROOT,digest
from monthly_fast_lp_costs_2025 import costs_for_hours,offer_groups
from monthly_lp_spline_inputs_2025 import aligned
from nve_hydro_diagnostics import solver

from run_regional_water_candidate_2025 import guarded_hour
from solar_anchor_bids_2025 import model
from solar_country_fit_2025 import write

FIT=DEST/'aligned-mixed-flow-observed-root-v1-u20-r1'
OUT=ROOT/'data/bidding-zone-network-2025/observed-root-fast-joint-lp-v1'
ACTIVE=ROOT/'config/active-research-baseline.json'
ARCHIVED=ROOT/'config/research-baseline-solar-anchor-2025.json'


def inputs():
    audit=json.loads((FIT/'audit.json').read_text())
    if audit['status']!='replayed' or audit['months']!=12:raise ValueError('Incomplete fitted-curve audit')
    sources={}
    for month,row in enumerate(audit['records'],1):
        path=FIT/f'month-{month:02d}/curves.npz'
        if digest(path)!=row['curves_sha256']:raise ValueError('Changed fitted curves')
        sources[str(path.relative_to(ROOT))]=digest(path)
        summary=json.loads((path.parent/'summary.json').read_text())
        if summary['updates']!=20 or summary['month']!=month or summary['rate']!=1.:
            raise ValueError('Different monthly fit protocol')
    current=json.loads(ACTIVE.read_text())
    historical=ARCHIVED if current['model']=='monthly-fitted-bids-v1' else ACTIVE
    for path in [FIT/'audit.json',FIT/'flow-metadata.json']:
        sources[str(path.relative_to(ROOT))]=digest(path)
    # The annual witness was produced against the archived incumbent. Retain
    # its original source key/hash so the sealed audit can be replayed after
    # research-baseline adoption without pretending it used the new pointer.
    sources[str(ACTIVE.relative_to(ROOT))]=digest(historical)
    active=json.loads(historical.read_text())
    if active['model']!='solar-anchor-bids-v1' or active['annual_case']!='resource_full':
        raise ValueError('Accepted baseline pointer changed')
    for relative,sha in active['artifacts'].items():
        if digest(ROOT/relative)!=sha:raise ValueError('Accepted baseline source changed: '+relative)
    return audit,active,sources


def alignment(fit_state,aligned_state,accepted,lp):
    s,d,*_=fit_state;schema,data,*_=aligned_state
    keys=lambda state:[(g['zone'],g['country'],g['technology']) for g in state['groups']]
    if keys(s)!=keys(schema) or s['zones']!=schema['zones']:
        raise ValueError('Fitting and LP group/zone order differ')
    for key in ('source_cost','load','fixed_generation'):
        if not np.array_equal(d[key],data[key]):raise ValueError('Changed fitting input '+key)
    delta=data['capacity']-d['capacity']
    for g,row in enumerate(schema['groups']):
        if row['technology']!='solar' and abs(delta[:,g]).max()>1e-5:
            raise ValueError('Non-solar availability changed')
    np.testing.assert_allclose(data['capacity'].sum(axis=1),
        lp['availability'][:,~accepted['emergency_mask']].sum(axis=1),atol=1e-5,rtol=0)
    return dict(technology='solar only',annual_signed_twh=float(delta.sum()/1e6),
        annual_absolute_twh=float(abs(delta).sum()/1e6),
        max_hourly_zonal_mw=float(abs(delta).max()),
        max_hourly_europe_mw=float(abs(delta.sum(axis=1)).max()),
        changed_solar_cells=int(np.count_nonzero(abs(delta)>1e-5)))


def transferred_costs(schema,data,market,lp,grouped):
    if market.ng!=326 or lp['ng']!=799:raise ValueError('Changed model dimensions')
    costs=lp['cost'].copy();groups=market.ng
    for month in range(1,13):
        hours=month_hours(month)
        with np.load(FIT/f'month-{month:02d}/curves.npz') as z:curves=z['weights']
        if curves.shape!=(24,groups,6) or not np.isfinite(curves).all():
            raise ValueError('Invalid monthly curve array')
        weights=np.zeros((groups,26,6));weights[:,:24]=curves.transpose(1,0,2)
        for start in range(0,len(hours),168):
            h=hours[start:start+168]
            costs[h]=costs_for_hours(schema,data,market,lp,weights,
                                      np.zeros((groups,2)),h,grouped)
    if not np.isfinite(costs).all():raise ValueError('Nonfinite transferred LP bid')
    return costs


def pilot(lp,accepted,costs):
    hours=np.r_[np.arange(0,6),np.arange(2700,2706),
                np.arange(5440,5446),np.arange(8400,8406)]
    local=lp|dict(cost=costs[hours],availability=lp['availability'][hours],
        load=lp['load'][hours],island_rhs=lp['island_rhs'][hours],
        link_min=lp['link_min'][hours],link_max=lp['link_max'][hours])
    h=solver(local);h.setOptionValue('primal_feasibility_tolerance',1e-8)
    emergency=0.;primal=0.
    for t,hour in enumerate(hours):
        result,x=guarded_hour(h,local,t,accepted['flow'][hour])
        if x is None:raise ValueError(f'24-hour LP pilot failed at {hour}: {result}')
        emergency+=float(np.maximum(x[:lp['ng']][accepted['emergency_mask']],0).sum())
        lhs=lp['A']@x
        lo=np.r_[local['load'][t],local['island_rhs'][t],-lp['ratings']-accepted['flow'][hour]]
        hi=np.r_[local['load'][t],local['island_rhs'][t],lp['ratings']-accepted['flow'][hour]]
        primal=max(primal,float(np.maximum(lo-lhs,0).max()),float(np.maximum(lhs-hi,0).max()))
    if emergency>1e-6 or primal>=1e-4:raise ValueError('Original pilot gates failed')
    return dict(hours=hours.tolist(),emergency_mwh=emergency,max_primal_mw=primal)


def run():
    OUT.mkdir(exist_ok=True);lock=(OUT/'job.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (OUT/'annual.npz').exists() or (OUT/'failure.json').exists():
        raise ValueError('Inspect existing annual witness/failure before restart')
    started=time.perf_counter();audit,active,sources=inputs()
    _,state,market,_,_=aligned();schema,data,*_=state
    fit_state=state
    _,accepted,lp=model()
    mismatch=alignment(fit_state,state,accepted,lp)
    grouped,mixed=offer_groups(schema,accepted,lp)
    costs=transferred_costs(schema,data,market,lp,grouped)
    np.savez_compressed(OUT/'costs.npz',cost=costs)
    control=pilot(lp,accepted,costs)
    write(OUT/'inputs.json',dict(status='frozen_monthly_curves_accepted_physical_lp',
        sources=sources,fit_audit_sha256=digest(FIT/'audit.json'),
        accepted_baseline_witness_sha256=active['witness']['witness_sha256'],
        costs_sha256=digest(OUT/'costs.npz'),pilot=control,
        solar_availability_mismatch=mismatch,offer_columns=lp['ng'],
        mapped_offer_columns=sum(map(len,grouped.values())),
        mixed_renewable_offer_columns=len(mixed),
        preparation_seconds=time.perf_counter()-started,
        limitations=['20-update same-month fit; observed-price root selection on hard hours and three Baltic price cells excluded from training; no forward test',
                     'All observed price cells retained in reported fit MAE',
                     'Curve midpoints sampled on existing LP offer columns; no plant bid reconstruction']))
    print('PILOT',control,'SOLAR_MISMATCH',mismatch,flush=True)
    x,y,obj,info=clear_or_reject(lp|dict(cost=costs),accepted['flow'],costs,OUT/'annual.npz')
    if x is None:
        write(OUT/'failure.json',dict(status='annual_lp_failed_original_gates',market=info))
        return
    emergency=float(np.maximum(x[:,:lp['ng']][:,accepted['emergency_mask']],0).sum())
    if emergency>1e-6:
        write(OUT/'failure.json',dict(status='no_emergency_gate_failed',
            emergency_mwh=emergency,market=info))
        return
    with np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz') as z:observed=z['prices']
    known=np.isfinite(observed).all(axis=0)
    if known.sum()!=41:raise ValueError('Changed corrected SDAC coverage')
    mae=float(abs(y[:,:lp['nz']][:,known]-observed[:,known]).mean())
    write(OUT/'summary.json',dict(status='annual_lp_completed_pending_independent_audit',
        price_mae=mae,emergency_mwh=emergency,market=info,
        witness_sha256=digest(OUT/'annual.npz'),inputs_sha256=digest(OUT/'inputs.json'),
        fitting_price_mae=audit['price_mae'],accepted_baseline_price_mae=active['prices']['equal_zone_mae']))
    print('ANNUAL',mae,'SECONDS',info['clearing_seconds'],flush=True)


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
    try:run()
    except Exception:
        OUT.mkdir(exist_ok=True)
        write(OUT/'failure.json',dict(status='exception',traceback=traceback.format_exc()))
        raise
