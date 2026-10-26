"""Independently replay the annual stock timing candidate's emergency failure."""
import json
import calendar

import numpy as np

import solar_anchor_bids_2025 as baseline
from run_annual_norway_stock_2025 import OUT, corrected_load
from generation_mix_2025 import ROOT,digest
from price_mechanism_2025 import dual_replay
from solar_country_fit_2025 import write


def run():
    inputs=json.loads((OUT/'inputs.json').read_text())
    for relative,sha in inputs['source_sha256'].items():
        assert digest(ROOT/relative)==sha, relative
    p,s,m=baseline.model()
    changed,change=corrected_load(p,s['load'])
    np.testing.assert_allclose(change['annual_mwh'],inputs['change']['annual_mwh'],atol=1e-4,rtol=0)
    sealed=json.loads((baseline.OUT/'inputs.json').read_text())
    prop=dict(np.load(baseline.OUT/'proposal.npz'))
    c=baseline.costs(s['cost'],p['zones'],s['offer_zones'].tolist(),sealed['kinds'],
        prop['features'],prop['resource'],1,sealed['design']['bounds_eur_mwh'])
    with np.load(OUT/'annual.npz') as witness:
        x=witness['values'];y=witness['row_duals'];obj=witness['objectives']
        assert witness['optimal'].all()
        np.testing.assert_array_equal(witness['hours'],np.arange(8760))
    emergency=np.maximum(x[:,:p['ng']][:,s['emergency_mask']],0)
    amount=emergency.sum(axis=1)
    maxima=dict(primal_mw=0.,objective_eur=0.,duality_gap_maximum_eur=0.,
                complementarity_maximum_eur=0.)
    for first in range(0,8760,168):
        sl=slice(first,min(first+168,8760));n=sl.stop-sl.start
        local=dict(ng=p['ng'],nl=p['nl'],nz=p['nz'],A=m['A'],cost=c[sl],
                   availability=m['availability'][sl],link_min=m['link_min'][sl],
                   link_max=m['link_max'][sl],load=changed[sl],
                   island_rhs=m['island_rhs'][sl],ratings=m['ratings'],islands=m['islands'])
        rc=np.c_[c[sl],np.zeros((n,p['nl']+p['nz']))]-(m['A'].T@y[sl].T).T
        cert=dual_replay(local,x[sl],y[sl],rc,obj[sl],s['flow'][sl])
        ax=(m['A']@x[sl].T).T
        lo=np.c_[changed[sl],m['island_rhs'][sl],-m['ratings']-s['flow'][sl]]
        hi=np.c_[changed[sl],m['island_rhs'][sl],m['ratings']-s['flow'][sl]]
        maxima['primal_mw']=max(maxima['primal_mw'],float(np.maximum(lo-ax,0).max()),
                               float(np.maximum(ax-hi,0).max()))
        maxima['objective_eur']=max(maxima['objective_eur'],
            float(abs((x[sl,:p['ng']]*c[sl]).sum(axis=1)-obj[sl]).max()))
        for key in ('duality_gap_maximum_eur','complementarity_maximum_eur'):
            maxima[key]=max(maxima[key],cert[key])
    assert maxima['primal_mw']<=1e-4 and maxima['objective_eur']<.05
    assert maxima['duality_gap_maximum_eur']<.05
    assert maxima['complementarity_maximum_eur']<.05
    assert amount.sum()>1e-6
    mask=np.flatnonzero(s['emergency_mask'])
    zones={zone:float(emergency[:,j].sum()) for j,col in enumerate(mask)
           if (zone:=str(s['offer_zones'][col])) and emergency[:,j].sum()>1e-6}
    months=[];offset=0
    for month in range(1,13):
        end=offset+calendar.monthrange(2025,month)[1]*24
        block=amount[offset:end]
        months.append(dict(month=month,emergency_mwh=float(block.sum()),
                           hours=int((block>1e-6).sum())))
        offset=end
    outcome=dict(status='independent_lp_replay_passed_but_no_emergency_gate_failed',
        numerical=maxima,emergency_mwh=float(amount.sum()),
        emergency_hours=int((amount>1e-6).sum()),
        first_emergency_hour=int(np.flatnonzero(amount>1e-6)[0]),
        zones_mwh=zones,months=months,witness_sha256=digest(OUT/'annual.npz'),
        inputs_sha256=digest(OUT/'inputs.json'),
        conclusion='Invalid annual baseline candidate; network-aware annual water retiming is needed.')
    write(OUT/'failure.json',outcome)
    print(json.dumps(outcome),flush=True)


if __name__=='__main__':run()
