"""Independent full-year LP, source-availability and generation replay."""
import json
import resource
import numpy as np
from scipy.sparse import hstack

from monthly_lp_spline_inputs_2025 import aligned
from clear_monthly_lp_splines_2025 import OUT,FIT,BINS,offer_costs
from conditional_monotone_market_2025 import ConditionalMarket
from forward_hourly_splines_2025 import month_hours
from price_mechanism_2025 import dual_replay
from supply_knot_network_2025 import generation
from sigmoid_month_pairs_2025 import metric
from solar_country_fit_2025 import write
from generation_mix_2025 import ROOT,digest


def run():
    sealed=json.loads((OUT/'inputs.json').read_text())
    summary=json.loads((OUT/'summary.json').read_text())
    assert sealed['bins']==BINS and summary['inputs_sha256']==digest(OUT/'inputs.json')
    assert summary['witness_sha256']==digest(OUT/'annual.npz')
    for relative,sha in sealed['source_sha256'].items():
        assert digest(ROOT/relative)==sha,relative
    base,state,market,network,design=aligned()
    s,d,A,emergency,sourcecap=state
    market.__class__=ConditionalMarket
    market.reference=np.maximum(market.capacity.max(axis=0),.001)
    ng=market.ng;ne=emergency.shape[1]
    physical=hstack([A[:,np.repeat(np.arange(ng),BINS)],emergency,A[:,ng:]],format='csc')
    cost=offer_costs(s,d,market)
    availability=np.c_[np.repeat(d['capacity']/BINS,BINS,axis=1),
                       d['emergency_available']]
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
        local=dict(ng=ng*BINS+ne,nl=s['nl'],nz=s['nz'],A=physical,
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
            float(abs((x[sl,:ng*BINS+ne]*cost[sl]).sum(axis=1)-obj[sl]).max()))
        for key in ('duality_gap_maximum_eur','complementarity_maximum_eur'):
            maximum[key]=max(maximum[key],cert[key])
    if any(maximum[k]>=limit for k,limit in [('primal_mw',1e-4),('objective_eur',.05),
            ('duality_gap_maximum_eur',.05),('complementarity_maximum_eur',.05)]):
        raise ValueError('Original annual numerical gate failed')
    emergency_mwh=float(np.maximum(x[:,ng*BINS:ng*BINS+ne],0).sum())
    if emergency_mwh>1e-6:raise ValueError('Emergency supply in annual witness')
    with np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz') as target:
        observed=target['prices']
    known=np.isfinite(observed).all(axis=0)
    if known.sum()!=41:raise ValueError('Changed target coverage')
    price_mae=float(abs(y[:,:s['nz']][:,known]-observed[:,known]).mean())
    if abs(price_mae-summary['price_mae'])>1e-9:raise ValueError('Changed price score')
    quantities=x[:,:ng*BINS].reshape(8760,ng,BINS).sum(axis=2)
    months=[]
    for month in range(1,13):
        hours=month_hours(month)
        mix=generation(s,d,sourcecap,quantities[hours],hours)
        score,monthly=metric(s,d,y[hours,:s['nz']],mix,hours,month)
        months.append(dict(month=month,price_mae=score['price_mae'],
            generation_mae_twh=score['generation_mae_twh'],
            generation_normalized_mae=score['generation_normalized_mae'],
            generation_cells=score['generation_cells']))
    write(OUT/'audit.json',dict(status='full_8760_lp_source_and_generation_replay_passed',
        numerical=maximum,emergency_mwh=emergency_mwh,price_mae=price_mae,
        generation_monthly_mae_twh=float(np.mean([r['generation_mae_twh'] for r in months])),
        generation_monthly_normalized_mae=float(np.mean([r['generation_normalized_mae'] for r in months])),
        months=months,summary_sha256=digest(OUT/'summary.json'),
        witness_sha256=digest(OUT/'annual.npz'),
        limitations=['Year-specific monthly bid fitting is in-sample reconstruction.',
                     'Grouped eight-segment offers preserve physical LP columns but do not identify actual auction orders.']))
    print('AUDITED YEAR',price_mae,maximum,flush=True)


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
    run()
