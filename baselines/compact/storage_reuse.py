"""Reusable HiGHS template for the same fixed-horizon storage/network LP.

This is a performance experiment against ``storage.clear_window``. It keeps
all physical, battery-stock and no-emergency gates; the accepted annual source
and saved storage trial are untouched.
"""
from __future__ import annotations

import time

import highspy
import numpy as np
from scipy.sparse import block_diag, coo_matrix, hstack, vstack

from .lp import ratings_at
from .storage import Battery


class ReusableBatteryWindow:
    """One battery, one fixed-size horizon, changing inputs and starting stock."""

    def __init__(self, model, costs, battery: Battery, hours: int):
        if hours < 24 or hours % 24:
            raise ValueError('Expected a positive whole-day horizon')
        zones = list(map(str, model['zones']))
        if battery.zone not in zones or battery.power_mw <= 0 or battery.energy_mwh <= 0:
            raise ValueError('Invalid battery declaration')
        if not (0 < battery.charge_efficiency <= 1 and
                0 < battery.discharge_efficiency <= 1 and
                0 <= battery.initial_mwh <= battery.energy_mwh and
                0 <= battery.terminal_mwh <= battery.energy_mwh and
                battery.throughput_eur_mwh >= 0):
            raise ValueError('Invalid battery stock, efficiency or cost')
        self.model, self.costs, self.battery, self.hours = model, costs, battery, hours
        self.ng, self.nl, self.nz = (int(model[key]) for key in ('ng', 'nl', 'nz'))
        self.nr, self.nc = model['A'].shape
        self.zone = zones.index(battery.zone)
        self.nbase = hours * self.nc
        self.ncols = self.nbase + 3 * hours
        self.nrows = hours * self.nr + hours
        begun = time.perf_counter()
        source = block_diag([model['A'].tocsc()] * hours, format='csc')
        rows, cols, data = [], [], []
        for t in range(hours):
            rows.extend([t * self.nr + self.zone] * 2)
            cols.extend([3*t, 3*t+1])
            data.extend([-1., 1.])
        injections = coo_matrix((data, (rows, cols)),
                                shape=(hours*self.nr, 3*hours)).tocsc()
        network = hstack([source, injections], format='csc')
        rows, cols, data = [], [], []
        for t in range(hours):
            rows.extend([t, t, t])
            cols.extend([self.nbase+3*t, self.nbase+3*t+1, self.nbase+3*t+2])
            data.extend([-battery.charge_efficiency,
                         1/battery.discharge_efficiency, 1.])
            if t:
                rows.append(t)
                cols.append(self.nbase+3*(t-1)+2)
                data.append(-1.)
        stock = coo_matrix((data, (rows, cols)), shape=(hours, self.ncols)).tocsc()
        self.matrix = vstack([network, stock], format='csc')
        self.assembly_seconds = time.perf_counter() - begun
        self.highs = highspy.Highs()
        self.highs.setOptionValue('output_flag', False)
        self.highs.setOptionValue('threads', 1)
        self.highs.setOptionValue('solver', 'simplex')
        self.highs.setOptionValue('primal_feasibility_tolerance', 1e-8)
        self.highs.setOptionValue('dual_feasibility_tolerance', 1e-8)
        self._initialized = False

    def _arrays(self, start: int, initial_mwh: float):
        if (start < 0 or start + self.hours > len(self.model['availability']) or
                not 0 <= initial_mwh <= self.battery.energy_mwh):
            raise ValueError('Invalid rolling window or starting stock')
        c = np.zeros(self.ncols)
        lower = np.full(self.ncols, -np.inf)
        upper = np.full(self.ncols, np.inf)
        row_lower = np.zeros(self.nrows)
        row_upper = np.zeros(self.nrows)
        for t in range(self.hours):
            h, col, row = start+t, t*self.nc, t*self.nr
            c[col:col+self.ng] = self.costs[h]
            lower[col:col+self.ng] = 0.
            upper[col:col+self.ng] = self.model['availability'][h]
            lower[col+self.ng:col+self.ng+self.nl] = self.model['link_min'][h]
            upper[col+self.ng:col+self.ng+self.nl] = self.model['link_max'][h]
            k = self.nz + len(self.model['islands'])
            rhs = np.r_[self.model['load'][h], self.model['island_rhs'][h]]
            row_lower[row:row+k] = rhs
            row_upper[row:row+k] = rhs
            rating = ratings_at(self.model, h)
            row_lower[row+k:row+self.nr] = -rating - self.model['flow'][h]
            row_upper[row+k:row+self.nr] = rating - self.model['flow'][h]
            bcol = self.nbase + 3*t
            c[bcol:bcol+2] = self.battery.throughput_eur_mwh
            lower[bcol:bcol+3] = 0.
            upper[bcol:bcol+3] = [self.battery.power_mw,
                                  self.battery.power_mw, self.battery.energy_mwh]
        end_stock = self.nbase + 3*(self.hours-1) + 2
        lower[end_stock] = upper[end_stock] = self.battery.terminal_mwh
        row_lower[self.hours*self.nr] = row_upper[self.hours*self.nr] = initial_mwh
        return c, lower, upper, row_lower, row_upper

    def clear(self, start: int, initial_mwh: float):
        begun = time.perf_counter()
        c, lower, upper, row_lower, row_upper = self._arrays(start, initial_mwh)
        highs = self.highs
        if not self._initialized:
            lp = highspy.HighsLp()
            lp.num_col_, lp.num_row_ = self.ncols, self.nrows
            lp.col_cost_, lp.col_lower_, lp.col_upper_ = c, lower, upper
            lp.row_lower_, lp.row_upper_ = row_lower, row_upper
            lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
            lp.a_matrix_.start_ = self.matrix.indptr
            lp.a_matrix_.index_ = self.matrix.indices
            lp.a_matrix_.value_ = self.matrix.data
            highs.passModel(lp)
            self._initialized = True
        else:
            cols = np.arange(self.ncols, dtype=np.int32)
            rows = np.arange(self.nrows, dtype=np.int32)
            highs.changeColsCost(self.ncols, cols, c)
            highs.changeColsBounds(self.ncols, cols, lower, upper)
            highs.changeRowsBounds(self.nrows, rows, row_lower, row_upper)
        update_seconds = time.perf_counter() - begun
        begun = time.perf_counter()
        highs.setOptionValue('time_limit', highs.getRunTime() + 120.)
        highs.run()
        if highs.getModelStatus() != highspy.HighsModelStatus.kOptimal:
            highs.clearSolver()
            highs.setOptionValue('time_limit', highs.getRunTime() + 120.)
            highs.run()
        if highs.getModelStatus() != highspy.HighsModelStatus.kOptimal:
            raise RuntimeError(f'Window {start}: {highs.modelStatusToString(highs.getModelStatus())}')
        solve_seconds = time.perf_counter() - begun
        solution = highs.getSolution()
        x = np.asarray(solution.col_value)
        actual = self.matrix @ x
        residual = max(float(np.maximum(row_lower - actual, 0).max(initial=0)),
                       float(np.maximum(actual - row_upper, 0).max(initial=0)),
                       float(np.maximum(lower - x, 0).max(initial=0)),
                       float(np.maximum(x - upper, 0).max(initial=0)))
        if residual > 1e-4:
            raise ValueError(f'Window {start}: primal residual {residual}')
        values = x[:self.nbase].reshape(self.hours, self.nc)
        if np.any(values[:, :self.ng][:, self.model['emergency_mask']].sum(axis=1) > 1e-6):
            raise ValueError(f'Window {start}: emergency dispatch')
        storage = x[self.nbase:].reshape(self.hours, 3)
        if np.any(np.minimum(storage[:, 0], storage[:, 1]) > 1e-5):
            raise ValueError(f'Window {start}: simultaneous charging and discharging')
        return dict(objective_eur=float(highs.getObjectiveValue()),
                    values=values,
                    zonal_prices=np.asarray(solution.row_dual)[:self.hours*self.nr]
                    .reshape(self.hours, self.nr)[:, :self.nz],
                    storage=storage, maximum_primal_residual=residual,
                    update_seconds=update_seconds, solve_seconds=solve_seconds)
