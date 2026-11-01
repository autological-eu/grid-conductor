"""Read-only evaluation of the paused odd/even AttnRes checkpoint."""
from __future__ import annotations

import json

import numpy as np
import torch

from .odd_even_transformer_trial import MONTH, OUT, evaluate
from .transformer_screen_trial import MarketTransformer, inputs
from .source import grouped_fit_inputs, ROOT, digest
from .evaluation import ANNUAL


def run():
    torch.set_num_threads(2)
    manifest = json.loads((OUT / 'manifest.json').read_text())
    if manifest['model_source_sha256'] != digest(ROOT / 'baselines/compact/odd_even_transformer_trial.py'):
        raise ValueError('Training source changed since checkpoint')
    if manifest['transformer_source_sha256'] != digest(ROOT / 'baselines/compact/transformer_screen_trial.py'):
        raise ValueError('Transformer source changed since checkpoint')
    if manifest['annual_witness_sha256'] != digest(ANNUAL / 'annual.npz'):
        raise ValueError('LP witness changed since checkpoint')
    checkpoint = torch.load(OUT / 'checkpoint.pt', map_location='cpu', weights_only=False)
    if checkpoint['epoch'] != len(checkpoint['history']):
        raise ValueError('Incomplete checkpoint history')
    edges, raw = inputs()
    arrays = tuple(torch.from_numpy(value) for value in raw)
    model = MarketTransformer(arrays[0].shape[-1], edges, architecture='attnres')
    model.load_state_dict(checkpoint['model'])
    _, source, _ = grouped_fit_inputs()
    observed = torch.from_numpy(np.asarray(source['observed_prices'], dtype=np.float32))
    results = dict(status='paused_after_epoch_10_not_feasible_clearing',
                   epoch=checkpoint['epoch'], checkpoint_sha256=digest(OUT / 'checkpoint.pt'),
                   training_source_sha256=manifest['model_source_sha256'],
                   odd=evaluate(model, torch.from_numpy(np.flatnonzero(MONTH % 2 == 1).copy()), arrays, observed),
                   even=evaluate(model, torch.from_numpy(np.flatnonzero(MONTH % 2 == 0).copy()), arrays, observed),
                   even_months={str(month): evaluate(model,
                       torch.from_numpy(np.flatnonzero(MONTH == month).copy()), arrays, observed)
                       for month in range(2, 13, 2)},
                   loss_history=checkpoint['history'])
    if results['even']['price_mae_to_lp_eur_mwh'] != checkpoint['history'][-1]['even']['price_mae_to_lp_eur_mwh']:
        raise ValueError('Paused checkpoint does not reproduce saved even score')
    return results


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
