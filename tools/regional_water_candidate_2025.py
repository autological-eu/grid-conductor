"""Fresh regional-NVE fixed-water candidate; no electricity-price input or tuning.

Regional reservoirs remain pooled within each zone. HBV usable inflow is split
between reservoir/ROR by source turbine MW, an explicit approximation. Retain
the baseline seasonal output shape, adjusted by a water-only L1 schedule.
"""
import json
import numpy as np
import pandas as pd
import xarray as xr
from nve_hydro_inputs_2025 import ROOT, RELEASE, STOCK, HBV, utc_week
from hourly_renewable_estimates import digest
from update_norway_hydro_2025 import schedule

ZONES = ['NO1', 'NO2', 'NO3', 'NO4', 'NO5']
WEATHER = ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/profile_hydro.nc'


def distribute_weekly(frame, zone, weather, hours):
    inflow = np.full(len(hours), np.nan)
    rows = frame[frame['Område'] == zone]
    if rows.duplicated(['År', 'Uke']).any():
        raise ValueError('Duplicate regional inflow weeks')
    for _, row in rows.iterrows():
        start, end = utc_week(int(row['År']), int(row.Uke))
        mask = (hours >= start) & (hours < end)
        if not mask.any():
            continue
        energy = float(row[HBV])*1000
        if not np.isfinite(energy) or energy < 0:
            raise ValueError('Invalid regional HBV energy')
        full = hours[mask][0] == start and hours[mask][-1]+pd.Timedelta(hours=1) == end
        if full:
            weights = weather[mask]
            if weights.sum() <= 0:
                raise ValueError('Missing positive weekly weather shape')
            inflow[mask] = energy*weights/weights.sum()
        else:
            inflow[mask] = energy/((end-start).total_seconds()/3600)
    if not np.isfinite(inflow).all():
        raise ValueError('Incomplete regional inflow calendar')
    return inflow


def stock_series(raw, number, edges):
    rows = sorted((r for r in raw if r['omrType'] == 'EL' and r['omrnr'] == number
                   and '2024-12-15' <= r['dato_Id'] <= '2026-01-15'), key=lambda r:r['dato_Id'])
    times = pd.DatetimeIndex([pd.Timestamp(r['dato_Id']).tz_localize('Europe/Oslo')
                             +pd.DateOffset(days=1) for r in rows]).tz_convert('UTC')
    if len(times) < 2 or times.has_duplicates or times[0] > edges[0] or times[-1] < edges[-1]:
        raise ValueError('Unbracketed regional stocks')
    energy = np.array([r['fylling_TWh']*1e6 for r in rows])
    caps = np.array([r['kapasitet_TWh']*1e6 for r in rows])
    if not np.isfinite(energy+caps).all() or (energy < 0).any() or (energy > caps).any() or np.ptp(caps) > 1e-4:
        raise ValueError('Invalid/changing regional stock capacity')
    return np.interp(edges.asi8.astype(float), times.asi8.astype(float), energy), float(caps[0])


def source_inputs():
    workbook = RELEASE/'table.xlsx'
    receipt = json.loads((RELEASE/'receipt.json').read_text())
    stock_receipt = json.loads(STOCK.with_name('nve-reservoir-history.meta.json').read_text())
    assert digest(workbook) == receipt['sha256'] and digest(STOCK) == stock_receipt['sha256']
    frame = pd.read_excel(workbook)
    frame = frame[(frame['År'] == 2025)|((frame['År'] == 2026)&(frame.Uke == 1))]
    hours = pd.date_range('2025-01-01', periods=8760, freq='h', tz='UTC')
    edges = pd.date_range('2025-01-01', periods=8761, freq='h', tz='UTC')
    with xr.open_dataarray(WEATHER) as ds:
        np.testing.assert_array_equal(ds.time.values, hours.tz_localize(None).values)
        weather = ds.sel(countries='NO').values.copy()
    raw = json.loads(STOCK.read_text())
    stocks, capacities = zip(*(stock_series(raw, i+1, edges) for i in range(5)))
    inflow = np.column_stack([distribute_weekly(frame,z,weather,hours) for z in ZONES])
    return inflow, np.column_stack(stocks), np.array(capacities), {
        str(p.relative_to(ROOT)):digest(p) for p in [workbook, STOCK, WEATHER]}


def allocation(n, original, mapping):
    """Retain baseline plant shares/turbine MW; do not relocate turbines."""
    su = original.storage_units.query("carrier=='hydro'")
    turbine = pd.Series(0., index=n.buses.index)
    for row in mapping['allocation']:
        if row['component'] != 'FixedReservoir':
            continue
        unit = su.loc[row['name']]
        if original.buses.loc[unit.bus, 'country'] != 'NO':
            continue
        if unit.standing_loss != 0 or abs(unit.efficiency_dispatch-.9) > 1e-12:
            raise ValueError('Unsupported regional turbine efficiency/loss')
        for bus, share in row['shares'].items():
            turbine[bus] += float(unit.p_nom)*share
    return turbine


def prepare(n, fixed, original, mapping):
    inflow, stocks, capacities, sources = source_inputs()
    turbine = allocation(n, original, mapping)
    newfixed = fixed.copy()
    outputs, inventories, spills, reservoir_inflows, plans, details = [], [], [], [], [], []
    for j, zone in enumerate(ZONES):
        buses = n.buses.index[n.buses.bidding_zone == zone]
        mw = float(turbine.loc[buses].sum())
        ids = n.generators.index[(n.generators.carrier=='ror')&n.generators.bus.isin(buses)]
        rormw = float(n.generators.loc[ids].p_nom.sum())
        if mw <= 0:
            raise ValueError('No regional reservoir turbine '+zone)
        fraction = mw/(mw+rormw)
        natural = inflow[:,j]*fraction
        budget = float(natural.sum()+stocks[0,j]-stocks[-1,j])
        if budget < 0:
            raise ValueError('Negative regional water budget')
        reference = fixed.loc[:,buses].sum(axis=1).values
        if reference.sum() <= 0:
            raise ValueError('Missing regional seasonal reference')
        target = reference*budget/reference.sum()
        power, state, spill, plan = schedule(natural,stocks[0,j],stocks[-1,j],capacities[j],
                                             np.zeros(8760),np.full(8760,mw),target)
        weights = turbine.loc[buses]/mw
        newfixed.loc[:,buses] = power[:,None]*weights.values
        if rormw:
            n.generators_t.p_max_pu.loc[:,ids] = np.minimum(inflow[:,j,None]*(1-fraction)/rormw,1.)
        outputs.append(power);inventories.append(state);spills.append(spill);reservoir_inflows.append(natural);plans.append(plan)
        details.append(dict(zone=zone,turbine_mw=mw,ror_mw=rormw,reservoir_inflow_share=fraction,
                            inflow_twh=float(inflow[:,j].sum()/1e6),reservoir_output_twh=float(power.sum()/1e6),
                            spill_twh=float(spill.sum()/1e6),initial_stock_twh=float(stocks[0,j]/1e6),
                            closing_stock_twh=float(stocks[-1,j]/1e6),capacity_twh=float(capacities[j]/1e6)))
    water = dict(power=np.column_stack(outputs),inventory=np.column_stack(inventories),
                 spill=np.column_stack(spills),inflow=np.column_stack(reservoir_inflows),
                 initial=stocks[0],terminal=stocks[-1],capacity=capacities,
                 turbine=np.array([d['turbine_mw'] for d in details]))
    return newfixed,water,dict(sources=sources,regions=details,schedules=plans,
        limitations=['Regional pooled reservoirs; no catchment/cascade routing.',
            'HBV usable inflow split reservoir/ROR by turbine capacity; not measured plant inflow.',
            'National ERA5 hourly shape retained within regional weekly HBV totals.',
            'Electrical-equivalent water balance; stored quantities equal these values divided by eta=0.9.',
            'Fixed seasonal schedule from source reference; no price fitting or daily adaptive hydro.',
            'Water-only schedule is not guaranteed network feasible; failed hours must remain visible.'])
