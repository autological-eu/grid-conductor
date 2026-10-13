"""Dated NVE zone shares; controlled relocation of existing onshore wind volume.

This isolates geography, not weather/fleet completeness. The current-operating
registry cannot recover farms retired before its retrieval. No generation target
or observed electricity price enters construction. Intra-zone bus shares remain
the existing capacity proxy; national hourly availability and source nameplate
normalisation (including the inherited IRENA trajectory) are conserved.
"""
import json
import numpy as np
import pandas as pd
from bidding_zone_network_2025 import ROOT
from nve_hydro_diagnostics import digest


def dated_capacity(records, snapshots):
    capacity=pd.DataFrame(0.,index=snapshots,columns=['NO1','NO2','NO3','NO4','NO5'])
    seen=set()
    for farm in records:
        zone='NO'+str(farm['ElspotomraadeNummer'])
        if zone not in capacity:raise ValueError('Unknown NVE wind area')
        for batch in farm['Turbiner']:
            key=batch['TurbinID']
            if key in seen:raise ValueError('Duplicate turbine batch')
            seen.add(key)
            if not batch.get('DatoIdriftsatt'):raise ValueError('Missing commissioning date')
            start=pd.Timestamp(batch['DatoIdriftsatt']);end=batch.get('DatoUtavdrift')
            mw=float(batch['AntallTurbiner'])*float(batch['TurbinStorrelse_kW'])/1000
            if not np.isfinite(mw) or mw<0:raise ValueError('Invalid turbine capacity')
            mask=snapshots>=start
            if end:
                finish=pd.Timestamp(end)
                if finish<start:raise ValueError('Retirement precedes commissioning')
                mask&=snapshots<finish
            capacity.loc[mask,zone]+=mw
    if (capacity.sum(axis=1)<=0).any():raise ValueError('Empty dated fleet')
    return capacity


def apply(n):
    path=ROOT/'data/bidding-zone-source-audit-2025/nve-wind.json'
    receipt=json.loads(path.with_suffix('.meta.json').read_text())
    assert digest(path)==receipt['sha256']
    cap=dated_capacity(json.loads(path.read_text()),n.snapshots)
    # This experiment has static GSKs; reject instead of hiding commissioning.
    if not np.all(cap.values==cap.values[0]):raise ValueError('Time-varying fleet requires a new GSK design')
    rows=n.generators
    mask=rows.carrier.eq('onwind')&rows.bus.map(n.buses.country).eq('NO')
    names=rows.index[mask];old=rows.loc[names,'p_nom'].copy()
    cf=n.get_switchable_as_dense('Generator','p_max_pu')
    national=(cf[names]*old).sum(axis=1);nominal=float(old.sum())
    if nominal<=0:raise ValueError('Missing source onshore wind')
    zones=rows.loc[names,'bus'].map(n.buses.bidding_zone)
    share=cap.iloc[0]/cap.iloc[0].sum();alloc={}
    for zone in cap.columns:
        ids=names[zones.eq(zone)]
        if share[zone]>0 and (not len(ids) or old.loc[ids].sum()<=0):raise ValueError('Missing target-zone source buses')
        if len(ids):
            weights=old.loc[ids]/old.loc[ids].sum()
            n.generators.loc[ids,'p_nom']=nominal*share[zone]*weights
            for key in ids:alloc[key]=float(share[zone]*weights[key])
    # Same national hourly curve in each target zone: geography-only control.
    # Values >1 can encode inherited IRENA scaling relative to old source p_nom.
    n.generators_t.p_max_pu.loc[:,names]=np.repeat((national/nominal).values[:,None],len(names),axis=1)
    np.testing.assert_allclose((n.get_switchable_as_dense('Generator','p_max_pu')[names]*n.generators.loc[names,'p_nom']).sum(axis=1),national,rtol=1e-12,atol=1e-7)
    return dict(source=receipt,dated_zone_capacity_mw=cap.iloc[0].to_dict(),
        source_normalisation_mw=nominal,national_available_twh=float(national.sum()/1e6),allocation=alloc,
        scope='Current-operating NVE registry dated turbine batches; historical completeness unverified',
        limits=['National hourly available MW conserved; not a weather or total-capacity correction.',
                'Registry MW determine shares only; inherited IRENA national trajectory remains.',
                'Common national weather curve isolates geography; regional weather is not certified.',
                'Within-zone bus capacity weights remain proxies; GSK recomputed from relocated capacity.',
                'Offshore wind, hydro, demand, fuel bids, grid topology and ratings unchanged.'])
