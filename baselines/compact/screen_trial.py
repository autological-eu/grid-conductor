"""Small reproducible fixed-input trial of the independent-corridor screen.

This is a numerical diagnostic, not an accepted annual scenario estimator.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from .evaluation import FIT, TIMEZONES, physical_lp, saved_annual
from .network import transport_corridors
from .recovery import RecoveredTransportMarket
from .source import grouped_fit_inputs


def run():
    schema, data, _ = grouped_fit_inputs()
    edges, lower, upper = transport_corridors(schema['zones'], data)
    market = RecoveredTransportMarket(
        schema['zones'], schema['groups'], lower, upper, edges,
        data['capacity'] / 1000, data['source_cost'], data['load'] / 1000)
    with np.load(FIT / 'month-01/curves.npz') as archive:
        weights = archive['weights']
    rows = []
    for length in (24, 168):
        hours = np.arange(length)
        utc = pd.Timestamp('2025-01-01', tz='UTC') + pd.to_timedelta(hours, unit='h')
        clocks = np.column_stack([
            np.asarray(utc.tz_convert(TIMEZONES[group['zone'][:2]]).hour)
            for group in schema['groups']])
        theta = weights[clocks, np.arange(market.ng)]
        began = time.perf_counter()
        row = dict(hours=length, zones=market.nz, corridors=len(edges))
        try:
            result = market.solve(theta, hours)
            row.update(status='passed', solve_seconds=time.perf_counter() - began,
                       certificate=result['certificate'],
                       maximum_newton_iterations=int(result['iterations'].max()),
                       coordinate_recoveries=int(result['coordinate_recoveries']))
            if length == 24:
                lp = physical_lp()
                _, witness = saved_annual()
                lp_prices = witness['row_duals'][:length, :lp['nz']]
                row['mean_abs_price_gap_to_physical_lp_eur_mwh'] = float(
                    np.abs(result['prices'] - lp_prices).mean())
                row['observed_price_mae_eur_mwh'] = float(np.nanmean(
                    np.abs(result['prices'] - data['observed_prices'][:length])))
        except RuntimeError as error:
            row.update(status='failed', solve_seconds=time.perf_counter() - began,
                       failure=str(error))
        rows.append(row)
    return rows


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
