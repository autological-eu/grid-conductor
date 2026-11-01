"""DeepOPF-style zonal prediction followed by an exact transport projection.

Research pilot only: trained on retained January–March LP dispatch, tested on
April hours. The model predicts zonal generation; a small LP repairs its zone
balances and independent corridor bounds. It is not an offer or storage solver.
"""
from __future__ import annotations

import json
import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix, hstack, vstack
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from .evaluation import physical_lp, saved_annual
from .network import transport_corridors
from .source import grouped_fit_inputs


def zone_totals(values, zone_index, nz):
    out = np.zeros((len(values), nz))
    for zone in range(nz):
        out[:, zone] = values[:, zone_index == zone].sum(axis=1)
    return out


def projection_matrix(nz, edges):
    ne = len(edges)
    incidence = np.zeros((nz, ne))
    for k, (start, end) in enumerate(edges):
        incidence[start, k] = -1
        incidence[end, k] = 1
    balance = hstack([csc_matrix(np.eye(nz)), csc_matrix(incidence),
                      csc_matrix((nz, 2 * nz))], format='csc')
    match = hstack([csc_matrix(np.eye(nz)), csc_matrix((nz, ne)),
                    csc_matrix(-np.eye(nz)), csc_matrix(np.eye(nz))], format='csc')
    return vstack([balance, match], format='csc')


def run(test_hours=720):
    schema, data, _ = grouped_fit_inputs()
    lp = physical_lp()
    cost, witness = saved_annual()
    edges, lower, upper = transport_corridors(schema['zones'], data)
    nz, ne, ng = lp['nz'], len(edges), lp['ng']
    zone_index = np.array([schema['zones'].index(str(z)) for z in lp['offer_zones']])
    available = zone_totals(lp['availability'], zone_index, nz)
    dispatched = zone_totals(witness['values'][:, :ng], zone_index, nz)
    weighted_cost = zone_totals(lp['availability'] * cost, zone_index, nz)
    mean_cost = np.divide(weighted_cost, available, out=np.zeros_like(weighted_cost), where=available > 0)
    features = np.column_stack([lp['load'], available, mean_cost]) / 1000
    target = dispatched / 1000
    train = np.arange(0, 24 * (31 + 28 + 31))
    test = np.arange(24 * (31 + 28 + 31), 24 * (31 + 28 + 31) + test_hours)
    scaler = StandardScaler().fit(features[train])
    start = time.perf_counter()
    network = MLPRegressor(hidden_layer_sizes=(64, 64), activation='relu',
                           random_state=7, max_iter=100, early_stopping=True,
                           n_iter_no_change=10).fit(scaler.transform(features[train]), target[train])
    train_seconds = time.perf_counter() - start
    start = time.perf_counter()
    prediction = network.predict(scaler.transform(features[test]))
    inference_seconds = time.perf_counter() - start
    clipped = np.clip(prediction, 0, available[test] / 1000)
    A = projection_matrix(nz, edges)
    objective = np.r_[np.zeros(nz), np.full(ne, 1e-4), np.ones(2 * nz)]
    corrected = []
    repair_start = time.perf_counter()
    for offset, hour in enumerate(test):
        bounds = ([(0, float(v)) for v in available[hour] / 1000]
                  + list(zip(lower[hour], upper[hour]))
                  + [(0, None)] * (2 * nz))
        result = linprog(objective, A_eq=A,
                         b_eq=np.r_[lp['load'][hour] / 1000, clipped[offset]],
                         bounds=bounds, method='highs')
        if not result.success:
            raise RuntimeError(f'Projection hour {hour}: {result.message}')
        if np.max(np.abs(A @ result.x - np.r_[lp['load'][hour] / 1000, clipped[offset]])) > 1e-7:
            raise ValueError('Projection balance certificate failed')
        corrected.append(result.x)
    repair_seconds = time.perf_counter() - repair_start
    corrected = np.asarray(corrected)
    flow = corrected[:, nz:nz + ne]
    capacity = available[test] / 1000
    return dict(train_hours=len(train), held_out_hours=len(test), zones=nz,
                corridors=ne, training_seconds=train_seconds,
                inference_seconds=inference_seconds, correction_seconds=repair_seconds,
                raw_generation_mae_gw=float(np.abs(prediction - target[test]).mean()),
                corrected_generation_mae_gw=float(np.abs(corrected[:, :nz] - target[test]).mean()),
                maximum_generation_bound_residual_mw=float(max(
                    np.maximum(-corrected[:, :nz], 0).max(),
                    np.maximum(corrected[:, :nz] - capacity, 0).max()) * 1000),
                maximum_corridor_bound_residual_mw=float(max(
                    np.maximum(lower[test] - flow, 0).max(),
                    np.maximum(flow - upper[test], 0).max()) * 1000),
                maximum_balance_residual_mw=float(np.abs(corrected[:, :nz] +
                    corrected[:, nz:nz + ne] @ A[:nz, nz:nz + ne].toarray().T -
                    lp['load'][test] / 1000).max() * 1000),
                scope='Zonal dispatch prediction and transport projection only; no technology offers, prices, PTDF or storage')


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
