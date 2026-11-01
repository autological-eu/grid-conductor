"""Train the one-pass AttnRes screen on odd 2025 months; audit even months.

All odd-month hours train the network. Even-month scores never select a model.
The 100-epoch fixed horizon is resumable at 10-epoch checkpoints in ignored
data; no LP or projection is called during network inference.
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

from .source import ROOT, digest, grouped_fit_inputs
from .evaluation import ANNUAL
from .transformer_screen_trial import MarketTransformer, inputs
from .vendor.aurora.aurora import aurora

OUT = ROOT / 'data/bidding-zone-network-2025/odd-even-attnres-v1'
MONTH = (np.arange('2025-01-01T00', '2026-01-01T00', dtype='datetime64[h]')
         .astype('datetime64[M]').astype(int) % 12 + 1)


def loss_parts(generation, flow, price, ids, arrays):
    _, _, _, _, load, target, teacher_price, incidence = arrays
    balance = generation + flow @ incidence - load[ids]
    generation_loss = (generation - target[ids]).square().mean() / 100
    price_loss = (price - teacher_price[ids]).square().mean() / 10000
    balance_loss = 4 * balance.square().mean() / 100
    return generation_loss, price_loss, balance_loss


def evaluate(model, ids, arrays, observed):
    predictions = []
    model.eval()
    began = time.perf_counter()
    with torch.no_grad():
        for block in ids.split(256):
            predictions.append(model(arrays[0][block], arrays[1][block],
                                     arrays[2][block], arrays[3][block]))
    seconds = time.perf_counter() - began
    generation = torch.cat([p[0] for p in predictions])
    flow = torch.cat([p[1] for p in predictions])
    price = torch.cat([p[2] for p in predictions])
    balance = generation + flow @ arrays[7] - arrays[4][ids]
    target_price = arrays[6][ids]
    obs = observed[ids]
    covered = torch.isfinite(obs)
    price_error = (price - obs).abs()
    return dict(hours=len(ids), observed_price_cells=int(covered.sum()),
                inference_seconds=seconds,
                price_mae_to_lp_eur_mwh=float((price - target_price).abs().mean()),
                price_mae_to_observed_eur_mwh=float(price_error[covered].mean()),
                generation_mae_to_lp_gw=float((generation - arrays[5][ids]).abs().mean()),
                balance_mae_mw=float(balance.abs().mean() * 1000),
                balance_max_mw=float(balance.abs().max() * 1000),
                balance_above_1mw_cells=int((balance.abs() > .001).sum()),
                generation_bound_violation_mw=float(torch.maximum(-generation,
                    generation - arrays[1][ids]).clamp_min(0).max() * 1000),
                corridor_bound_violation_mw=float(torch.maximum(arrays[2][ids] - flow,
                    flow - arrays[3][ids]).clamp_min(0).max() * 1000))


def run(epochs=100, batch_size=256):
    torch.set_num_threads(2)
    if epochs != 100 or batch_size != 256:
        raise ValueError('This sealed trial uses exactly 100 epochs and batch size 256')
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'job.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        schema, data, _ = grouped_fit_inputs()
        edges, raw = inputs()
        arrays = tuple(torch.from_numpy(value) for value in raw)
        observed = torch.from_numpy(np.asarray(data['observed_prices'], dtype=np.float32))
        assert observed.shape == arrays[6].shape == (8760, 48)
        odd = torch.from_numpy(np.flatnonzero(MONTH % 2 == 1).copy())
        even = torch.from_numpy(np.flatnonzero(MONTH % 2 == 0).copy())
        if len(odd) + len(even) != 8760:
            raise ValueError('Lost chronology')
        provenance = dict(protocol='odd-month-attnres-100-aurora-v1',
                          model_source_sha256=digest(Path(__file__)),
                          transformer_source_sha256=digest(ROOT / 'baselines/compact/transformer_screen_trial.py'),
                          annual_witness_sha256=digest(ANNUAL / 'annual.npz'),
                          fitted_costs_sha256=digest(ANNUAL / 'costs.npz'),
                          odd_hours=len(odd), even_hours=len(even),
                          zones=len(schema['zones']), edges=len(edges))
        manifest = OUT / 'manifest.json'
        if manifest.exists():
            if json.loads(manifest.read_text()) != provenance:
                raise ValueError('Changed source or protocol; refusing resume')
        else:
            manifest.write_text(json.dumps(provenance, indent=2) + '\n')
        torch.manual_seed(11)
        model = MarketTransformer(arrays[0].shape[-1], edges, architecture='attnres')
        adam = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.01)
        matrices = [p for p in model.parameters() if p.ndim == 2]
        momentum = [torch.zeros_like(p) for p in matrices]
        checkpoint = OUT / 'checkpoint.pt'
        history = []
        start_epoch = 0
        if checkpoint.exists():
            saved = torch.load(checkpoint, map_location='cpu', weights_only=False)
            model.load_state_dict(saved['model'])
            adam.load_state_dict(saved['adam'])
            momentum = saved['momentum']
            history = saved['history']
            start_epoch = saved['epoch']
        began = time.perf_counter()
        for epoch in range(start_epoch, epochs):
            model.train()
            perm = odd[torch.randperm(len(odd), generator=torch.Generator().manual_seed(100 + epoch))]
            totals = np.zeros(3)
            for ids in perm.split(batch_size):
                generation, flow, price = model(arrays[0][ids], arrays[1][ids],
                                                arrays[2][ids], arrays[3][ids])
                parts = loss_parts(generation, flow, price, ids, arrays)
                loss = sum(parts)
                adam.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 10)
                for parameter in matrices:
                    parameter.grad_saved = parameter.grad
                    parameter.grad = None
                adam.step()
                for parameter, state in zip(matrices, momentum):
                    aurora(parameter, parameter.grad_saved, state, eta=.002, weight_decay=.01)
                    del parameter.grad_saved
                totals += np.array([float(v.detach()) for v in parts]) * len(ids)
            record = dict(epoch=epoch + 1,
                          odd_generation_loss=float(totals[0] / len(odd)),
                          odd_price_loss=float(totals[1] / len(odd)),
                          odd_balance_loss=float(totals[2] / len(odd)))
            if (epoch + 1) % 10 == 0:
                record['even'] = evaluate(model, even, arrays, observed)
            history.append(record)
            if (epoch + 1) % 10 == 0:
                temporary = checkpoint.with_suffix('.tmp')
                torch.save(dict(epoch=epoch + 1, model=model.state_dict(),
                                adam=adam.state_dict(), momentum=momentum,
                                history=history), temporary)
                os.replace(temporary, checkpoint)
                print(f'epoch {epoch + 1}/{epochs}: odd loss={sum(totals) / len(odd):.5f}; '
                      f'even price-to-LP={record["even"]["price_mae_to_lp_eur_mwh"]:.2f}; '
                      f'even balance={record["even"]["balance_mae_mw"]:.0f} MW', flush=True)
        if not history or history[-1]['epoch'] != epochs:
            raise RuntimeError('Incomplete training')
        results = dict(provenance=provenance, epochs=epochs,
                       training_seconds_this_invocation=time.perf_counter() - began,
                       odd=evaluate(model, odd, arrays, observed),
                       even=evaluate(model, even, arrays, observed),
                       even_months={str(month): evaluate(model,
                           torch.from_numpy(np.flatnonzero(MONTH == month).copy()), arrays, observed)
                           for month in range(2, 13, 2)}, history=history,
                       status='research_surrogate_not_feasible_clearing')
        (OUT / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=100)
    args = parser.parse_args()
    result = run(args.epochs)
    print(json.dumps({k:v for k,v in result.items() if k!='history'}, indent=2))
