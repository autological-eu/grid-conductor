"""Replay frozen folds, inverse target isolation, dispatch, duals and scores."""
import json
import fcntl
import logging
import resource
import time
import numpy as np
from scipy.special import logit
from sigmoid_month_pairs_2025 import (ROOT, OUT, load, split, inverse_fit, neutral, certify, metric,
    generation, objective, update, digest, digest_bytes, write)


def audit():
    start = time.perf_counter(); sealed, data, A = load()
    producer = digest(ROOT/'tools/run_sigmoid_month_pairs_2025.py')
    helper = digest(ROOT/'tools/sigmoid_month_pairs_2025.py'); waiting = 0.
    def read_when_complete(path):
        nonlocal waiting
        began = time.perf_counter()
        while True:
            if (OUT/'failure.json').exists():
                raise RuntimeError('Runner failure; no completed audit claim')
            try:
                value = json.loads(path.read_text())
                waiting += time.perf_counter()-began
                return value
            except (FileNotFoundError, json.JSONDecodeError):
                if time.perf_counter()-start > 2400:
                    raise TimeoutError('Waiting for immutable completed pair')
                time.sleep(5)
    G = len(sealed['groups']); K = sealed['design']['segments']; checked = 0; pairs = []
    maximum = dict(primal_mw=0., duality_gap_eur=0., complementarity_eur=0., free_reduced_cost_eur_mwh=0.)
    all_test = []; records = []
    for train, test in sealed['design']['pairs']:
        row = read_when_complete(OUT/f'pair-{train:02d}-{test:02d}.json')
        assert row['inputs_sha256'] == digest(OUT/'inputs.json')
        assert row['train_month'] == train and row['test_month'] == test
        records.append(row)
        fit_hours, test_hours = split(train, test); all_test.extend(test_hours)
        pp = ROOT/row['proposal']['path']; assert digest(pp) == row['proposal']['sha256']; proposal = json.loads(pp.read_text())
        np.testing.assert_array_equal(proposal['training_hours'], fit_hours)
        path = OUT/f'train-{train:02d}-targets.npz'; assert digest(path) == proposal['target_sha256']
        with np.load(path) as z:
            np.testing.assert_array_equal(z['hours'], fit_hours)
            for key, source in [('prices', 'observed_prices'), ('generation', 'observed_generation')]:
                np.testing.assert_array_equal(z[key], data[source][fit_hours])
            np.testing.assert_array_equal(z['ember'], data['ember'][train-1])
        histories = proposal['history']
        best = min(h['objective'] for h in histories)
        theta = np.array(proposal['theta'])
        assert abs(best-proposal['selected_training_objective']) < 1e-12
        assert any(h['theta_sha256'] == digest_bytes(theta) and abs(h['objective']-best) < 1e-12 for h in histories)
        assert abs(theta[:, :5]).max() <= 80+1e-9 and np.exp(theta[:, 5]).min() >= 1-1e-9 and np.exp(theta[:, 5]).max() <= 100+1e-9
        for role, record in row['witnesses'].items():
            path = ROOT/record['path']; assert digest(path) == record['sha256']
            with np.load(path) as z:
                w = {key:z[key] for key in z.files}
            hours = fit_hours if role.startswith('train') else test_hours
            np.testing.assert_array_equal(w['hours'], hours)
            state = neutral(sealed) if role.endswith('control') else theta
            gi = [g['parameter'] for g in sealed['groups']]; zi = [g['zone_id'] for g in sealed['groups']]
            # Independent reconstruction, not the offer compiler's reshape path.
            prices = np.zeros((len(hours), G*K))
            for j in range(G):
                par = state[gi[j]]
                midpoint = data['source_cost'][hours, j]+np.clip(data['features'][hours, zi[j]]@par[:5], -80, 80)
                prices[:, j*K:(j+1)*K] = midpoint[:, None]+np.exp(par[5])*logit((np.arange(K)+.5)/K)
            assert (np.diff(prices.reshape(len(hours), G, K), axis=2) >= 0).all()
            cost = np.c_[prices, data['emergency_cost'][hours]]
            av = np.c_[np.repeat(data['capacity'][hours]/K, K, axis=1), data['emergency_available'][hours]]
            np.testing.assert_allclose(av[:, :G*K].reshape(len(hours), G, K).sum(axis=2), data['capacity'][hours], rtol=0, atol=1e-8)
            result = certify(A, cost, av, data, hours, w['values'], w['row_duals'], w['objectives'], sealed['ng'], sealed['nl'], sealed['nz'])
            for key in maximum:
                maximum[key] = max(maximum[key], result[key])
            assert np.maximum(w['values'][:, G*K:sealed['ng']], 0).sum() <= 1e-6
            gen = generation(sealed, data, w['values'], hours)
            np.testing.assert_allclose(gen, w['generation'], rtol=0, atol=1e-7)
            np.testing.assert_allclose(gen.sum(axis=(1, 2)), w['values'][:, :G*K].sum(axis=1)+data['fixed_generation'][hours].sum(axis=(1, 2)), rtol=0, atol=1e-5)
            metrics, _ = metric(sealed, data, w['row_duals'][:, :sealed['nz']], gen, hours, train if role.startswith('train') else test)
            target = row[role]
            for key in metrics:
                assert abs(metrics[key]-target[key]) < 1e-9, (role, key)
            if role == 'train_selected':
                assert abs(objective(metrics, state, sealed)-best) < 1e-12
            checked += len(hours)
        with np.load(ROOT/row['witnesses']['train_control']['path']) as z:
            control_prices = z['row_duals'][:, :sealed['nz']]
        # Poison every non-training observation in an independent copy. Learned
        # initialization must reproduce the original proposal, including targets.
        poisoned = data.copy()
        for key in ['observed_prices', 'observed_generation']:
            poisoned[key] = data[key].copy(); mask = np.ones(8760, bool); mask[fit_hours] = False
            poisoned[key][mask] = 1e12
        poisoned['ember'] = data['ember'].copy(); keep = poisoned['ember'][train-1].copy(); poisoned['ember'][:] = 1e12; poisoned['ember'][train-1] = keep
        replay, _, imputed = inverse_fit(sealed, poisoned, fit_hours, control_prices, train)
        np.testing.assert_array_equal(np.asarray(proposal['initializer_theta']), replay)
        assert imputed == proposal['imputed_training_price_cells']
        with np.load(ROOT/row['witnesses']['train_selected']['path']) as z:
            selected = {k:z[k] for k in z.files}
        _, monthly = metric(sealed, data, selected['row_duals'][:, :sealed['nz']], selected['generation'], fit_hours, train)
        np.testing.assert_array_equal(update(sealed, data, theta, selected, monthly, train),
                                      update(sealed, poisoned, theta, selected, monthly, train))
        pairs.append(dict(train_month=train, test_month=test, heldout_hours=len(test_hours), initializer_and_update_isolation='all_other_month_targets_poisoned_without_parameter_change'))
        write(OUT/'audit-progress.json', dict(completed_pairs=len(pairs), pairs=pairs, retained_witness_hours=checked, maximum_certificate=maximum))
        print('Audited pair', train, '->', test, flush=True)
    assert checked == 17520 and len(set(all_test)) == 4344 and len(all_test) == 4344
    summary = read_when_complete(OUT/'summary.json')
    assert summary['status'] == 'six_odd_train_even_test_pairs_complete_not_adopted'
    assert summary['inputs_sha256'] == digest(OUT/'inputs.json') and summary['pairs'] == records
    assert summary['producer_sha256'] == producer == digest(ROOT/'tools/run_sigmoid_month_pairs_2025.py')
    assert summary['helper_sha256'] == helper == digest(ROOT/'tools/sigmoid_month_pairs_2025.py')
    result = dict(status='all_six_folds_17520_retained_LP_hours_and_target_isolation_passed', summary_sha256=digest(OUT/'summary.json'),
                  inputs_sha256=digest(OUT/'inputs.json'), auditor_sha256=digest(__file__), retained_witness_hours=checked,
                  heldout_hours=len(all_test), maximum_certificate=maximum, pairs=pairs, seconds=time.perf_counter()-start-waiting,
                  wall_seconds=time.perf_counter()-start, waiting_seconds=waiting, concurrent_with_training=True)
    write(OUT/'audit.json', result); print(result['status'], result['seconds'], flush=True)


if __name__ == '__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    resource.setrlimit(resource.RLIMIT_AS, (5*1024**3,)*2)
    lock = (OUT/'audit.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    audit()
