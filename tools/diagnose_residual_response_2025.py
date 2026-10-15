"""Descriptive response bands and source-fleet inventory; no fitted dispatch bids."""
import argparse
import fcntl
import json
import logging
import resource
import signal
import sys
import time
from pathlib import Path

import numpy as np

from bidding_zone_network_2025 import ROOT, build
from nve_hydro_diagnostics import digest

BASE = ROOT / 'data/bidding-zone-network-2025'
TRAIN = np.arange(8760) < 4344
EVALUATE = ~TRAIN
TIERS = [0., 30., 60., 100., 200.]


def band_edges(x):
    """Training-only quintiles; retain ties and empty bands explicitly."""
    if not np.isfinite(x).all():
        raise ValueError('Unknown training residual demand')
    return np.quantile(x, [.2, .4, .6, .8])


def band_ids(x, edges):
    return np.searchsorted(edges, x, side='right')


def response_rows(x, observed, physical, reference, edges):
    bands = band_ids(x, edges)
    common = EVALUATE & np.isfinite(observed) & np.isfinite(physical) & np.isfinite(reference)
    rows = []
    for k in range(5):
        mask = common & (bands == k)
        row = dict(band=k + 1, hours=int(mask.sum()))
        if mask.any():
            row.update(residual_mean_mw=float(x[mask].mean()),
                       observed_mean=float(observed[mask].mean()),
                       physical_mean=float(physical[mask].mean()),
                       reference_mean=float(reference[mask].mean()),
                       physical_bias=float((physical[mask] - observed[mask]).mean()),
                       physical_mae=float(abs(physical[mask] - observed[mask]).mean()))
        rows.append(row)
    return rows, common, bands


def verify_sources():
    roots = dict(residual=ROOT / 'data/residual-demand-audit-2025/v1',
                 physical=BASE / 'annual-v7', simple=BASE / 'simple-stack-v1')
    r, b, s = [json.loads((roots[k] / 'summary.json').read_text()) for k in roots]
    ra = json.loads((roots['residual'] / 'replay.json').read_text())
    sa = json.loads((roots['simple'] / 'audit.json').read_text())
    br = json.loads((roots['simple'] / 'benchmark-replay.json').read_text())
    assert ra['summary_sha256'] == digest(roots['residual'] / 'summary.json')
    assert sa['summary_sha256'] == digest(roots['simple'] / 'summary.json')
    # Seal every evidence file actually consumed, including the fitted-reference replay.
    paths = [roots['residual'] / 'summary.json', roots['residual'] / 'replay.json',
             roots['residual'] / 'hourly.npz', roots['physical'] / 'summary.json',
             roots['physical'] / 'annual.npz', roots['simple'] / 'summary.json',
             roots['simple'] / 'audit.json', roots['simple'] / 'benchmark.json',
             roots['simple'] / 'benchmark-replay.json', roots['simple'] / 'benchmark.npz']
    assert digest(roots['residual'] / 'hourly.npz') == r['witness_sha256']
    assert digest(roots['physical'] / 'annual.npz') == b['witness_sha256']
    bench = json.loads((roots['simple'] / 'benchmark.json').read_text())
    assert digest(roots['simple'] / 'benchmark.npz') == bench['witness_sha256']
    assert br['benchmark_sha256'] == digest(roots['simple'] / 'benchmark.json')
    return roots, r, b, {str(p.relative_to(ROOT)): digest(p) for p in paths}


def run(out):
    started = time.perf_counter()
    design = dict(training='January–June 4344 hours: residual-demand quintile boundaries only',
                  evaluation='July–December 4416 hours; all 41 eligible A44 price areas',
                  response='Common-hour observed, physical and separately fitted-reference means in five training-defined residual bands',
                  supply='Available MW by carrier, installed MW, efficiency and bid-profile dispersion; fixed reservoir output separate',
                  tiers_eur_mwh=TIERS,
                  envelope='Local available generator MW bidding <= each fixed price tier plus fixed hydro minus demand; excludes emergency, imports, commitment and deliverability',
                  selection='Rank evaluation bands by absolute physical mean bias with >=100 hours; descriptive post-hoc prioritization, not validation or causal attribution',
                  fixed='No solve, coefficient change, fitted dispatch bid, hydro flexibility or baseline promotion')
    (out / 'design.json').write_text(json.dumps(design, indent=2) + '\n')
    roots, residual_summary, baseline, sources = verify_sources()
    print('Evidence sealed; rebuilding unchanged source fleet', flush=True)
    n, cost, fixed, mapping, original, old, hp = build()
    zones = baseline['cases']['bidding_zone']['zones']
    labels = n.buses.bidding_zone.replace({'ES-IB-MA': 'ES'})
    carriers = sorted(set(n.generators.carrier) - {'emergency'})
    shape = (8760, len(zones))
    available = np.zeros((*shape, len(carriers)))
    cheap = np.zeros((*shape, len(TIERS)))
    av = n.get_switchable_as_dense('Generator', 'p_max_pu').values * n.generators.p_nom.values
    inventory = []
    for z in zones:
        zi = zones.index(z)
        for carrier in carriers:
            ids = np.flatnonzero((n.generators.bus.map(labels) == z) & (n.generators.carrier == carrier))
            if not len(ids):
                continue
            ci = carriers.index(carrier)
            available[:, zi, ci] = av[:, ids].sum(axis=1)
            weights = av[:, ids].sum(axis=0)
            g = n.generators.iloc[ids]
            bids = cost[:, ids]
            positive = av[:, ids] > 1e-9
            profiles = len({cost[:, k].tobytes() for k in ids})
            efficiency = sorted(set(float(v) for v in g.efficiency))
            inventory.append(dict(zone=z, carrier=carrier, generators=len(ids),
                installed_mw=float(g.p_nom.sum()), unique_efficiencies=efficiency,
                unique_annual_bid_profiles=profiles,
                bid_min=float(bids[positive].min()) if positive.any() else None,
                bid_max=float(bids[positive].max()) if positive.any() else None,
                available_weighted_bid=float((bids * av[:, ids]).sum() / weights.sum()) if weights.sum() else None,
                hourly_available_min_mw=float(available[:, zi, ci].min()),
                hourly_available_max_mw=float(available[:, zi, ci].max()),
                availability_constant=bool(np.ptp(available[:, zi, ci]) < 1e-6)))
            for k, tier in enumerate(TIERS):
                cheap[:, zi, k] += (av[:, ids] * (bids <= tier)).sum(axis=1)
    prepared = time.perf_counter() - started
    print('Source inventory prepared', round(prepared, 2), 'seconds', flush=True)
    observations = ROOT / 'data/price-trace/dispatch-validation-2025-v2'
    manifest = json.loads((observations / 'manifest.json').read_text())
    sources[str((observations / 'manifest.json').relative_to(ROOT))] = digest(observations / 'manifest.json')
    from compare_daily_dispatch_prices import audit_observations
    rows = []
    with np.load(roots['residual'] / 'hourly.npz') as r, np.load(roots['physical'] / 'annual.npz') as b, np.load(roots['simple'] / 'benchmark.npz') as ref:
        assert r['zones'].tolist() == zones
        # Independent fresh source totals must reproduce the retained features.
        for family, types in [('wind', ['onwind', 'offwind-ac', 'offwind-dc', 'offwind-float']), ('solar', ['solar', 'solar-hsat']), ('nuclear', ['nuclear'])]:
            indices = [carriers.index(c) for c in types if c in carriers]
            np.testing.assert_allclose(available[:, :, indices].sum(axis=2), r[family], atol=1e-6, rtol=1e-12)
        gap = cheap + r['fixed_hydro'][:, :, None] - r['demand'][:, :, None]
        for z, meta in sorted(manifest['zones'].items()):
            area = 'IE-SEM' if z == 'IE' else z
            if area not in zones or z + '_prediction' not in ref:
                continue
            path = observations / (z + '.json')
            assert digest(path) == meta['hourly_sha256']
            sources[str(path.relative_to(ROOT))] = digest(path)
            target = np.array(json.loads(path.read_text()), float)
            audit_observations(z, meta, target)
            j = zones.index(area)
            x = r['residual_vre'][:, j]
            edges = band_edges(x[TRAIN])
            bands, common, ids = response_rows(x, target, b['bidding_zone_prices'][:, j], ref[z + '_prediction'], edges)
            for row in bands:
                mask = common & (ids == row['band'] - 1)
                if not mask.any():
                    continue
                row['available_mean_mw'] = {c: float(available[mask, j, k].mean()) for k, c in enumerate(carriers)}
                row['fixed_hydro_mean_mw'] = float(r['fixed_hydro'][mask, j].mean())
                row['demand_mean_mw'] = float(r['demand'][mask, j].mean())
                row['tier_local_surplus_mean_mw'] = gap[mask, j].mean(axis=0).tolist()
            rows.append(dict(zone=z, area=area, evaluation_hours=int(common.sum()), edges_mw=edges.tolist(), bands=bands))
        np.savez_compressed(out / 'fleet.npz', zones=np.array(zones), carriers=np.array(carriers), available=available, cheap=cheap)
    ranking = sorted([dict(zone=r['zone'], **band) for r in rows for band in r['bands'] if band['hours'] >= 100], key=lambda b: -abs(b['physical_bias']))
    dependencies = {Path(v.__file__).name: digest(v.__file__) for v in list(sys.modules.values()) if getattr(v, '__file__', None) and Path(v.__file__).parent == ROOT / 'tools' and Path(v.__file__).suffix == '.py'}
    summary = dict(status='descriptive_response_and_fleet_diagnostic_not_candidate', design=design, zones=rows,
                   inventory=inventory, largest_band_biases=ranking[:20], source_hashes=sources,
                   source_mapping=mapping, source_dependencies=dependencies,
                   witness_sha256=digest(out / 'fleet.npz'), producer_sha256=digest(__file__),
                   design_sha256=digest(out / 'design.json'), preparation_seconds=prepared,
                   end_to_end_seconds=time.perf_counter() - started,
                   peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print('Completed', len(rows), 'price areas; no coefficients changed', flush=True)


if __name__ == '__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p = argparse.ArgumentParser(); p.add_argument('out', type=Path); args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    lock = (args.out / 'driver.lock').open('w'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS, (5 * 1024**3, 5 * 1024**3)); signal.alarm(1200)
    run(args.out)
