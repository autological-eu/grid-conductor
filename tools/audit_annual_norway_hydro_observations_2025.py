"""Full-year model NO hydro versus source-audited Elhub metered production."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import solar_anchor_bids_2025 as baseline
from run_annual_sweden_geography_2025 import NATIVE
from generation_mix_2025 import ROOT,digest
from solar_country_fit_2025 import write

OUT=ROOT/'data/bidding-zone-source-audit-2025/annual-norway-hydro-v1'
SOURCE=ROOT/'data/bidding-zone-source-audit-2025/elhub-annual-v1'


def run():
    OUT.mkdir(exist_ok=False)
    summary=json.loads((SOURCE/'summary.json').read_text())
    audit=json.loads((SOURCE/'audit.json').read_text())
    assert audit['summary_sha256']==digest(SOURCE/'summary.json')
    assert summary['hourly_sha256']==digest(SOURCE/'hourly.csv')
    pins={str((SOURCE/'summary.json').relative_to(ROOT)):digest(SOURCE/'summary.json'),
          str((SOURCE/'audit.json').relative_to(ROOT)):digest(SOURCE/'audit.json'),
          str((SOURCE/'hourly.csv').relative_to(ROOT)):digest(SOURCE/'hourly.csv'),
          str(NATIVE.relative_to(ROOT)):digest(NATIVE)}
    for entry in summary['sources']:
        import hashlib
        raw=SOURCE/'raw'/(hashlib.sha256(entry['url'].encode()).hexdigest()+'.json')
        assert digest(raw)==entry['sha256']
        pins[str(raw.relative_to(ROOT))]=digest(raw)
    p,s,_=baseline.model()
    zones=[z for z in p['zones'] if z.startswith('NO')]
    assert zones==['NO1','NO2','NO3','NO4','NO5']
    ids=[p['zones'].index(z) for z in zones]
    layout_path=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json'
    layout=json.loads(layout_path.read_text());pins[str(layout_path.relative_to(ROOT))]=digest(layout_path)
    with xr.open_dataset(NATIVE) as n:
        buszone=dict(zip(n.buses_i.values,n.buses_bidding_zone.values))
        gross=np.zeros((8760,5))
        for j,bus in enumerate(n.loads_bus.values):
            zone=str(buszone[bus])
            if zone in zones:gross[:,zones.index(zone)]+=n.loads_t_p_set.values[:,j]
        carrier=n.generators_carrier.values.astype(str)
        genzone=np.array([str(buszone[b]) for b in n.generators_bus.values])
    fixed=gross-s['load'][:,ids]
    if fixed.min() < -1e-4:raise ValueError('Negative source fixed hydro')
    active=json.loads((ROOT/'config/active-research-baseline.json').read_text())
    witness=ROOT/active['witness']['witness']
    assert digest(witness)==active['witness']['witness_sha256']
    pins[str(witness.relative_to(ROOT))]=digest(witness)
    with np.load(witness) as z:dispatch=z['values']
    ror=np.zeros_like(fixed)
    for group,members in enumerate(layout['members']):
        families={str(carrier[i]) for i in members}
        groupzones={str(genzone[i]) for i in members}
        if families=={'ror'} and len(groupzones)==1 and next(iter(groupzones)) in zones:
            ror[:,zones.index(next(iter(groupzones)))]+=dispatch[:,group]
        elif 'ror' in families and any(z in zones for z in groupzones):
            raise ValueError('Mixed Norwegian run-of-river offer')
    frame=pd.read_csv(SOURCE/'hourly.csv')
    reported=np.full((8760,5),np.nan)
    utc=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC').as_unit('ns').to_numpy()
    for j,zone in enumerate(zones):
        rows=frame[frame.zone.eq(zone)].sort_values('utc')
        np.testing.assert_array_equal(pd.to_datetime(rows.utc,utc=True).dt.as_unit('ns').to_numpy(),utc)
        reported[:,j]=rows.hydro_mwh.to_numpy(float)
    total=fixed+ror
    results=[]
    for j,zone in enumerate(zones):
        x=total[:,j];y=reported[:,j]
        assert np.isfinite(y).all()
        results.append(dict(zone=zone,hours=8760,model_hydro_twh=float(x.sum()/1e6),
            model_reservoir_twh=float(fixed[:,j].sum()/1e6),model_ror_twh=float(ror[:,j].sum()/1e6),
            metered_hydro_twh=float(y.sum()/1e6),hourly_mae_mw=float(abs(x-y).mean()),
            correlation=float(np.corrcoef(x,y)[0,1])))
    np.savez_compressed(OUT/'hourly.npz',zones=np.array(zones),reported=reported,model=total,
                        reservoir=fixed,ror=ror)
    fig,axes=plt.subplots(5,1,figsize=(12,10),sharex=True)
    for j,(zone,ax) in enumerate(zip(zones,axes)):
        for label,v,color in [('Elhub metered',reported,'black'),('Accepted baseline',total,'#287aae')]:
            av=np.array([v[k:k+168,j].mean() for k in range(0,8760,168)])
            ax.plot(np.arange(len(av)),av,label=label,color=color,linewidth=1.2)
        ax.set_ylabel(zone+' MW');ax.grid(alpha=.15)
    axes[0].legend(ncol=2,fontsize=8)
    axes[-1].set_xlabel('Weeks since 1 January 2025')
    fig.tight_layout();fig.savefig(OUT/'weekly-shape.png',dpi=140);plt.close(fig)
    write(OUT/'summary.json',dict(status='annual_raw_elhub_hydro_vs_accepted_model',
        zones=results,source_sha256=pins,limitations=[
            'Elhub metered hydro and model fixed reservoir plus dispatched ROR may differ in taxonomy.',
            'Reported production validates the model; it is never used as availability.',
            'The source-audited national demand scope differs from model gross load and is not substituted.']))
    print(json.dumps(results),flush=True)


if __name__=='__main__':run()
