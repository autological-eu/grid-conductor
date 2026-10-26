"""Annual geography-only control on the accepted baseline, without invented water data.

This does not apply the Jan/Feb stock, ROR or JAO envelope corrections.
"""
import json
import resource
from pathlib import Path

import numpy as np
import xarray as xr

import solar_anchor_bids_2025 as baseline
from joint_network_clear_2025 import clear_or_reject
from generation_mix_2025 import ROOT, digest
from solar_country_fit_2025 import write

OUT = ROOT/'data/bidding-zone-network-2025/annual-sweden-geography-v1'
NATIVE = ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1/native.nc'
WATER = ROOT/'data/bidding-zone-network-2025/sweden-stock-window-v2/water.npz'
BASELINE = ROOT/'config/active-research-baseline.json'


def corrected_load(p, original):
    zones=[zone for zone in p['zones'] if zone.startswith('SE')]
    assert zones == ['SE1','SE2','SE3','SE4']
    ids=[p['zones'].index(zone) for zone in zones]
    with xr.open_dataset(NATIVE) as n:
        mapping=dict(zip(n.buses_i.values,n.buses_bidding_zone.values))
        gross=np.zeros((8760,4))
        for j,bus in enumerate(n.loads_bus.values):
            zone=str(mapping[bus])
            if zone in zones:gross[:,zones.index(zone)]+=n.loads_t_p_set.values[:,j]
    old=gross-original[:,ids]
    if old.min() < -1e-4:raise ValueError('Original fixed hydro is negative')
    with np.load(WATER) as source:shares=source['static_allocation'].copy()
    if np.min(shares)<0 or abs(shares.sum()-1)>1e-8:raise ValueError('Invalid source shares')
    country=old.sum(axis=1)
    updated=original.copy()
    updated[:,ids]=gross-country[:,None]*shares
    np.testing.assert_allclose(updated.sum(axis=1),original.sum(axis=1),rtol=0,atol=1e-7)
    np.testing.assert_allclose((gross-updated[:,ids]).sum(axis=1),country,rtol=0,atol=1e-7)
    return updated,dict(zones=zones,shares=shares.tolist(),
                        old_fixed_twh=(old.sum(axis=0)/1e6).tolist(),
                        new_fixed_twh=(country.sum()*shares/1e6).tolist(),
                        retained_country_fixed_twh=float(country.sum()/1e6))


def run():
    OUT.mkdir(exist_ok=False)
    active=json.loads(BASELINE.read_text())
    assert active['model']=='solar-anchor-bids-v1' and active['annual_case']=='resource_full'
    for path,expected in active['artifacts'].items():assert digest(ROOT/path)==expected
    p,s,m=baseline.model()
    changed,geography=corrected_load(p,s['load'])
    m['load']=changed
    sealed=json.loads((baseline.OUT/'inputs.json').read_text())
    prop=dict(np.load(baseline.OUT/'proposal.npz'))
    c=baseline.costs(s['cost'],p['zones'],s['offer_zones'].tolist(),
                     sealed['kinds'],prop['features'],prop['resource'],1,
                     sealed['design']['bounds_eur_mwh'])
    paths=[Path(__file__),BASELINE,NATIVE,WATER,baseline.OUT/'inputs.json',
           baseline.OUT/'proposal.npz',ROOT/active['witness']['witness']]
    provenance={str(path.relative_to(ROOT)):digest(path) for path in paths}
    write(OUT/'inputs.json',dict(scope='annual fixed-hydro geography-only control',
                                 source_sha256=provenance,geography=geography,
                                 excluded=['Jan/Feb corrected stock and inflow','corrected river availability',
                                           'JAO directional envelopes','bid refitting']))
    path=OUT/'annual.npz'
    x,y,_,info=clear_or_reject(m|dict(cost=c),s['flow'],c,path)
    if x is None:
        write(OUT/'failure.json',dict(info=info))
        raise RuntimeError('Annual candidate failed original market gates')
    with np.load(ROOT/active['witness']['witness']) as witness:
        before=witness['row_duals'][:,:p['nz']]
    with np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz') as z:target=z['prices']
    known=np.isfinite(target).all(axis=0)
    if known.sum()!=41:raise ValueError('Changed price target coverage')
    rows=[]
    for j,zone in enumerate(p['zones']):
        if not known[j]:continue
        rows.append(dict(zone=zone,baseline_mae=float(abs(before[:,j]-target[:,j]).mean()),
                         candidate_mae=float(abs(y[:,j]-target[:,j]).mean()),
                         baseline_bias=float((before[:,j]-target[:,j]).mean()),
                         candidate_bias=float((y[:,j]-target[:,j]).mean())))
    emergency=float(np.maximum(x[:,:p['ng']][:,s['emergency_mask']],0).sum())
    if emergency>1e-6:raise ValueError('Candidate uses emergency supply')
    write(OUT/'summary.json',dict(status='annual_geography_only_control_completed',
        hours=8760,optimal_hours=info['optimal_hours'],
        baseline_mae=float(np.mean([r['baseline_mae'] for r in rows])),
        candidate_mae=float(np.mean([r['candidate_mae'] for r in rows])),
        emergency_mwh=emergency,geography=geography,zone_scores=rows,
        market=info,inputs_sha256=digest(OUT/'inputs.json'),
        witness_sha256=digest(path),limitations=[
            'Only Swedish geographic shares changed; annual water, river and JAO corrections are unavailable.',
            'Same-year price score is retrospective reconstruction, not forecast validation.',
            'No baseline promotion is implied by this control.']))
    print('annual',np.mean([r['baseline_mae'] for r in rows]),
          np.mean([r['candidate_mae'] for r in rows]),flush=True)


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3))
    run()
