"""Wu–Lisser-style ODE-residual neural approximation of a zonal transport LP.

Research diagnostic. Fixed 48-zone/95-corridor independent transport model;
hourly aggregate generation, not the accepted 799-offer physical PTDF LP.
The network has no solver or projection in its inference path.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import time
from pathlib import Path

import numpy as np
import torch
from scipy.optimize import linprog
from torch import nn

from .evaluation import ANNUAL
from .odd_even_transformer_trial import MONTH
from .source import ROOT, digest
from .transformer_screen_trial import inputs

OUT = ROOT / 'data/bidding-zone-network-2025/neurodynamic-transport-v1'
SCALE_GW = 10.0
SCALE_PRICE = 100.0


class TrajectoryNet(nn.Module):
    def __init__(self, ntheta, nstate):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(ntheta + 1, 256), nn.Tanh(),
                                 nn.Linear(256, 256), nn.Tanh(),
                                 nn.Linear(256, nstate))

    def forward(self, theta, t):
        return (1 - torch.exp(-t)) * self.net(torch.cat([theta, t / 10], dim=1))


def construction():
    edges, raw = inputs()
    feature, capacity, lower, upper, load, _, _, incidence = raw
    nz, ne = 48, len(edges)
    nx = nz + ne
    # Ax <= b: +balance, -balance, +q, -q, +f, -f.
    balance = np.column_stack([np.eye(nz), incidence.T])
    A = np.vstack([balance, -balance, np.eye(nx)[:nz],
                   -np.eye(nx)[:nz], np.eye(nx)[nz:], -np.eye(nx)[nz:]]).astype('float32')
    if A.shape != (2 * nz + 2 * nx, nx):
        raise ValueError('Changed transport LP constraint order')
    d = load / SCALE_GW
    cap = capacity / SCALE_GW
    lo = lower / SCALE_GW
    hi = upper / SCALE_GW
    cost = feature[:, :, -1]  # accepted fitted mean zonal offer cost / 100
    b = np.column_stack([d, -d, cap, np.zeros_like(cap), hi, -lo]).astype('float32')
    c = np.column_stack([cost, np.zeros_like(lower)]).astype('float32')
    theta = np.column_stack([b, c]).astype('float32')
    odd = np.flatnonzero(MONTH % 2 == 1)
    mean = theta[odd].mean(axis=0)
    std = np.maximum(theta[odd].std(axis=0), .05)
    standardized = (theta - mean) / std
    return dict(A=torch.from_numpy(A), b=torch.from_numpy(b), c=torch.from_numpy(c),
                theta=torch.from_numpy(standardized), lower=lower, upper=upper,
                capacity=capacity, load=load, incidence=incidence, cost=cost,
                edges=edges, nx=nx, odd=odd,
                even=np.flatnonzero(MONTH % 2 == 0))


def vector_field(y, c, b, A, nx):
    x, u = y[:, :nx], y[:, nx:]
    slack_excess = x @ A.T - b
    projected = torch.relu(u + slack_excess)
    return torch.cat([-c - projected @ A, projected - u], dim=1)


def ode_loss(model, theta, c, b, A, nx, t):
    # Forward-mode JVP computes dy/dt for all primal and dual coordinates;
    # unlike finite differences, this is the paper's actual ODE residual.
    y, derivative = torch.func.jvp(lambda tau: model(theta, tau),
                                   (t,), (torch.ones_like(t),))
    field = vector_field(y, c, b, A, nx)
    return (derivative - field).square().mean()


def predict(model, data, indices):
    model.eval()
    started = time.perf_counter()
    outputs = []
    with torch.no_grad():
        for part in np.array_split(indices, max(1, (len(indices) + 255) // 256)):
            outputs.append(model(data['theta'][part], torch.full((len(part), 1), 10.0)))
    y = torch.cat(outputs).numpy()
    return y, time.perf_counter() - started


def audit_prediction(data, indices, y):
    nx = data['nx']
    x, u = y[:, :nx], y[:, nx:]
    A = data['A'].numpy()
    b = data['b'][indices].numpy()
    c = data['c'][indices].numpy()
    excess = x @ A.T - b
    stationarity = c + u @ A
    scale_mw = SCALE_GW * 1000
    balance = (x[:, :48] + x[:, 48:] @ data['incidence'].astype('float32')
               - data['load'][indices] / SCALE_GW)
    return dict(hours=len(indices),
                balance_mae_mw=float(np.abs(balance).mean() * scale_mw),
                balance_max_mw=float(np.abs(balance).max() * scale_mw),
                inequality_max_violation_mw=float(np.maximum(excess, 0).max() * scale_mw),
                inequality_above_1mw_cells=int((excess > 1 / scale_mw).sum()),
                dual_negative_max=float(np.maximum(-u, 0).max()),
                stationarity_mae=float(np.abs(stationarity).mean()),
                complementarity_mae=float(np.abs(u * excess).mean()),
                mean_predicted_objective=float((c * x).sum(axis=1).mean()))


def oracle(data, indices, x):
    A = data['A'].numpy()
    b = data['b'][indices].numpy()
    c = data['c'][indices].numpy()
    objectives, prices, errors = [], [], []
    started = time.perf_counter()
    for row, hour in enumerate(indices):
        solution = linprog(c[row], A_ub=A.astype('float64'),
                           b_ub=b[row].astype('float64'), bounds=[(None, None)] * data['nx'],
                           method='highs')
        if not solution.success:
            raise RuntimeError(f'Exact transport LP hour {hour}: {solution.message}')
        objectives.append(solution.fun)
        # Positive and negative copies of balance have non-unique duals.
        prices.append((solution.ineqlin.marginals[:48] -
                       solution.ineqlin.marginals[48:96]) * SCALE_PRICE)
        errors.append(float(np.abs(solution.x - x[row]).mean()))
    predicted = (c * x).sum(axis=1)
    gap = predicted - np.asarray(objectives)
    return dict(exact_solve_seconds=time.perf_counter() - started,
                exact_mean_objective=float(np.mean(objectives)),
                predicted_minus_exact_objective_mean=float(gap.mean()),
                predicted_objective_below_optimum_hours=int((gap < -1e-5).sum()),
                decision_mae_scaled=float(np.mean(errors)),
                exact_price_mean_eur_mwh=float(np.mean(prices)))


def run(epochs=20, batch_size=128):
    torch.set_num_threads(2)
    if epochs != 20 or batch_size != 128:
        raise ValueError('This trial is sealed at 20 epochs and batch size 128')
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'job.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        data = construction()
        provenance = dict(protocol='wu-lisser-zonal-transport-ode-residual-v1',
                          source_sha256=digest(Path(__file__)),
                          transformer_source_sha256=digest(ROOT / 'baselines/compact/transformer_screen_trial.py'),
                          annual_witness_sha256=digest(ANNUAL / 'annual.npz'),
                          fitted_costs_sha256=digest(ANNUAL / 'costs.npz'),
                          odd_hours=len(data['odd']), even_hours=len(data['even']),
                          variables=data['nx'], inequalities=len(data['A']))
        manifest = OUT / 'manifest.json'
        if manifest.exists():
            if json.loads(manifest.read_text()) != provenance:
                raise ValueError('Changed source or trial protocol; refusing resume')
        else:
            manifest.write_text(json.dumps(provenance, indent=2) + '\n')
        torch.manual_seed(17)
        model = TrajectoryNet(data['theta'].shape[1], data['nx'] + len(data['A']))
        optimizer = torch.optim.AdamW(model.parameters(), lr=.001)
        checkpoint = OUT / 'checkpoint.pt'
        history = []
        start_epoch = 0
        if checkpoint.exists():
            saved = torch.load(checkpoint, map_location='cpu', weights_only=False)
            model.load_state_dict(saved['model'])
            optimizer.load_state_dict(saved['optimizer'])
            history = saved['history']
            start_epoch = saved['epoch']
        began = time.perf_counter()
        for epoch in range(start_epoch, epochs):
            model.train()
            permutation = np.random.default_rng(100 + epoch).permutation(data['odd'])
            losses = []
            for ids in np.array_split(permutation, max(1, (len(permutation) + batch_size - 1) // batch_size)):
                t = torch.rand((len(ids), 1)) * 10
                loss = ode_loss(model, data['theta'][ids], data['c'][ids],
                                data['b'][ids], data['A'], data['nx'], t)
                optimizer.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 10)
                optimizer.step()
                losses.append(float(loss.detach()))
            row = dict(epoch=epoch + 1, odd_ode_residual_mse=float(np.mean(losses)))
            history.append(row)
            if (epoch + 1) % 5 == 0:
                temporary = checkpoint.with_suffix('.tmp')
                torch.save(dict(epoch=epoch + 1, model=model.state_dict(),
                                optimizer=optimizer.state_dict(), history=history), temporary)
                os.replace(temporary, checkpoint)
                print(f'epoch {epoch + 1}/{epochs}: ODE loss={row["odd_ode_residual_mse"]:.6f}', flush=True)
        odd_y, odd_seconds = predict(model, data, data['odd'])
        even_y, even_seconds = predict(model, data, data['even'])
        result = dict(status='experimental_ode_surrogate_not_validated_lp_solver',
                      provenance=provenance, history=history,
                      training_seconds_this_invocation=time.perf_counter() - began,
                      odd=dict(inference_seconds=odd_seconds,
                               **audit_prediction(data, data['odd'], odd_y)),
                      even=dict(inference_seconds=even_seconds,
                                **audit_prediction(data, data['even'], even_y)),
                      even_oracle=oracle(data, data['even'], even_y[:, :data['nx']]))
        (OUT / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=20)
    args = parser.parse_args()
    value = run(args.epochs)
    print(json.dumps({k:v for k,v in value.items() if k!='history'}, indent=2))
