"""Full-year source-stock Norwegian hydro timing control on accepted annual bids."""
import json
import resource

import numpy as np
import xarray as xr

import solar_anchor_bids_2025 as baseline
from joint_network_clear_2025 import clear_or_reject
from generation_mix_2025 import ROOT,digest
from solar_country_fit_2025 import write
from run_annual_sweden_geography_2025 import NATIVE,BASELINE

OUT=ROOT/'data/bidding-zone-network-2025/annual-norway-stock-v1'
SOURCE=ROOT/'data/bidding-zone-network-2025/nordic-stock-reconciliation-v1'
NVE=ROOT/'data/hydro-observations-2025/nve-updated-model-v5'


def corrected_load(p,original):
    zones=[z for z in p['zones'] if z.startswith('NO')]
    assert zones==['NO1','NO2','NO3','NO4','NO5']
    ids=[p['zones'].index(z) for z in zones]
    with xr.open_dataset(NATIVE) as n:
        mapping=dict(zip(n.buses_i.values,n.buses_bidding_zone.values))
        gross=np.zeros((8760,5))
        for j,bus in enumerate(n.loads_bus.values):
            zone=str(mapping[bus])
            if zone in zones:gross[:,zones.index(zone)]+=n.loads_t_p_set.values[:,j]
    old=gross-original[:,ids]
    with np.load(SOURCE/'hydro.npz') as h:
        power=h['power'].copy();old_power=h['old_power'].copy()
    np.testing.assert_allclose(old.sum(axis=1),old_power,atol=1e-4,rtol=0)
    if old.min() < -1e-4:raise ValueError('Negative original Norwegian fixed hydro')
    share=np.divide(old,old_power[:,None],out=np.zeros_like(old),where=old_power[:,None]>1e-6)
    if np.any((old_power<=1e-6)&(power>1e-6)):
        raise ValueError('New hydro requires undefined geographic allocation')
    new=original.copy()
    new[:,ids]=gross-power[:,None]*share
    np.testing.assert_allclose((gross-new[:,ids]).sum(axis=1),power,atol=1e-4,rtol=0)
    np.testing.assert_allclose(old_power.sum(),power.sum(),atol=1e-4,rtol=0)
    return new,dict(zones=zones,annual_mwh=float(power.sum()),
                    original_mwh=float(old_power.sum()),
                    max_hourly_change_mw=float(abs(power-old_power).max()),
                    geography='unchanged original hourly shares')


def run():
    OUT.mkdir(exist_ok=False)
    active=json.loads(BASELINE.read_text())
    assert active['model']=='solar-anchor-bids-v1' and active['annual_case']=='resource_full'
    for path,sha in active['artifacts'].items():assert digest(ROOT/path)==sha
    source=json.loads((SOURCE/'audit.json').read_text())
    assert source['summary_sha256']==digest(SOURCE/'summary.json')
    meta=json.loads((NVE/'summary.json').read_text())
    assert digest(NVE/'water.npz')==meta['water_witness_sha256']
    p,s,m=baseline.model();new,change=corrected_load(p,s['load']);m['load']=new
    sealed=json.loads((baseline.OUT/'inputs.json').read_text())
    prop=dict(np.load(baseline.OUT/'proposal.npz'))
    c=baseline.costs(s['cost'],p['zones'],s['offer_zones'].tolist(),sealed['kinds'],
                     prop['features'],prop['resource'],1,sealed['design']['bounds_eur_mwh'])
    paths=[BASELINE,NATIVE,SOURCE/'summary.json',SOURCE/'audit.json',SOURCE/'hydro.npz',
           NVE/'summary.json',NVE/'water.npz',baseline.OUT/'inputs.json',
           baseline.OUT/'proposal.npz']
    provenance={str(path.relative_to(ROOT)):digest(path) for path in paths}
    write(OUT/'inputs.json',dict(scope='annual Norway source-stock timing only',
        change=change,source_sha256=provenance,
        excluded=['Swedish stock correction','river reconstitution','JAO envelopes','bid refitting']))
    path=OUT/'annual.npz'
    x,y,_,info=clear_or_reject(m|dict(cost=c),s['flow'],c,path)
    if x is None:
        write(OUT/'failure.json',dict(status='source_schedule_infeasible_in_accepted_network',
            info=info,inputs_sha256=digest(OUT/'inputs.json')))
        print('INFEASIBLE',info,flush=True)
        return
    with np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz') as z:target=z['prices']
    known=np.isfinite(target).all(axis=0)
    with np.load(ROOT/active['witness']['witness']) as z:before=z['row_duals'][:,:p['nz']]
    rows=[dict(zone=zone,baseline_mae=float(abs(before[:,j]-target[:,j]).mean()),
               candidate_mae=float(abs(y[:,j]-target[:,j]).mean()))
          for j,zone in enumerate(p['zones']) if known[j]]
    emergency=float(np.maximum(x[:,:p['ng']][:,s['emergency_mask']],0).sum())
    if emergency>1e-6:
        needed=np.maximum(x[:,:p['ng']][:,s['emergency_mask']],0).sum(axis=1)
        write(OUT/'failure.json',dict(status='no_emergency_gate_failed',
            emergency_mwh=emergency,emergency_hours=int((needed>1e-6).sum()),
            first_emergency_hour=int(np.flatnonzero(needed>1e-6)[0]),
            witness_sha256=digest(path),inputs_sha256=digest(OUT/'inputs.json'),
            market=info,change=change,
            note='Candidate is invalid for baseline promotion; price score withheld.'))
        print('NO_EMERGENCY_GATE_FAILED',emergency,int((needed>1e-6).sum()),flush=True)
        return
    write(OUT/'summary.json',dict(status='annual_norway_stock_only_control_completed',
        source_sha256=provenance,inputs_sha256=digest(OUT/'inputs.json'),
        witness_sha256=digest(path),market=info,change=change,zone_scores=rows,
        baseline_price_mae=float(np.mean([r['baseline_mae'] for r in rows])),
        candidate_price_mae=float(np.mean([r['candidate_mae'] for r in rows])),
        emergency_mwh=emergency,limitations=[
            'NVE-stock schedule is a retrospective reconstruction, not an operational forecast.',
            'Only Norwegian country hydro timing changed; Swedish correction and JAO envelopes are absent.',
            'The original hourly Norwegian geographic allocation is retained.',
            'No automatic baseline promotion.']))
    print('annual',np.mean([r['baseline_mae'] for r in rows]),
          np.mean([r['candidate_mae'] for r in rows]),flush=True)


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3))
    run()
