"""One-pass transformer dispatch pilot; no clearing or correction at inference.

Training targets are retained LP outputs. April is held out from network
training, but the 2025 bids themselves were fitted retrospectively.
"""
from __future__ import annotations

import json
import time

import numpy as np
import torch
from torch import nn

from .evaluation import physical_lp, saved_annual
from .network import transport_corridors
from .source import grouped_fit_inputs
from .vendor.aurora.aurora import aurora


class MarketTransformer(nn.Module):
    def __init__(self, features, edges, width=64):
        super().__init__()
        self.register_buffer('start', torch.tensor(edges[:, 0], dtype=torch.long))
        self.register_buffer('end', torch.tensor(edges[:, 1], dtype=torch.long))
        self.embed = nn.Linear(features, width)
        self.zone_id = nn.Parameter(torch.zeros(1, 48, width))
        layer = nn.TransformerEncoderLayer(width, 4, 128, dropout=0, batch_first=True,
                                           norm_first=True)
        self.body = nn.TransformerEncoder(layer, 2, enable_nested_tensor=False)
        self.generation = nn.Linear(width, 1)
        self.price = nn.Linear(width, 1)
        self.flow = nn.Sequential(nn.Linear(2 * width + 2, width), nn.GELU(), nn.Linear(width, 1))

    def forward(self, zone_features, capacity, lower, upper):
        hidden = self.body(self.embed(zone_features) + self.zone_id)
        generation = torch.sigmoid(self.generation(hidden).squeeze(-1)) * capacity
        price = self.price(hidden).squeeze(-1) * 100
        edge = torch.cat([hidden[:, self.start], hidden[:, self.end],
                          lower[..., None], upper[..., None]], dim=-1)
        flow = lower + torch.sigmoid(self.flow(edge).squeeze(-1)) * (upper - lower)
        return generation, flow, price


def inputs():
    schema, data, _ = grouped_fit_inputs()
    lp = physical_lp()
    _, witness = saved_annual()
    edges, lower, upper = transport_corridors(schema['zones'], data)
    nz = lp['nz']
    kinds = sorted({group['technology'] for group in schema['groups']})
    features = np.zeros((8760, nz, 1 + 2 * len(kinds)), np.float32)
    features[:, :, 0] = lp['load'] / 1000 / 20
    for k, group in enumerate(schema['groups']):
        z = schema['zones'].index(group['zone'])
        t = kinds.index(group['technology'])
        capacity = data['capacity'][:, k] / 1000
        features[:, z, 1 + t] += capacity / 20
        features[:, z, 1 + len(kinds) + t] += capacity * data['source_cost'][:, k] / 2000
    availability = np.zeros((8760, nz), np.float32)
    target = np.zeros_like(availability)
    for z, name in enumerate(schema['zones']):
        columns = np.asarray(lp['offer_zones']).astype(str) == name
        availability[:, z] = lp['availability'][:, columns].sum(axis=1) / 1000
        target[:, z] = witness['values'][:, :lp['ng']][:, columns].sum(axis=1) / 1000
    incidence = np.zeros((len(edges), nz), np.float32)
    incidence[np.arange(len(edges)), edges[:, 0]] = -1
    incidence[np.arange(len(edges)), edges[:, 1]] = 1
    arrays = (features, availability, lower.astype('float32'), upper.astype('float32'),
              lp['load'].astype('float32') / 1000, target,
              witness['row_duals'][:, :nz].astype('float32'), incidence)
    return edges, arrays


def train_one(name, edges, tensors, epochs=12):
    torch.manual_seed(11)
    model = MarketTransformer(tensors[0].shape[-1], edges)
    ordinary = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
    matrices = [parameter for parameter in model.parameters() if parameter.ndim == 2]
    momentum = [torch.zeros_like(parameter) for parameter in matrices]
    training = torch.arange(2160)
    testing = torch.arange(2160, 2880)
    start = time.perf_counter()
    history = []
    for epoch in range(epochs):
        model.train()
        generator = torch.Generator().manual_seed(100 + epoch)
        batches = training[torch.randperm(len(training), generator=generator)].split(128)
        for ids in batches:
            x, cap, lo, hi, load, target, prices, incidence = tensors
            generation, flow, predicted_price = model(x[ids], cap[ids], lo[ids], hi[ids])
            balance = generation + flow @ incidence - load[ids]
            loss = ((generation - target[ids]) ** 2).mean() / 100
            loss = loss + ((predicted_price - prices[ids]) ** 2).mean() / 10000
            loss = loss + 4 * (balance ** 2).mean() / 100
            ordinary.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 10)
            if name == 'aurora':
                # Aurora updates matrix weights; AdamW handles embeddings,
                # biases and norm parameters, as in the released recipe.
                for parameter in matrices:
                    parameter.grad_saved = parameter.grad
                    parameter.grad = None
                ordinary.step()
                for parameter, state in zip(matrices, momentum):
                    aurora(parameter, parameter.grad_saved, state, eta=0.002, weight_decay=0.01)
                    del parameter.grad_saved
            else:
                ordinary.step()
        history.append(float(loss.detach()))
    train_seconds = time.perf_counter() - start
    model.eval()
    start = time.perf_counter()
    with torch.no_grad():
        output = [model(tensors[0][ids], tensors[1][ids], tensors[2][ids], tensors[3][ids])
                  for ids in testing.split(128)]
        generation = torch.cat([part[0] for part in output])
        flow = torch.cat([part[1] for part in output])
        price = torch.cat([part[2] for part in output])
        residual = generation + flow @ tensors[7] - tensors[4][testing]
    inference_seconds = time.perf_counter() - start
    return dict(optimizer=name, epochs=epochs, training_seconds=train_seconds,
                inference_seconds=inference_seconds, final_training_batch_loss=history[-1],
                held_out_generation_mae_gw=float((generation - tensors[5][testing]).abs().mean()),
                held_out_price_mae_to_lp_eur_mwh=float((price - tensors[6][testing]).abs().mean()),
                held_out_balance_mae_mw=float(residual.abs().mean() * 1000),
                held_out_max_balance_residual_mw=float(residual.abs().max() * 1000),
                held_out_generation_bound_violation_mw=float(torch.maximum(-generation,
                    generation - tensors[1][testing]).clamp_min(0).max() * 1000),
                held_out_corridor_bound_violation_mw=float(torch.maximum(tensors[2][testing] - flow,
                    flow - tensors[3][testing]).clamp_min(0).max() * 1000))


def run():
    torch.set_num_threads(2)
    edges, arrays = inputs()
    tensors = tuple(torch.from_numpy(value) for value in arrays)
    return [train_one(name, edges, tensors) for name in ('adamw', 'aurora')]


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
