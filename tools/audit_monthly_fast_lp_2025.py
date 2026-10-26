"""Independent replay of the one-pass annual joint LP and fitted-bid transfer."""
import json
import resource
import numpy as np
from monthly_lp_spline_inputs_2025 import aligned
from monthly_fast_lp_costs_2025 import transferred_costs
from clear_monthly_fast_lp_2025 import OUT,FIT
from forward_hourly_splines_2025 import month_hours
from price_mechanism_2025 import dual_replay
from supply_knot_network_2025 import generation
from sigmoid_month_pairs_2025 import metric
from solar_country_fit_2025 import write
from generation_mix_2025 import ROOT,digest


def run():
    sealed=json.loads((OUT/'inputs.json').read_text())
    summary=json.loads((OUT/'summary.json').read_text())
    assert sealed['offer_columns']==799 and summary['inputs_sha256']==digest(OUT/'inputs.json')
    assert summary['witness_sha256']==digest(OUT/'annual.npz')
    for relative,sha in sealed['sources'].items():
        assert digest(ROOT/relative)==sha,relative
    base,state,market,network,design=aligned()
    s,d,A,emergency,sourcecap=state
    from solar_anchor_bids_2025 import model
    p,accepted,lp=model()
    physical=lp['A'];ng=lp['ng'];ne=int(accepted['emergency_mask'].sum())
    cost,transfer=transferred_costs(s,d,market,accepted,lp,FIT)
    assert transfer==sealed['transfer']
    availability=lp['availability']
    with np.load(OUT/'annual.npz') as witness:
        x=witness['values'];y=witness['row_duals'];obj=witness['objectives']
        assert witness['optimal'].all()
        np.testing.assert_array_equal(witness['hours'],np.arange(8760))
        assert x.shape==(8760,physical.shape[1])
        assert y.shape==(8760,physical.shape[0])
    maximum=dict(primal_mw=0.,objective_eur=0.,duality_gap_maximum_eur=0.,
                 complementarity_maximum_eur=0.)
    for start in range(0,8760,168):
        sl=slice(start,min(start+168,8760));n=sl.stop-sl.start
        local=dict(ng=ng,nl=s['nl'],nz=s['nz'],A=physical,
            cost=cost[sl],availability=availability[sl],
            link_min=d['link_min'][sl],link_max=d['link_max'][sl],
            load=d['load'][sl],island_rhs=d['island_rhs'][sl],
            ratings=d['ratings'],islands=[None]*d['island_rhs'].shape[1])
        rc=np.c_[cost[sl],np.zeros((n,s['nl']+s['nz']))]-(physical.T@y[sl].T).T
        cert=dual_replay(local,x[sl],y[sl],rc,obj[sl],d['flow'][sl])
        ax=(physical@x[sl].T).T
        lo=np.c_[d['load'][sl],d['island_rhs'][sl],-d['ratings']-d['flow'][sl]]
        hi=np.c_[d['load'][sl],d['island_rhs'][sl],d['ratings']-d['flow'][sl]]
        maximum['primal_mw']=max(maximum['primal_mw'],
            float(np.maximum(lo-ax,0).max()),float(np.maximum(ax-hi,0).max()))
        maximum['objective_eur']=max(maximum['objective_eur'],
            float(abs((x[sl,:ng]*cost[sl]).sum(axis=1)-obj[sl]).max()))
        for key in ('duality_gap_maximum_eur','complementarity_maximum_eur'):
            maximum[key]=max(maximum[key],cert[key])
    if any(maximum[k]>=limit for k,limit in [('primal_mw',1e-4),('objective_eur',.05),
            ('duality_gap_maximum_eur',.05),('complementarity_maximum_eur',.05)]):
        raise ValueError('Original annual numerical gate failed')
    emergency_mwh=float(np.maximum(x[:,:ng][:,accepted['emergency_mask']],0).sum())
    if emergency_mwh>1e-6:raise ValueError('Emergency supply in annual witness')
    with np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz') as target:
        observed=target['prices']
    known=np.isfinite(observed).all(axis=0)
    if known.sum()!=41:raise ValueError('Changed target coverage')
    price_mae=float(abs(y[:,:s['nz']][:,known]-observed[:,known]).mean())
    if abs(price_mae-summary['price_mae'])>1e-9:raise ValueError('Changed price score')
    # Keep original source-offer allocation; grouped mix is only illustrative.
    from generation_mix_2025 import CARRIER
    layout=json.loads((ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json').read_text())
    from bidding_zone_network_2025 import build
    native,*_=build();carrier=native.generators.carrier.to_numpy(dtype=str)
    grouped={i:[] for i in range(market.ng)}
    keys={(g['zone'],g['technology']):i for i,g in enumerate(s['groups'])}
    for j,members in enumerate(layout['members']):
        zone=str(accepted['offer_zones'][j]);kinds={CARRIER[carrier[k]] for k in members}
        if len(kinds)!=1:continue
        kind=next(iter(kinds))
        key=(str(zone),kind)
        if key in keys:grouped[keys[key]].append(j)
    for j in range(len(layout['members']),ng):
        key=(str(accepted['offer_zones'][j]),'oil')
        if key not in keys:raise ValueError('Unmapped oil source column')
        grouped[keys[key]].append(j)
    mixed=[j for j,members in enumerate(layout['members'])
           if len({CARRIER[carrier[k]] for k in members})>1]
    native_available=native.get_switchable_as_dense('Generator','p_max_pu').values*native.generators.p_nom.values
    def allocate(values):
        quantities=np.zeros((8760,market.ng))
        for g,ids in grouped.items():
            if ids:quantities[:,g]=values[:,ids].sum(axis=1)
        for j in mixed:
            members=layout['members'][j];denominator=native_available[:,members].sum(axis=1)
            zone=str(accepted['offer_zones'][j])
            for kind in {CARRIER[carrier[k]] for k in members}:
                key=(zone,kind)
                if key not in keys:raise ValueError('Unmapped mixed source '+str(key))
                ids=[k for k in members if CARRIER[carrier[k]]==kind]
                part=native_available[:,ids].sum(axis=1)
                quantities[:,keys[key]]+=np.divide(values[:,j]*part,denominator,
                    out=np.zeros(8760),where=denominator>0)
        if abs(quantities.sum(axis=1)-values[:,:ng][:,~accepted['emergency_mask']].sum(axis=1)).max()>1e-4:
            raise ValueError('Technology allocation does not conserve LP generation')
        return quantities
    quantities=allocate(x)
    mixed_twh=float(x[:,mixed].sum()/1e6)
    baseline_path=ROOT/'data/bidding-zone-network-2025/solar-anchor-bids-v1/resource_full.npz'
    with np.load(baseline_path) as baseline:
        prior_x=baseline['values'];prior_y=baseline['row_duals']
    prior_quantity=allocate(prior_x)
    months=[]
    for month in range(1,13):
        hours=month_hours(month)
        mix=generation(s,d,sourcecap,quantities[hours],hours)
        score,monthly=metric(s,d,y[hours,:s['nz']],mix,hours,month)
        prior_mix=generation(s,d,sourcecap,prior_quantity[hours],hours)
        prior_score,_=metric(s,d,prior_y[hours,:s['nz']],prior_mix,hours,month)
        months.append(dict(month=month,price_mae=score['price_mae'],
            generation_mae_twh=score['generation_mae_twh'],
            generation_normalized_mae=score['generation_normalized_mae'],
            generation_cells=score['generation_cells'],baseline_price_mae=prior_score['price_mae'],
            baseline_generation_mae_twh=prior_score['generation_mae_twh'],
            baseline_generation_normalized_mae=prior_score['generation_normalized_mae']))
    write(OUT/'audit.json',dict(status='full_8760_lp_source_and_generation_replay_passed',
        numerical=maximum,emergency_mwh=emergency_mwh,price_mae=price_mae,
        generation_monthly_mae_twh=float(np.mean([r['generation_mae_twh'] for r in months])),
        generation_monthly_normalized_mae=float(np.mean([r['generation_normalized_mae'] for r in months])),
        mixed_offer_dispatch_twh=mixed_twh,
        baseline_witness_sha256=digest(baseline_path),
        baseline_price_mae=float(abs(prior_y[:,:s['nz']][:,known]-observed[:,known]).mean()),
        baseline_generation_monthly_mae_twh=float(np.mean([r['baseline_generation_mae_twh'] for r in months])),
        months=months,summary_sha256=digest(OUT/'summary.json'),
        witness_sha256=digest(OUT/'annual.npz'),
        limitations=['Year-specific monthly bid fitting is in-sample reconstruction.',
                     'Original LP offer columns preserved; mixed renewable allocation remains illustrative.',
                     'Mixed-offer generation uses source-member available-MW shares; individual technologies are not uniquely determined by the LP.']))
    print('AUDITED YEAR',price_mae,maximum,flush=True)


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
    run()
