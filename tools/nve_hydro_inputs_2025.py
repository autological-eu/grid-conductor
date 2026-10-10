"""Independent NVE weather-driven inflow and observed stock compiler.

NVE net usable-inflow GWh and gross stock energy are treated as electrical-energy
equivalents. This reporting-basis assumption is explicit, not a turbine-efficiency
change. Generation-derived inflow and Elhub production never enter this compiler.
"""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from hourly_renewable_estimates import digest

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'data/hydro-observations-2025/nve-hydrology-release'
STOCK = ROOT / 'data/bidding-zone-source-audit-2025/nve-reservoir-history.json'
HBV = 'Nyttbart tilsig HBV (brukes før 2015 og til min/maks/gj.snitt)'
METHOD_URL = 'https://www.nve.no/energi/analyser-og-statistikk/hydrologiske-data-til-kraftsituasjonsrapporten/'


def utc_week(year, week):
    start = dt.datetime.combine(dt.date.fromisocalendar(year, week, 1), dt.time(), ZoneInfo('Europe/Oslo'))
    end = start + dt.timedelta(days=7)
    return pd.Timestamp(start).tz_convert('UTC'), pd.Timestamp(end).tz_convert('UTC')


def compile_inputs(weather):
    path = RELEASE / 'table.xlsx'
    receipt = json.loads((RELEASE / 'receipt.json').read_text())
    sm = json.loads(STOCK.with_name('nve-reservoir-history.meta.json').read_text())
    if digest(path) != receipt['sha256'] or digest(STOCK) != sm['sha256']:
        raise ValueError('Changed NVE source')
    frame = pd.read_excel(path)
    selected = frame[(frame['Område'].isin(['NO', 'NO1', 'NO2', 'NO3', 'NO4', 'NO5'])) &
                     ((frame['År'] == 2025) | ((frame['År'] == 2026) & (frame.Uke == 1)))].copy()
    if selected.duplicated(['Område', 'År', 'Uke']).any():
        raise ValueError('Duplicate NVE weeks')
    hours = pd.date_range('2025-01-01', periods=8760, freq='h', tz='UTC')
    edges = pd.date_range('2025-01-01', periods=8761, freq='h', tz='UTC')
    weather = np.asarray(weather, dtype=float)
    if weather.shape != (8760,) or not np.isfinite(weather).all() or (weather < 0).any():
        raise ValueError('Invalid weather shape')
    inflow = np.full(8760, np.nan)
    weekly = []
    for _, row in selected[selected['Område'] == 'NO'].iterrows():
        start, end = utc_week(int(row['År']), int(row.Uke))
        mask = (hours >= start) & (hours < end)
        energy = float(row[HBV]) * 1000  # GWh -> MWh electrical equivalent
        if not np.isfinite(energy) or energy < 0:
            raise ValueError('Missing/negative weather-driven inflow')
        if mask.any():
            complete = hours[mask][0] == start and hours[mask][-1] + pd.Timedelta(hours=1) == end
            if complete:
                weights = weather[mask]
                if weights.sum() <= 0:
                    raise ValueError('Zero weather shape for a positive inflow week')
                inflow[mask] = energy * weights / weights.sum()
            else:
                # Do not concentrate a full weekly volume into a partial year week.
                inflow[mask] = energy / ((end - start).total_seconds() / 3600)
            weekly.append(dict(year=int(row['År']), week=int(row.Uke), start_utc=start.isoformat(),
                               end_utc=end.isoformat(), energy_mwh=energy, full_week_in_year=bool(complete)))
    if not np.isfinite(inflow).all():
        raise ValueError('Incomplete NVE calendar')
    raw = json.loads(STOCK.read_text())
    national = sorted((r for r in raw if r['omrType'] == 'NO' and r['omrnr'] == 0 and
                       '2024-12-15' <= r['dato_Id'] <= '2026-01-15'), key=lambda r: r['dato_Id'])
    # NVE Sunday-dated measurements refer to Sunday 24:00 local time.
    times = pd.DatetimeIndex([pd.Timestamp(r['dato_Id']).tz_localize('Europe/Oslo') + pd.DateOffset(days=1)
                              for r in national]).tz_convert('UTC')
    if times[0] > edges[0] or times[-1] < edges[-1] or times.has_duplicates:
        raise ValueError('Unbracketed reservoir boundaries')
    energy = np.array([r['fylling_TWh'] * 1e6 for r in national])
    caps = np.array([r['kapasitet_TWh'] * 1e6 for r in national])
    if not np.isfinite(energy).all() or (energy < 0).any() or (energy > caps).any():
        raise ValueError('Invalid observed stock')
    # Require constant capacity to avoid inventing a commissioning trajectory.
    if np.ptp(caps) > 1e-4:
        raise ValueError('Changing NVE storage capacity needs dated treatment')
    target = np.interp(edges.asi8.astype(float), times.asi8.astype(float), energy)
    meta = dict(source=receipt, stock_source=sm, compiler_sha256=digest(Path(__file__)),
                source_column=HBV, method_url=METHOD_URL, calendar_inflow_twh=float(inflow.sum()/1e6),
                iso_2025_inflow_twh=float(selected[(selected['Område']=='NO') & (selected['År']==2025)][HBV].sum()/1000),
                initial_electrical_stock_twh=float(target[0]/1e6), final_electrical_stock_twh=float(target[-1]/1e6),
                storage_electrical_capacity_twh=float(caps[0]/1e6), weeks=weekly,
                limitations=['Revised HBV model estimates, not measured plant inflows.',
                             'ERA5 shape distributes complete weekly volumes; partial boundary weeks use uniform rates.',
                             'Gross stock energy and net usable inflow use an explicit common electrical-equivalent basis.',
                             'Country pooling and linear stock-boundary interpolation are approximations, not NO1–NO5 reservoir routing.'])
    return inflow, target, caps[0], meta
