"""Train six independent odd-month curves; freeze before next-month scoring."""
import argparse
import fcntl
import json
import logging
import resource
import signal
import time
import traceback
import numpy as np
from sigmoid_month_pairs_2025 import (ROOT, OUT, PLAN, digest, digest_bytes, write, prepare, load, split,
    neutral, clear, metric, objective, inverse_fit, update)


def save_witness(name, witness):
    path = OUT/name
    np.savez_compressed(path, **witness)
    return dict(path=str(path.relative_to(ROOT)), sha256=digest(path))


def run():
    started = time.perf_counter(); sealed, data, A = load(); summary = []
    for train, test in sealed['design']['pairs']:
        record_path = OUT/f'pair-{train:02d}-{test:02d}.json'
        if record_path.exists():
            row = json.loads(record_path.read_text())
            assert row['inputs_sha256'] == digest(OUT/'inputs.json')
            for r in row['witnesses'].values():
                assert digest(ROOT/r['path']) == r['sha256']
            assert digest(ROOT/row['proposal']['path']) == row['proposal']['sha256']
            summary.append(row); continue
        begun = time.perf_counter(); fit_hours, test_hours = split(train, test)
        # Save only this odd month's targets as a reproducible fitting boundary.
        train_targets = OUT/f'train-{train:02d}-targets.npz'
        np.savez_compressed(train_targets, hours=fit_hours, prices=data['observed_prices'][fit_hours], generation=data['observed_generation'][fit_hours], ember=data['ember'][train-1])
        theta = neutral(sealed)
        control, control_info = clear(sealed, data, A, theta, fit_hours)
        cm, _ = metric(sealed, data, control['row_duals'][:, :sealed['nz']], control['generation'], fit_hours, train)
        best = theta; witness = control; best_info = control_info; best_metrics = cm; history = []
        def entry(label, state, w, info):
            metrics, monthly = metric(sealed, data, w['row_duals'][:, :sealed['nz']], w['generation'], fit_hours, train)
            score = objective(metrics, state, sealed)
            history.append(dict(label=label, objective=score, metrics=metrics, theta_sha256=digest_bytes(state), **info))
            write(OUT/f'train-{train:02d}-progress.json', history)
            print('fit', train, label, 'objective', round(score, 5), 'priceMAE', round(metrics['price_mae'], 3), 'mix', round(metrics['generation_normalized_mae'], 4), 'seconds', round(info['seconds'], 2), flush=True)
            return score, metrics, monthly
        best_score, _, monthly = entry('unfit-control', theta, control, control_info)
        fitting = time.perf_counter()
        fitted, support, imputed = inverse_fit(sealed, data, fit_hours, control['row_duals'][:, :sealed['nz']], train)
        inverse_seconds = time.perf_counter()-fitting
        fw, fi = clear(sealed, data, A, fitted, fit_hours)
        value, fm, mon = entry('inverse-initializer', fitted, fw, fi)
        if value < best_score-1e-12:
            best, witness, best_info, best_metrics, best_score, monthly = fitted, fw, fi, fm, value, mon
        for iteration in range(sealed['design']['network_iterations']):
            direction = update(sealed, data, best, witness, monthly, train)-best
            if np.max(abs(direction)) < 1e-10:
                break
            origin = best.copy(); candidates = []
            for strength in sealed['design']['network_step_sizes']:
                candidate = origin+strength*direction
                cw, ci = clear(sealed, data, A, candidate, fit_hours)
                score, metrics, mon = entry(f'network-{iteration+1}-strength-{strength}', candidate, cw, ci)
                candidates.append((score, candidate, cw, ci, metrics, mon))
            chosen = min(candidates, key=lambda r:r[0])
            if chosen[0] < best_score-1e-12:
                best_score, best, witness, best_info, best_metrics, monthly = chosen
            else:
                break
        proposal = OUT/f'proposal-{train:02d}.json'
        write(proposal, dict(train_month=train, test_month=test, training_hours=fit_hours.tolist(), target_sha256=digest(train_targets),
              theta=best.tolist(), initializer_theta=fitted.tolist(), neutral_theta=theta.tolist(), support=support, imputed_training_price_cells=imputed,
              selected_training_objective=best_score, history=history, selection='minimum exact odd-month network price/mix objective; test targets not read for selection'))
        frozen = digest(proposal)
        # No call above scores an even month. Test outcomes cannot select theta.
        tw, ti = clear(sealed, data, A, best, test_hours)
        tc, tci = clear(sealed, data, A, theta, test_hours)
        learned, _ = metric(sealed, data, tw['row_duals'][:, :sealed['nz']], tw['generation'], test_hours, test)
        unfit, _ = metric(sealed, data, tc['row_duals'][:, :sealed['nz']], tc['generation'], test_hours, test)
        accepted, _ = metric(sealed, data, data['accepted_prices'][test_hours], data['accepted_generation'][test_hours], test_hours, test)
        assert digest(proposal) == frozen
        files = dict(train_control=save_witness(f'train-{train:02d}-control.npz', control), train_selected=save_witness(f'train-{train:02d}-selected.npz', witness),
                     test_control=save_witness(f'test-{test:02d}-control.npz', tc), test_selected=save_witness(f'test-{test:02d}-selected.npz', tw))
        row = dict(train_month=train, test_month=test, inputs_sha256=digest(OUT/'inputs.json'), proposal=dict(path=str(proposal.relative_to(ROOT)), sha256=frozen),
                   train_hours=len(fit_hours), test_hours=len(test_hours), train_control=cm, train_selected=best_metrics,
                   test_control=unfit, test_selected=learned, accepted_insample_test=accepted, inverse_fit_seconds=inverse_seconds,
                   training_clearing_seconds=sum(h['seconds'] for h in history), test_clearing_seconds=ti['seconds']+tci['seconds'],
                   test_selected_info=ti, test_control_info=tci, witnesses=files, pair_seconds=time.perf_counter()-begun)
        write(record_path, row); summary.append(row)
        write(OUT/'progress.json', dict(completed_pairs=len(summary), pairs=summary))
        print('PAIR', train, '->', test, 'TEST MAE', learned['price_mae'], 'CONTROL', unfit['price_mae'], 'MIX', learned['generation_normalized_mae'], 'seconds', row['pair_seconds'], flush=True)
    write(OUT/'summary.json', dict(status='six_odd_train_even_test_pairs_complete_not_adopted', producer_sha256=digest(__file__), helper_sha256=digest(ROOT/'tools/sigmoid_month_pairs_2025.py'),
          inputs_sha256=digest(OUT/'inputs.json'), pairs=summary, test_hours=sum(r['test_hours'] for r in summary), train_hours=sum(r['train_hours'] for r in summary),
          execution_seconds=time.perf_counter()-started))


if __name__ == '__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    parser = argparse.ArgumentParser(); parser.add_argument('stage', choices=['prepare', 'run']); args = parser.parse_args()
    limits = json.loads(PLAN.read_text())['limits']
    resource.setrlimit(resource.RLIMIT_AS, (limits['address_space_gib']*1024**3,)*2)
    signal.alarm(limits['job_seconds'])
    lock = (OUT.parent/'sigmoid-month-pairs-v1.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    try:
        prepare() if args.stage == 'prepare' else run()
    except Exception:
        if OUT.exists():
            write(OUT/'failure.json', dict(stage=args.stage, traceback=traceback.format_exc()))
        raise
