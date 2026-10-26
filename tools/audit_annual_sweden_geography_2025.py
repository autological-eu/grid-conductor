"""Replay the annual Swedish geography-only LP witness and source conservation."""
import json
import numpy as np
from price_mechanism_2025 import dual_replay
from generation_mix_2025 import ROOT, digest
from run_annual_sweden_geography_2025 import OUT, corrected_load
import solar_anchor_bids_2025 as baseline
from solar_country_fit_2025 import write


def run():
    inputs=json.loads((OUT/'inputs.json').read_text())
    summary=json.loads((OUT/'summary.json').read_text())
    assert summary['inputs_sha256']==digest(OUT/'inputs.json')
    assert summary['witness_sha256']==digest(OUT/'annual.npz')
    for relative,sha in inputs['source_sha256'].items():
        assert digest(ROOT/relative)==sha, relative
    p,s,m=baseline.model()
    new,geography=corrected_load(p,s['load'])
    np.testing.assert_allclose(geography['shares'],inputs['geography']['shares'],rtol=0,atol=0)
    np.testing.assert_array_equal(m['load'],s['load'])
    sealed=json.loads((baseline.OUT/'inputs.json').read_text())
    prop=dict(np.load(baseline.OUT/'proposal.npz'))
    c=baseline.costs(s['cost'],p['zones'],s['offer_zones'].tolist(),sealed['kinds'],
                     prop['features'],prop['resource'],1,sealed['design']['bounds_eur_mwh'])
    with np.load(OUT/'annual.npz') as witness:
        x=witness['values'];y=witness['row_duals'];obj=witness['objectives']
        assert x.shape==(8760,m['A'].shape[1]) and y.shape==(8760,m['A'].shape[0])
        assert witness['optimal'].all()
        np.testing.assert_array_equal(witness['hours'],np.arange(8760))
    maximum=dict(primal_mw=0.,objective_eur=0.,duality_gap_maximum_eur=0.,
                 complementarity_maximum_eur=0.)
    for start in range(0,8760,168):
        sl=slice(start,min(start+168,8760));n=sl.stop-sl.start
        local=dict(ng=p['ng'],nl=p['nl'],nz=p['nz'],A=m['A'],cost=c[sl],
                   availability=m['availability'][sl],link_min=m['link_min'][sl],
                   link_max=m['link_max'][sl],load=new[sl],
                   island_rhs=m['island_rhs'][sl],ratings=m['ratings'],
                   islands=m['islands'])
        rc=np.c_[c[sl],np.zeros((n,p['nl']+p['nz']))]-(m['A'].T@y[sl].T).T
        cert=dual_replay(local,x[sl],y[sl],rc,obj[sl],s['flow'][sl])
        ax=(m['A']@x[sl].T).T
        lo=np.c_[new[sl],m['island_rhs'][sl],-m['ratings']-s['flow'][sl]]
        hi=np.c_[new[sl],m['island_rhs'][sl],m['ratings']-s['flow'][sl]]
        maximum['primal_mw']=max(maximum['primal_mw'],float(np.maximum(lo-ax,0).max()),
                                 float(np.maximum(ax-hi,0).max()))
        maximum['objective_eur']=max(maximum['objective_eur'],
                                     float(abs((x[sl,:p['ng']]*c[sl]).sum(axis=1)-obj[sl]).max()))
        for key in ('duality_gap_maximum_eur','complementarity_maximum_eur'):
            maximum[key]=max(maximum[key],cert[key])
    assert maximum['primal_mw']<=1e-4 and maximum['objective_eur']<.05
    assert float(np.maximum(x[:,:p['ng']][:,s['emergency_mask']],0).sum())<=1e-6
    with np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz') as t:
        target=t['prices']
    known=np.isfinite(target).all(axis=0)
    assert known.sum()==41
    mae=float(abs(y[:,:p['nz']][:,known]-target[:,known]).mean())
    assert abs(mae-summary['candidate_mae'])<1e-9
    write(OUT/'audit.json',dict(status='annual_independent_lp_replay_passed',
         witness_sha256=digest(OUT/'annual.npz'),summary_sha256=digest(OUT/'summary.json'),
         numerical=maximum,known_zones=int(known.sum()),price_mae=mae,
         load_conservation_max_mw=float(abs(new.sum(axis=1)-s['load'].sum(axis=1)).max()),
         limitations=['Geography-only test: the two-month water, river and border controls do not extend through the year.']))
    print(maximum,flush=True)


if __name__=='__main__':run()
