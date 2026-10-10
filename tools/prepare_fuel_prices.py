"""Compile observed monthly benchmarks into explicit hourly research inputs.

Requires explicit heating-value and crude-proxy assumptions. No inferred daily
fluctuations, missing-month filling, or historical carbon-price fabrication.
Raw provider files remain ignored; output is compatible with --fuel-prices.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

WB_URL = 'https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx'
ECB_URL = 'https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?startPeriod=2025-01-01&endPeriod=2025-12-31&format=csvdata'
MMBTU_MWH = 0.2930710701722222


def positive(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('Positive finite conversion assumption required')
    return value


def compile_prices(workbook, exchange, year, gas_basis_multiplier,
                   oil_mwh_barrel, carbon):
    if year != 2025:
        raise ValueError('This provenance configuration currently supports 2025 only')
    import pandas as pd
    from thermal_bid_rules import validate_market
    multiplier = positive(gas_basis_multiplier)
    heat = positive(oil_mwh_barrel)
    carbon = float(carbon)
    if not math.isfinite(carbon) or carbon < 0:
        raise ValueError('Finite nonnegative carbon assumption required')
    prices = pd.read_excel(workbook, sheet_name='Monthly Prices', header=4)
    fx = pd.read_csv(exchange, skipinitialspace=True)
    if not (fx['KEY'] == 'EXR.D.USD.EUR.SP00.A').all():
        raise ValueError('Expected ECB USD per EUR series')
    fx = fx.rename(columns={'TIME_PERIOD': 'Date', 'OBS_VALUE': 'USD'})
    fx['Date'] = pd.to_datetime(fx['Date'], errors='raise')
    if fx['Date'].duplicated().any():
        raise ValueError('Duplicate ECB observation date')
    monthly = []
    for month in range(1, 13):
        rows = prices[prices.iloc[:, 0] == f'{year}M{month:02d}']
        quotes = pd.to_numeric(fx.loc[(fx.Date.dt.year == year) &
                                     (fx.Date.dt.month == month), 'USD'], errors='raise')
        if len(rows) != 1 or quotes.empty or not quotes.map(lambda x: math.isfinite(x) and x > 0).all():
            raise ValueError('Missing/duplicate benchmark month or invalid FX')
        # Mean reciprocal daily ECB quotes: EUR per USD, not reciprocal mean.
        eur_usd = float((1 / quotes).mean())
        gas = positive(rows.iloc[0]['Natural gas, Europe'])
        oil = positive(rows.iloc[0]['Crude oil, Brent'])
        monthly.append(dict(month=month, gas_usd_mmbtu=gas, brent_usd_barrel=oil,
                            eur_per_usd=eur_usd, fx_observations=len(quotes),
                            gas_eur_mwh_th=gas * eur_usd / MMBTU_MWH * multiplier,
                            oil_eur_mwh_th=oil * eur_usd / heat))
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    hours = []
    while start < end:
        row = monthly[start.month - 1]
        hours.append(dict(utc=start.isoformat().replace('+00:00', 'Z'),
                          gas_eur_mwh_th=row['gas_eur_mwh_th'],
                          oil_eur_mwh_th=row['oil_eur_mwh_th'], co2_eur_t=carbon))
        start += timedelta(hours=1)
    result = dict(sources={
        'gas_eur_mwh_th': 'World Bank monthly TTF benchmark; ECB monthly mean reciprocal daily FX; explicit heating-basis multiplier',
        'oil_eur_mwh_th': 'World Bank monthly Brent crude proxy, not delivered oil product; ECB FX; explicit thermal content',
        'co2_eur_t': f'Constant assumption EUR {carbon}/t; not observed EU ETS prices'},
        assumptions=dict(gas_basis_multiplier=multiplier, oil_mwh_th_per_barrel=heat,
                         co2_eur_t=carbon, temporal_resolution='Monthly values repeated over UTC hours; perfect-forecast retrospective inputs'),
        provenance=[dict(url=url, sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
                    for path, url in [(workbook, WB_URL), (exchange, ECB_URL)]],
        monthly=monthly, hours=hours)
    validate_market(result, [row['utc'] for row in hours])
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--world-bank', required=True)
    p.add_argument('--ecb', required=True)
    p.add_argument('--year', type=int, default=2025)
    p.add_argument('--gas-basis-multiplier', type=float, required=True,
                   help='Explicit benchmark thermal-basis to efficiency-basis multiplier; 1 assumes identical bases')
    p.add_argument('--oil-mwh-th-per-barrel', type=float, required=True)
    p.add_argument('--carbon-eur-t', type=float, required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    output = Path(a.output)
    if output.exists():
        raise FileExistsError('Use a fresh output path')
    result = compile_prices(a.world_bank, a.ecb, a.year, a.gas_basis_multiplier,
                            a.oil_mwh_th_per_barrel, a.carbon_eur_t)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(f'Prepared {len(result["hours"])} hours from 12 observed monthly benchmarks')


if __name__ == '__main__':
    main()
