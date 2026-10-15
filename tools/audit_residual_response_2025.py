"""Independent source-column aggregation and response-cohort replay."""
import argparse
import json
import logging
import resource
import signal
import time
from pathlib import Path

import numpy as np

from bidding_zone_network_2025 import ROOT, build
from nve_hydro_diagnostics import digest


def audit(folder):
    start = time.perf_counter()
    s = json.loads((folder / 'summary.json').read_text())
    assert digest(folder / 'fleet.npz') == s['witness_sha256']
    assert digest(folder / 'design.json') == s['design_sha256']
    assert digest(ROOT / 'tools/diagnose_residual_response_2025.py') == s['producer_sha256']
    for path, sha in s['source_hashes'].items():
        assert digest(ROOT / path) == sha, path
    for name, sha in s['source_dependencies'].items():
        assert digest(ROOT / 'tools' / name) == sha, name
    n, cost, fixed, mapping, original, old, hp = build()
    assert mapping == s['source_mapping']
    max_error = 0.
    with np.load(folder / 'fleet.npz') as saved:
        zones, carriers = saved['zones'].tolist(), saved['carriers'].tolist()
        actual = saved['available']; cheap = saved['cheap']
        expected = np.zeros_like(actual); tiers = np.zeros_like(cheap)
        pu = n.get_switchable_as_dense('Generator', 'p_max_pu')
        labels = n.buses.bidding_zone.replace({'ES-IB-MA': 'ES'})
        # Iterate source columns, never the producer's grouped inventory helper.
        for k, (name, g) in enumerate(n.generators.iterrows()):
            if g.carrier == 'emergency':
                continue
            j = zones.index(labels[g.bus]); c = carriers.index(g.carrier)
            column = pu[name].to_numpy() * float(g.p_nom)
            expected[:, j, c] += column
            for p, tier in enumerate([0., 30., 60., 100., 200.]):
                tiers[:, j, p] += np.where(cost[:, k] <= tier, column, 0.)
        max_error = max(float(abs(expected - actual).max()), float(abs(tiers - cheap).max()))
        assert max_error < 1e-6
        for row in s['inventory']:
            z, carrier = row['zone'], row['carrier']
            ids = [k for k, (_, g) in enumerate(n.generators.iterrows()) if labels[g.bus] == z and g.carrier == carrier]
            g = n.generators.iloc[ids]
            assert len(ids) == row['generators']
            assert abs(float(g.p_nom.sum()) - row['installed_mw']) < 1e-7
            assert sorted(set(float(v) for v in g.efficiency)) == row['unique_efficiencies']
            assert len({cost[:, k].tobytes() for k in ids}) == row['unique_annual_bid_profiles']
            j, c = zones.index(z), carriers.index(carrier)
            assert bool(np.ptp(expected[:, j, c]) < 1e-6) == row['availability_constant']
            assert abs(expected[:, j, c].min() - row['hourly_available_min_mw']) < 1e-6
            assert abs(expected[:, j, c].max() - row['hourly_available_max_mw']) < 1e-6
            raw = pu.iloc[:, ids].to_numpy() * g.p_nom.to_numpy()
            bids = cost[:, ids]; positive = raw > 1e-9
            if positive.any():
                for value, key in [(bids[positive].min(), 'bid_min'), (bids[positive].max(), 'bid_max'), ((bids * raw).sum() / raw.sum(), 'available_weighted_bid')]:
                    assert abs(float(value) - row[key]) < 1e-7
        base = ROOT / 'data/bidding-zone-network-2025'
        with np.load(ROOT / 'data/residual-demand-audit-2025/v1/hourly.npz') as r, np.load(base / 'annual-v7/annual.npz') as b, np.load(base / 'simple-stack-v1/benchmark.npz') as ref:
            assert r['zones'].tolist() == zones
            assert {row['zone'] for row in s['zones']} == {key.removesuffix('_prediction') for key in ref.files if key.endswith('_prediction')}
            np.testing.assert_array_equal(n.snapshots.values, np.datetime64('2025-01-01') + np.arange(8760).astype('timedelta64[h]'))
            loads = n.get_switchable_as_dense('Load', 'p_set')
            for j, z in enumerate(zones):
                load_names = n.loads.index[n.loads.bus.map(labels) == z]
                buses = labels.index[labels == z]
                np.testing.assert_allclose(loads[load_names].sum(axis=1), r['demand'][:, j], atol=1e-6, rtol=1e-12)
                np.testing.assert_allclose(fixed[buses].sum(axis=1), r['fixed_hydro'][:, j], atol=1e-6, rtol=1e-12)
                wind = sum(expected[:, j, carriers.index(c)] for c in carriers if c.startswith(('onwind', 'offwind')))
                solar = sum(expected[:, j, carriers.index(c)] for c in carriers if c.startswith('solar'))
                np.testing.assert_allclose(r['demand'][:, j] - wind - solar, r['residual_vre'][:, j], atol=1e-6, rtol=1e-12)
            all_ranked = []
            for row in s['zones']:
                z = row['zone']; j = zones.index(row['area']); x = r['residual_vre'][:, j]
                # Reconstruct linear quantiles explicitly from sorted training values.
                train = np.sort(x[:4344]); positions = np.array([.2, .4, .6, .8]) * (len(train) - 1)
                edges = np.interp(positions, np.arange(len(train)), train)
                np.testing.assert_allclose(edges, row['edges_mw'], atol=1e-7, rtol=0)
                obs = np.array(json.loads((ROOT / f'data/price-trace/dispatch-validation-2025-v2/{z}.json').read_text()), float)
                price = b['bidding_zone_prices'][:, j]; fitted = ref[z + '_prediction']
                ids = (x[:, None] >= edges).sum(axis=1)
                common = (np.arange(8760) >= 4344) & np.isfinite(obs) & np.isfinite(price) & np.isfinite(fitted)
                assert int(common.sum()) == row['evaluation_hours'] == 4416
                for band in row['bands']:
                    mask = common & (ids == band['band'] - 1)
                    assert mask.sum() == band['hours']
                    if not mask.any():
                        continue
                    calculations = dict(residual_mean_mw=x[mask].mean(), observed_mean=obs[mask].mean(), physical_mean=price[mask].mean(), reference_mean=fitted[mask].mean(), physical_bias=(price[mask] - obs[mask]).mean(), physical_mae=abs(price[mask] - obs[mask]).mean(), fixed_hydro_mean_mw=r['fixed_hydro'][mask, j].mean(), demand_mean_mw=r['demand'][mask, j].mean())
                    for key, value in calculations.items():
                        assert abs(float(value) - band[key]) < 1e-7, (z, key)
                    for c, carrier in enumerate(carriers):
                        assert abs(expected[mask, j, c].mean() - band['available_mean_mw'][carrier]) < 1e-6
                    local = tiers[mask, j] + r['fixed_hydro'][mask, j, None] - r['demand'][mask, j, None]
                    np.testing.assert_allclose(local.mean(axis=0), band['tier_local_surplus_mean_mw'], atol=1e-6, rtol=0)
                    if mask.sum() >= 100:
                        all_ranked.append(dict(zone=z, **band))
            assert sorted(all_ranked, key=lambda row: -abs(row['physical_bias']))[:20] == s['largest_band_biases']
    result = dict(status='source_fleet_and_temporal_response_replay_passed',
                  summary_sha256=digest(folder / 'summary.json'), auditor_sha256=digest(__file__),
                  zones=len(s['zones']), inventory_rows=len(s['inventory']), maximum_source_sum_error_mw=max_error,
                  elapsed_seconds=time.perf_counter() - start,
                  limit='Descriptive associations; no coefficient change, causal error attribution or empirical acceptance')
    (folder / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p = argparse.ArgumentParser(); p.add_argument('folder', type=Path); args = p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (5 * 1024**3, 5 * 1024**3)); signal.alarm(1200)
    audit(args.folder)
