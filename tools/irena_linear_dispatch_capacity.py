"""IRENA year-end wind/PV capacity trajectories on original spatial weather shapes."""
import json
from pathlib import Path
import numpy as np
from hourly_renewable_estimates import digest
ROOT=Path(__file__).resolve().parents[1]
FAMILIES={'Solar photovoltaic':{'solar','solar-hsat'},'Wind energy':{'onwind','offwind-ac','offwind-dc','offwind-float'}}

def trajectory(lo,hi,hours=8760):
    if hours!=8760 or not np.isfinite([lo,hi]).all() or min(lo,hi)<0:
        raise ValueError('Finite nonnegative capacity endpoints and 8760 hours required')
    return lo+(hi-lo)*np.arange(hours)/hours

def apply(n,records):
    if len(n.snapshots)!=8760:raise ValueError('Full-year source required')
    bank={}
    for r in records:
        key=(r['country'],r['technology'])
        if key in bank:raise ValueError('Duplicate IRENA row')
        bank[key]=r
    original=n.get_switchable_as_dense('Generator','p_max_pu').copy()
    profiles=original.copy();countries=n.generators.bus.map(n.buses.country);audit=[]
    for country in sorted(set(n.buses.country)):
        for technology,carriers in FAMILIES.items():
            ids=n.generators.index[(countries==country)&n.generators.carrier.isin(carriers)]
            source=float(n.generators.loc[ids,'p_nom'].sum());row=bank.get((country,technology))
            item=dict(country=country,technology=technology,source_capacity_mw=source)
            if row is None:
                item['status']='missing_irena_endpoints_original_retained';audit.append(item);continue
            lo=row['capacity_2024']['mw'];hi=row['capacity_2025']['mw'];capacity=trajectory(lo,hi)
            item.update(capacity_2024=row['capacity_2024'],capacity_2025=row['capacity_2025'])
            if source<=0:
                item['status']='no_original_weather_fleet_original_retained';audit.append(item);continue
            values=original.loc[:,ids].values*n.generators.loc[ids,'p_nom'].values
            adjusted=values*(capacity/source)[:,None]
            profiles.loc[:,ids]=original.loc[:,ids].values*(capacity/source)[:,None]
            # Preserve original within-country technology/spatial weights; only fleet scale changes.
            np.testing.assert_allclose((n.generators.loc[ids,'p_nom'].values[None,:]*(capacity/source)[:,None]).sum(axis=1),capacity,rtol=1e-12,atol=1e-7)
            item.update(status='linear_capacity_applied',first_hour_capacity_mw=float(capacity[0]),last_hour_capacity_mw=float(capacity[-1]),original_available_twh=float(values.sum()/1e6),adjusted_available_twh=float(adjusted.sum()/1e6))
            audit.append(item)
    if not np.isfinite(profiles.values).all() or (profiles.values<0).any():raise ValueError('Invalid adjusted availability')
    n.generators_t.p_max_pu=profiles
    return audit

def load_and_apply(n):
    path=ROOT/'public/research/irena-capacity-2025/summary.json';record=json.loads(path.read_text())
    pdf=ROOT/'data/pypsa-eur/irena-capacity-2026/capacity.pdf'
    if digest(pdf)!=record['irena_pdf_sha256']:raise ValueError('IRENA PDF hash mismatch')
    return dict(irena_summary_sha256=digest(path),irena_pdf_sha256=digest(pdf),producer_sha256=digest(__file__),source_url=record['source_url'],rule='C(t)=C_end_2024+(C_end_2025-C_end_2024)*t/8760; t=0..8759 UTC',audit=apply(n,record['irena_rows']),limitations=['Wind/PV only; parent total wind and total PV used once, not summed with subcategories','Original weather/technology/location shares retained, including their biases','Missing endpoints or missing source weather fleets retain original inputs with explicit status','Hydro, PHS, bioenergy, geothermal, marine and fossil/nuclear unchanged','Static original GSK retained to isolate capacity change; no weather recalculation or observed commissioning dates','p_max_pu encodes original weather shape times capacity multiplier and can exceed 1 relative to original p_nom'])
