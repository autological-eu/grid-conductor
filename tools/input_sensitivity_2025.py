"""Predeclared one-input sensitivity coefficients, never fitted to power prices."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from hybrid_fixed_hydro_2025 import verified_fuel,FUEL
from thermal_bid_rules import validate_market
from simple_resource_bids import cost_assumptions,THERMAL
from nve_hydro_diagnostics import ROOT,digest

WIND={'onwind','offwind-ac','offwind-dc','offwind-float'}
CASES={'control':{},**{f'{k}_{direction}10':{k:sign*.1}
       for k in ['wind','gas','oil','carbon'] for direction,sign in [('minus',-1),('plus',1)]},
       'all_plus10':dict(wind=.1,gas=.1,oil=.1,carbon=.1)}


def coefficient_change(generators,cost,availability,gas,oil,carbon,assumptions,deltas):
    """Only offer costs/upper bounds change; capacity, GSK and all water stay fixed."""
    if set(deltas)-{'wind','gas','oil','carbon'}:
        raise ValueError('Unknown input perturbation')
    if any(not np.isfinite(x) or abs(x)>.1+1e-12 for x in deltas.values()):
        raise ValueError('Outside predeclared ten-percent range')
    newcost=cost.copy();newav=availability.copy()
    for j,(_,g) in enumerate(generators.iterrows()):
        if g.carrier in WIND and deltas.get('wind',0):
            newav[:,j]=np.minimum(availability[:,j]*(1+deltas['wind']),1.)
        if g.carrier not in THERMAL:
            continue
        if not np.isfinite(g.efficiency) or not 0<g.efficiency<=1:
            raise ValueError('Invalid thermal efficiency')
        extra=carbon*assumptions[g.carrier]['emissions_t_mwh_th']*deltas.get('carbon',0)
        if g.carrier in ['CCGT','OCGT']:extra=extra+gas*deltas.get('gas',0)
        elif g.carrier=='oil':extra=extra+oil*deltas.get('oil',0)
        newcost[:,j]+=extra/g.efficiency
    if not np.isfinite(newcost).all() or not np.isfinite(newav).all() or (newav<0).any():
        raise ValueError('Invalid changed coefficients')
    return newcost,newav


def inputs(n):
    fuel=verified_fuel(FUEL);rows=validate_market(fuel,n.snapshots)
    a,cost_source=cost_assumptions()
    return tuple(np.array([r[key] for r in rows]) for key in ['gas_eur_mwh_th','oil_eur_mwh_th','co2_eur_t']),a,{
        'fuel_sha256':digest(FUEL),'cost_source':cost_source,'fuel_sources':fuel['sources']}


def compile_case(n,cost,cf,fixed,deltas,fuel,assumptions):
    from global_bidding_zone_2025 import compile_global
    nc,na=coefficient_change(n.generators,cost,cf,*fuel,assumptions,deltas)
    n.generators_t.p_max_pu=pd.DataFrame(na,index=n.snapshots,columns=n.generators.index)
    m,off=compile_global(n,nc,fixed,'bidding_zone')
    return m,off,nc,na


def wind_source_check(n,cf):
    """Independent metered generation comparison; never turn dispatch into availability."""
    root=ROOT/'data/bidding-zone-source-audit-2025/elhub-annual-v1'
    s=json.loads((root/'summary.json').read_text());a=json.loads((root/'audit.json').read_text())
    assert a['summary_sha256']==digest(root/'summary.json')
    assert s['hourly_sha256']==digest(root/'hourly.csv')
    # Rehash source responses pinned by the prior independent raw replay.
    import hashlib
    for meta in s['sources']:
        path=root/'raw'/(hashlib.sha256(meta['url'].encode()).hexdigest()+'.json')
        assert digest(path)==meta['sha256']
    frame=pd.read_csv(root/'hourly.csv');frame.utc=pd.to_datetime(frame.utc,utc=True)
    zone=n.generators.bus.map(n.buses.bidding_zone);rows=[]
    availability=cf*n.generators.p_nom.values
    for z in ['NO1','NO2','NO3','NO4','NO5']:
        mask=(n.generators.carrier.isin(WIND)&(zone==z)).values
        model=availability[:,mask].sum(axis=1)
        source=frame[frame.zone==z].sort_values('utc')
        np.testing.assert_array_equal(source.utc.dt.tz_localize(None).values,n.snapshots.values)
        observed=source.wind_mwh.to_numpy(float);known=np.isfinite(observed)
        if len(source)!=8760 or not known.any():raise ValueError('Missing wind observation calendar')
        corr=float(np.corrcoef(model[known],observed[known])[0,1]) if model[known].std()>1e-9 and observed[known].std()>1e-9 else None
        excess=np.maximum(observed[known]-model[known],0)
        rows.append(dict(zone=z,known_hours=int(known.sum()),capacity_mw=float(n.generators.p_nom.values[mask].sum()),
            modeled_available_twh=float(model[known].sum()/1e6),metered_generation_twh=float(observed[known].sum()/1e6),
            shape_correlation=corr,hours_metered_above_modeled_available=int((excess>1.).sum()),
            energy_metered_above_modeled_available_twh=float(excess.sum()/1e6)))
    return dict(source_summary_sha256=digest(root/'summary.json'),source_csv_sha256=digest(root/'hourly.csv'),
        source_audit_sha256=digest(root/'audit.json'),regions=rows,
        limitations=s['limitations']+['Available energy may exceed generation due to curtailment; their difference is not a measured wind error.',
            'Above-availability intervals flag inconsistent scope/fleet/profile, not proven missing capacity.',
            'Tiny NO5 observed wind volumes cannot support a robust shape-correlation interpretation.'])
