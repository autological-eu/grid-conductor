"""Explicit final-48h mode-selection exception; all other daily rules unchanged.

A short network prepass uses unchanged bid prices and physical limits, with
charge/discharge volumes available. Only a strictly optimal, cycling-free primal
may select exclusive submitted storage directions. This is a terminal settlement
policy, not arithmetic-only bidding or guaranteed future network viability.
"""
import time
import numpy as np
import highspy
from simple_resource_bids import storage_bids as arithmetic_bids
from simple_daily_market import daily_lp
from daily_market_clearing import make_solver, residual, TOL

WINDOW_HOURS = 48


def select_modes(charge, discharge, charge_limit, discharge_limit, tolerance=1e-6):
    """Reject loss cycles before choosing exclusive power offers."""
    if not np.isfinite(charge).all() or not np.isfinite(discharge).all():
        raise ValueError('Nonfinite terminal mode witness')
    if np.any((charge > tolerance) & (discharge > tolerance)):
        raise ValueError('Terminal mode prepass has simultaneous cycling')
    c = np.where(charge > tolerance, charge_limit, 0.)
    d = np.where(discharge > tolerance, discharge_limit, 0.)
    return c, d


def storage_bids(n, m, start, end, current, terminal, prepared, settings):
    begin = time.perf_counter()
    bids = arithmetic_bids(n, m, start, end, current, terminal, prepared, settings)
    if len(prepared['forecast']) - start > WINDOW_HOURS:
        return bids
    relaxed = dict(bids)
    relaxed['charge_max'] = np.tile(prepared['charge_limit'], (end-start, 1))
    relaxed['discharge_max'] = np.tile(prepared['discharge_limit'], (end-start, 1))
    lp = daily_lp(n, m, start, end, current, terminal, relaxed)
    solver = make_solver(lp, 60, 'ipm'); solver.run()
    if solver.getModelStatus() != highspy.HighsModelStatus.kOptimal:
        raise ValueError('Terminal mode prepass not optimal: ' + str(solver.getModelStatus()))
    values = np.asarray(solver.getSolution().col_value).reshape(end-start, lp['width'])
    error = residual(lp, values.ravel())
    if error > TOL:
        raise ValueError('Terminal mode prepass physical replay failed')
    nb = lp['nb']; ns = lp['ns']
    charge, discharge = select_modes(values[:, nb:nb+ns], values[:, nb+ns:nb+2*ns],
                                     prepared['charge_limit'], prepared['discharge_limit'])
    for j, (_, row) in enumerate(n.storage_units.iterrows()):
        if row.carrier == 'hydro':
            continue
        bids['charge_max'][:, j] = charge[:, j]
        bids['discharge_max'][:, j] = discharge[:, j]
        bids['operators'][j]['terminal_network_mode_selection'] = True
        bids['operators'][j]['mode_selection_window_hours'] = WINDOW_HOURS
    # Retain the prepass primal for exact policy reproduction and provenance.
    bids['terminal_mode_witness'] = values
    bids['seconds'] = time.perf_counter() - begin
    return bids
