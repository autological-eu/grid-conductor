"""Independently replay the saved annual physical LP and baseline comparison."""
import json
import resource

import numpy as np

from forward_hourly_splines_2025 import month_hours
from generation_mix_2025 import CARRIER,ROOT,digest
from monthly_fast_lp_costs_2025 import offer_groups
from monthly_lp_spline_inputs_2025 import aligned
from price_mechanism_2025 import dual_replay
from run_identified_aligned_fast_joint_lp_2025 import OUT,FIT,inputs,transferred_costs
from sigmoid_month_pairs_2025 import metric
from solar_anchor_bids_2025 import model
from solar_country_fit_2025 import write
from supply_knot_network_2025 import generation


def allocate(schema,data,accepted,lp,market,values):
    """Replay illustrative mixed-offer allocation with original member MW."""
    from bidding_zone_network_2025 import build
    native,*_=build()
    carrier=native.generators.carrier.to_numpy(dtype=str)
    layout=json.loads((ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json').read_text())
    keys={(g['zone'],g['technology']):i for i,g in enumerate(schema['groups'])}
    grouped={i:[] for i in range(market.ng)}
    mixed=[]
    for j,members in enumerate(layout['members']):
        kinds={CARRIER[carrier[k]] for k in members}
        if len(kinds)==1:
            key=(str(accepted['offer_zones'][j]),next(iter(kinds)))
            if key in keys:grouped[keys[key]].append(j)
        else:mixed.append(j)
    for j in range(len(layout['members']),lp['ng']):
        key=(str(accepted['offer_zones'][j]),'oil')
        if key not in keys:raise ValueError('Unmapped LP oil group')
        grouped[keys[key]].append(j)
    quantities=np.zeros((8760,market.ng))
    for g,ids in grouped.items():
        if ids:quantities[:,g]=values[:,ids].sum(axis=1)
    native_av=native.get_switchable_as_dense('Generator','p_max_pu').values*native.generators.p_nom.values
    fallback_mwh=0.
    for j in mixed:
        members=layout['members'][j];den=native_av[:,members].sum(axis=1)
        zone=str(accepted['offer_zones'][j])
        absent=den<=1e-8
        kinds={CARRIER[carrier[k]] for k in members}
        fallback=np.zeros(8760)
        for kind in kinds:
            key=(zone,kind)
            if key in keys:fallback+=data['capacity'][:,keys[key]]
        if np.any(absent&(fallback<=1e-8)&(values[:,j]>1e-5)):
            raise ValueError(f'Mixed offer {j} dispatches with no member or group availability')
        effective_den=np.where(absent,fallback,den)
        fallback_mwh+=float(np.maximum(values[absent,j],0).sum())
        for kind in kinds:
            key=(zone,kind)
            ids=[k for k in members if CARRIER[carrier[k]]==kind]
            part=native_av[:,ids].sum(axis=1)
            if key not in keys:
                if part.max()<=1e-8:continue
                raise ValueError(f'Unmapped mixed source with positive availability: {key}')
            numerator=np.where(absent,data['capacity'][:,keys[key]],part)
            quantities[:,keys[key]]+=np.divide(values[:,j]*numerator,effective_den,
                out=np.zeros(8760),where=effective_den>0)
    non_emergency=values[:,:lp['ng']][:,~accepted['emergency_mask']].sum(axis=1)
    residual=quantities.sum(axis=1)-non_emergency
    if abs(residual).max()>1e-4:
        hour=int(abs(residual).argmax())
        unmapped=[(j,float(values[hour,j]),str(accepted['offer_zones'][j]),
                   sorted({CARRIER[carrier[k]] for k in members}))
                  for j,members in enumerate(layout['members'])
                  if len({CARRIER[carrier[k]] for k in members})==1
                  and (str(accepted['offer_zones'][j]),next(iter({CARRIER[carrier[k]] for k in members}))) not in keys
                  and values[hour,j]>1e-5]
        empty_mixed=[(j,float(values[hour,j])) for j in mixed
                     if native_av[hour,layout['members'][j]].sum()<1e-8 and values[hour,j]>1e-5]
        raise ValueError(f'Allocation hour={hour} residual_mw={residual[hour]} '
                         f'unmapped_pure={unmapped[:12]} empty_mixed={empty_mixed[:12]}')
    return quantities,float(values[:,mixed].sum()/1e6),fallback_mwh/1e6


def hourly_mix(modeled,observed):
    mask=np.isfinite(observed);o=np.nan_to_num(observed)
    volume=float(abs(modeled[mask]-o[mask]).mean())
    mt=np.where(mask,modeled,0);ot=np.where(mask,o,0)
    ms=np.divide(mt,mt.sum(axis=2,keepdims=True),out=np.zeros_like(mt),
                 where=mt.sum(axis=2,keepdims=True)>1e-6)
    os=np.divide(ot,ot.sum(axis=2,keepdims=True),out=np.zeros_like(ot),
                 where=ot.sum(axis=2,keepdims=True)>1e-6)
    shares=mask&(mt.sum(axis=2,keepdims=True)>1e-6)&(ot.sum(axis=2,keepdims=True)>1e-6)
    return dict(generation_cells=int(mask.sum()),generation_mae_gw=volume/1000,
                mix_cells=int(shares.sum()),mix_share_mae=float(abs(ms[shares]-os[shares]).mean()))


def run():
    sealed=json.loads((OUT/'inputs.json').read_text())
    summary=json.loads((OUT/'summary.json').read_text())
    fit_audit,active,sources=inputs()
    if sealed['sources']!=sources:
        raise ValueError('Changed source list')
    if summary['inputs_sha256']!=digest(OUT/'inputs.json') or summary['witness_sha256']!=digest(OUT/'annual.npz'):
        raise ValueError('Changed annual witness or inputs')
    if sealed['costs_sha256']!=digest(OUT/'costs.npz'):raise ValueError('Changed cost transfer')
    _,state,market,_,_=aligned();schema,data,_,_,sourcecap=state
    _,accepted,lp=model();grouped,mixed=offer_groups(schema,accepted,lp)
    recomputed=transferred_costs(schema,data,market,lp,grouped)
    with np.load(OUT/'costs.npz') as z:cost=z['cost']
    np.testing.assert_array_equal(cost,recomputed)
    with np.load(OUT/'annual.npz') as z:
        x=z['values'];y=z['row_duals'];objectives=z['objectives']
        assert z['optimal'].all() and np.array_equal(z['hours'],np.arange(8760))
    A=lp['A'];ng=lp['ng'];nz=lp['nz'];nl=lp['nl']
    if x.shape!=(8760,A.shape[1]) or y.shape!=(8760,A.shape[0]):
        raise ValueError('Annual witness shape mismatch')
    maximum=dict(primal_mw=0.,objective_eur=0.,duality_gap_maximum_eur=0.,
                 complementarity_maximum_eur=0.)
    for start in range(0,8760,168):
        sl=slice(start,min(start+168,8760));n=sl.stop-sl.start
        case=dict(A=A,cost=cost[sl],availability=lp['availability'][sl],
            ng=ng,nl=nl,nz=nz,link_min=lp['link_min'][sl],link_max=lp['link_max'][sl],
            load=lp['load'][sl],island_rhs=lp['island_rhs'][sl],
            ratings=lp['ratings'],islands=[None]*lp['island_rhs'].shape[1])
        full_cost=np.c_[cost[sl],np.zeros((n,nl+nz))]
        reduced=full_cost-(A.T@y[sl].T).T
        cert=dual_replay(case,x[sl],y[sl],reduced,objectives[sl],accepted['flow'][sl])
        ax=(A@x[sl].T).T
        lo=np.c_[lp['load'][sl],lp['island_rhs'][sl],-lp['ratings']-accepted['flow'][sl]]
        hi=np.c_[lp['load'][sl],lp['island_rhs'][sl],lp['ratings']-accepted['flow'][sl]]
        maximum['primal_mw']=max(maximum['primal_mw'],float(np.maximum(lo-ax,0).max()),
            float(np.maximum(ax-hi,0).max()))
        maximum['objective_eur']=max(maximum['objective_eur'],
            float(abs((x[sl,:ng]*cost[sl]).sum(axis=1)-objectives[sl]).max()))
        for key in ('duality_gap_maximum_eur','complementarity_maximum_eur'):
            maximum[key]=max(maximum[key],cert[key])
    if any(maximum[key]>=limit for key,limit in [('primal_mw',1e-4),
            ('objective_eur',.05),('duality_gap_maximum_eur',.05),
            ('complementarity_maximum_eur',.05)]):raise ValueError('Original LP gate failed')
    emergency=float(np.maximum(x[:,:ng][:,accepted['emergency_mask']],0).sum())
    if emergency>1e-6:raise ValueError('Emergency generation in annual LP')
    with np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz') as z:observed=z['prices']
    known=np.isfinite(observed).all(axis=0)
    if known.sum()!=41:raise ValueError('Changed corrected price target coverage')
    price=float(abs(y[:,:nz][:,known]-observed[:,known]).mean())
    if abs(price-summary['price_mae'])>1e-9:raise ValueError('Changed price score')
    with np.load(ROOT/active['witness']['witness']) as z:bx=z['values'];by=z['row_duals']
    if digest(ROOT/active['witness']['witness'])!=active['witness']['witness_sha256']:
        raise ValueError('Changed baseline witness')
    quantity,mixed_twh,fallback_twh=allocate(schema,data,accepted,lp,market,x)
    baseline_quantity,_,baseline_fallback_twh=allocate(schema,data,accepted,lp,market,bx)
    model_gen=generation(schema,data,sourcecap,quantity,np.arange(8760))
    baseline_gen=generation(schema,data,sourcecap,baseline_quantity,np.arange(8760))
    hourly=hourly_mix(model_gen,data['observed_generation'])
    baseline_hourly=hourly_mix(baseline_gen,data['observed_generation'])
    months=[]
    for month in range(1,13):
        hours=month_hours(month)
        result,_=metric(schema,data,y[hours,:nz],model_gen[hours],hours,month)
        prior,_=metric(schema,data,by[hours,:nz],baseline_gen[hours],hours,month)
        months.append(dict(month=month,price_mae=result['price_mae'],
            baseline_price_mae=prior['price_mae'],
            generation_mae_twh=result['generation_mae_twh'],
            baseline_generation_mae_twh=prior['generation_mae_twh'],
            generation_normalized_mae=result['generation_normalized_mae'],
            baseline_generation_normalized_mae=prior['generation_normalized_mae']))
    zones=[]
    for j,zone in enumerate(schema['zones']):
        if not known[j]:continue
        target=observed[:,j]
        zones.append(dict(zone=zone,price_mae=float(abs(y[:,j]-target).mean()),
                          baseline_price_mae=float(abs(by[:,j]-target).mean())))
    write(OUT/'audit.json',dict(status='full_8760_original_lp_replay_passed',
        numerical=maximum,emergency_mwh=emergency,price_mae=price,
        baseline_price_mae=float(abs(by[:,:nz][:,known]-observed[:,known]).mean()),
        hourly_generation=hourly,baseline_hourly_generation=baseline_hourly,
        generation_monthly_mae_twh=float(np.mean([r['generation_mae_twh'] for r in months])),
        baseline_generation_monthly_mae_twh=float(np.mean([r['baseline_generation_mae_twh'] for r in months])),
        generation_monthly_normalized_mae=float(np.mean([r['generation_normalized_mae'] for r in months])),
        baseline_generation_monthly_normalized_mae=float(np.mean([r['baseline_generation_normalized_mae'] for r in months])),
        mapped_offer_columns=sum(map(len,grouped.values())),mixed_offer_columns=len(mixed),
        mixed_offer_dispatch_twh=mixed_twh,mixed_zero_member_fallback_twh=fallback_twh,
        baseline_mixed_zero_member_fallback_twh=baseline_fallback_twh,
        solar_availability_mismatch=sealed['solar_availability_mismatch'],
        zones_improved=sum(r['price_mae']<r['baseline_price_mae'] for r in zones),
        zones=zones,months=months,fit_audit_sha256=digest(FIT/'audit.json'),
        inputs_sha256=digest(OUT/'inputs.json'),witness_sha256=digest(OUT/'annual.npz'),
        limitations=['20-update in-sample fit; three Baltic price cells excluded from training but retained in price score',
                     'Fitting and accepted LP solar availability aligned',
                     'Mixed LP offer allocation is illustrative and not unique; zero member-profile hours use zonal technology availability shares',
                     'No next-month price or asset-scenario validation']))
    print('AUDITED',price,maximum,flush=True)


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
    run()
