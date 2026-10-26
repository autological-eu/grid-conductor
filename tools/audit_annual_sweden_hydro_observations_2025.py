"""Source-audited annual Swedish hydro comparison; observed output is validation only."""
import json
import calendar
from pathlib import Path

import numpy as np
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import solar_anchor_bids_2025 as baseline
from run_annual_sweden_geography_2025 import corrected_load, OUT as CONTROL, NATIVE
from audit_2025_generation_observations import summarize,month_bounds
from carbon_pilot import parse_generation
from generation_mix_2025 import ROOT,digest
from solar_country_fit_2025 import write

OUT=ROOT/'data/bidding-zone-source-audit-2025/annual-sweden-hydro-v2'


def run():
    OUT.mkdir(exist_ok=False)
    control=json.loads((CONTROL/'audit.json').read_text())
    assert control['status']=='annual_independent_lp_replay_passed'
    p,s,_=baseline.model()
    new,geography=corrected_load(p,s['load'])
    zones=geography['zones'];ids=[p['zones'].index(z) for z in zones]
    with xr.open_dataset(NATIVE) as n:
        mapping=dict(zip(n.buses_i.values,n.buses_bidding_zone.values))
        gross=np.zeros((8760,4))
        for j,bus in enumerate(n.loads_bus.values):
            zone=str(mapping[bus])
            if zone in zones:gross[:,zones.index(zone)]+=n.loads_t_p_set.values[:,j]
    before=gross-s['load'][:,ids]
    after=gross-new[:,ids]
    layout_path=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json'
    layout=json.loads(layout_path.read_text())
    with xr.open_dataset(NATIVE) as n:
        carriers=n.generators_carrier.values.astype(str)
        rz=dict(zip(n.buses_i.values,n.buses_bidding_zone.values))
        source_zones=np.array([str(rz[bus]) for bus in n.generators_bus.values])
    ror_columns={zone:[] for zone in zones}
    for g,members in enumerate(layout['members']):
        actual={str(carriers[i]) for i in members}
        zone_set={str(source_zones[i]) for i in members}
        if actual=={'ror'} and len(zone_set)==1 and next(iter(zone_set)) in ror_columns:
            ror_columns[next(iter(zone_set))].append(g)
        elif 'ror' in actual and any(z in ror_columns for z in zone_set):
            raise ValueError('Mixed Swedish ROR offer cannot be assigned without a split')
    active=json.loads((ROOT/'config/active-research-baseline.json').read_text())
    with np.load(ROOT/active['witness']['witness']) as witness:
        baseline_dispatch=witness['values']
    with np.load(CONTROL/'annual.npz') as witness:
        candidate_dispatch=witness['values']
    prior=before.copy();candidate=after.copy()
    prior_ror=np.zeros_like(prior);candidate_ror=np.zeros_like(candidate)
    for j,zone in enumerate(zones):
        cols=ror_columns[zone]
        prior_ror[:,j]=baseline_dispatch[:,cols].sum(axis=1)
        candidate_ror[:,j]=candidate_dispatch[:,cols].sum(axis=1)
    prior+=prior_ror;candidate+=candidate_ror
    reported=np.full((8760,4),np.nan)
    sources={str((CONTROL/'audit.json').relative_to(ROOT)):digest(CONTROL/'audit.json'),
             str(NATIVE.relative_to(ROOT)):digest(NATIVE),
             str(layout_path.relative_to(ROOT)):digest(layout_path),
             str((ROOT/active['witness']['witness']).relative_to(ROOT)):digest(ROOT/active['witness']['witness']),
             str((CONTROL/'annual.npz').relative_to(ROOT)):digest(CONTROL/'annual.npz')}
    rows=[];offset=0
    for month in range(1,13):
        hours=calendar.monthrange(2025,month)[1]*24
        start,end=month_bounds(month)
        for j,zone in enumerate(zones):
            path=ROOT/f'data/carbon-pilot/map-2025/{zone}/{month:02d}.json'
            receipt=path.with_suffix('.receipt.json')
            meta=json.loads(receipt.read_text())
            raw=ROOT/f'data/carbon-pilot/entsoe/raw/{zone}-{start:%Y%m%d}-{end:%Y%m%d}.xml'
            assert digest(path)==meta['sha256'] and digest(raw)==meta['source']['sha256']
            values=json.loads(path.read_text());assert len(values)==hours
            summarize(parse_generation(raw.read_bytes(),meta['eic']),values,zone,start,end)
            for item in (path,receipt,raw):sources[str(item.relative_to(ROOT))]=digest(item)
            for h,row in enumerate(values):
                if 'B12' in row['reported_types'] and 'B12' not in row['missing_types']:
                    reported[offset+h,j]=row['generation_mwh_by_type']['B12']
            truth=reported[offset:offset+hours,j];valid=np.isfinite(truth)
            for label,model,reservoir,ror in [('accepted_baseline',prior,before,prior_ror),
                                              ('static_geography',candidate,after,candidate_ror)]:
                x=model[offset:offset+hours,j][valid];y=truth[valid]
                rows.append(dict(month=month,zone=zone,model=label,known_hours=int(valid.sum()),
                    model_total_hydro_twh=float(x.sum()/1e6),
                    model_reservoir_twh=float(reservoir[offset:offset+hours,j][valid].sum()/1e6),
                    model_ror_twh=float(ror[offset:offset+hours,j][valid].sum()/1e6),
                    reported_b12_twh=float(y.sum()/1e6),
                    hourly_mae_mw=float(abs(x-y).mean()) if len(x) else None,
                    correlation=float(np.corrcoef(x,y)[0,1]) if len(x)>1 and x.std()>0 and y.std()>0 else None))
        offset+=hours
    assert offset==8760
    for j,zone in enumerate(zones):
        valid=np.isfinite(reported[:,j])
        for label,model,reservoir,ror in [('accepted_baseline',prior,before,prior_ror),
                                          ('static_geography',candidate,after,candidate_ror)]:
            x=model[:,j][valid];y=reported[:,j][valid]
            rows.append(dict(month='annual',zone=zone,model=label,known_hours=int(valid.sum()),
                model_total_hydro_twh=float(x.sum()/1e6),
                model_reservoir_twh=float(reservoir[:,j][valid].sum()/1e6),
                model_ror_twh=float(ror[:,j][valid].sum()/1e6),
                reported_b12_twh=float(y.sum()/1e6),
                hourly_mae_mw=float(abs(x-y).mean()) if len(x) else None,
                correlation=float(np.corrcoef(x,y)[0,1]) if len(x)>1 and x.std()>0 and y.std()>0 else None))
    np.savez_compressed(OUT/'hourly.npz',reported_b12=reported,baseline_total_hydro=prior,
                        static_total_hydro=candidate,baseline_reservoir=before,
                        static_reservoir=after,zones=np.array(zones))
    fig,axes=plt.subplots(4,1,figsize=(12,9),sharex=True)
    for j,(zone,ax) in enumerate(zip(zones,axes)):
        for label,series,color in [('Reported ENTSO-E B12',reported,'black'),
                                   ('Accepted baseline',prior,'#db7343'),
                                   ('Static geography',candidate,'#287aae')]:
            means=np.array([np.nanmean(series[k:k+168,j]) for k in range(0,8760,168)])
            ax.plot(np.arange(len(means)),means,label=label,color=color,linewidth=1.25)
        ax.set_ylabel(zone+' MW');ax.grid(alpha=.15)
    axes[0].legend(ncol=3,fontsize=8)
    axes[-1].set_xlabel('Weeks since 1 January 2025')
    fig.tight_layout();fig.savefig(OUT/'weekly-shape.png',dpi=140);plt.close(fig)
    write(OUT/'summary.json',dict(status='annual_source_replayed_reservoir_validation',
        taxonomy='ENTSO-E B12 Hydro Water Reservoir versus modeled fixed reservoir plus dispatched ROR; Swedish B11 is not separately reported',
        rows=rows,sources=sources,
        limitations=['Reported generation is only a validation target, never availability or an imposed schedule.',
                     'A75/A16 B12 may aggregate ROR in practice; comparison to total modeled hydro is a taxonomy proxy, not certified like-for-like.',
                     'The control changes geography only; its annual stock and inflow were not corrected.']))
    print(json.dumps([r for r in rows if r['month']=='annual']),flush=True)


if __name__=='__main__':run()
