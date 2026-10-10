"""Performance adapter for the retained daily model; bids/forecast/physics unchanged.

The original producer and coefficient builder stay frozen for archived replay.
This entry point records itself in the producer manifest and uses that same
producer for chronology, forecasts, bid rules, witnesses and native verification.
"""
import argparse
import fcntl
import logging
import resource
import signal
import time
from pathlib import Path

import highspy
import numpy as np

import terminal_daily_market as producer
from daily_market_clearing import make_solver, residual, TOL
from hourly_renewable_estimates import digest


def timed_optimal(h, p, limit, strategy=1, edge=-1):
    """HiGHS limits refer to its cumulative run clock, not this day's wall time."""
    attempts = []
    for method in ('warm_simplex', 'cold_simplex', 'cold_ipm'):
        if method == 'cold_simplex':
            h.clearSolver()
        elif method == 'cold_ipm':
            h = make_solver(p, limit, 'ipm')
        if method != 'cold_ipm':
            h.setOptionValue('solver', 'simplex')
            h.setOptionValue('simplex_strategy', strategy)
            h.setOptionValue('simplex_dual_edge_weight_strategy', edge)
        allowance = limit if method == 'cold_ipm' else min(10., limit)
        h.setOptionValue('time_limit', h.getRunTime() + allowance)
        started = time.perf_counter()
        h.run()
        info = h.getInfo()
        status = h.getModelStatus()
        attempts.append(dict(method=method, status=str(status),
                             seconds=time.perf_counter()-started,
                             simplex_iterations=info.simplex_iteration_count,
                             ipm_iterations=info.ipm_iteration_count))
        if status == highspy.HighsModelStatus.kOptimal:
            return h, attempts
    raise ValueError('Nonoptimal daily result after bounded fallback: '+str(status))


def cached_daily_lp(n, m, start, end, initial, terminal, bids, cache):
    """Reuse the invariant sparse matrix; update every time-dependent LP input."""
    hours = end-start
    if cache is None or cache['hours'] != hours:
        p = producer.daily_lp(n, m, start, end, initial, terminal, bids)
        return p, dict(hours=hours, network=n, model=m, template=p,
                       inflows=n.get_switchable_as_dense('StorageUnit', 'inflow').values,
                       capacity=(n.storage_units.p_nom*n.storage_units.max_hours).values,
                       discharge_cost=n.storage_units.marginal_cost.values)
    if cache['network'] is not n or cache['model'] is not m:
        raise ValueError('Cannot reuse a matrix across changed network/model objects')
    if start < 0 or end > len(n.snapshots):
        raise ValueError('Invalid daily horizon')
    for state in (initial, terminal):
        if (np.shape(state) != cache['capacity'].shape or not np.isfinite(state).all()
                or np.any(state < 0) or np.any(state > cache['capacity']+1e-6)):
            raise ValueError('Invalid inventory boundary')
    p = dict(cache['template'])
    nb, ns, width = p['nb'], p['ns'], p['width']
    inflow = cache['inflows'][start:end].copy()
    water = inflow.copy(); water[0] += p['phi']*initial
    lower = p['lower'].copy().reshape(hours, width)
    upper = p['upper'].copy().reshape(hours, width)
    lower[:, m['ng']:m['ng']+m['nl']] = m['link_min'][start:end]
    upper[:, :m['ng']] = m['availability'][start:end]
    upper[:, m['ng']:m['ng']+m['nl']] = m['link_max'][start:end]
    upper[:, nb:nb+ns] = bids['charge_max']
    upper[:, nb+ns:nb+2*ns] = bids['discharge_max']
    lower[-1, nb+2*ns:nb+3*ns] = bids['reachable_lower']
    upper[-1, nb+2*ns:nb+3*ns] = bids['reachable_upper']
    upper[:, nb+3*ns:] = inflow
    rl = p['row_lower'].copy().reshape(hours, p['rowwidth'])
    ru = p['row_upper'].copy().reshape(hours, p['rowwidth'])
    rl[:, :m['nz']] = m['load'][start:end]; ru[:, :m['nz']] = m['load'][start:end]
    rl[:, -ns:] = water; ru[:, -ns:] = water
    operating = np.zeros((hours, width))
    operating[:, :m['ng']] = m['cost'][start:end]
    operating[:, nb+ns:nb+2*ns] = cache['discharge_cost'] + bids['wear']
    cost = operating.copy()
    cost[:, nb:nb+ns] = -bids['buy']; cost[:, nb+ns:nb+2*ns] = bids['sell']
    p.update(cost=cost.ravel(), operating_cost=operating.ravel(), lower=lower.ravel(),
             upper=upper.ravel(), row_lower=rl.ravel(), row_upper=ru.ravel(),
             inflow=inflow, initial=initial, terminal=terminal)
    return p, cache


def clear_day(n, m, start, end, initial, terminal, bids, cache=None, limit=60):
    begin = time.perf_counter()
    p, cache = cached_daily_lp(n, m, start, end, initial, terminal, bids, cache)
    h = cache.get('solver')
    if h is None:
        h = make_solver(p, limit)
    else:
        cols = cache['columns']; rows = cache['rows']
        h.changeColsBounds(len(cols), cols, p['lower'], p['upper'])
        h.changeColsCost(len(cols), cols, p['cost'])
        h.changeRowsBounds(len(rows), rows, p['row_lower'], p['row_upper'])
    preparation = time.perf_counter()-begin
    begin = time.perf_counter()
    h, attempts = timed_optimal(h, p, limit)
    cache.update(solver=h, columns=np.arange(len(p['cost']), dtype=np.int32),
                 rows=np.arange(len(p['row_lower']), dtype=np.int32))
    seconds = time.perf_counter()-begin
    sol = h.getSolution(); x = np.asarray(sol.col_value)
    error = residual(p, x); values = x.reshape(end-start, p['width'])
    nb, ns = p['nb'], p['ns']
    charge = values[:, nb:nb+ns]; discharge = values[:, nb+ns:nb+2*ns]
    soc = values[:, nb+2*ns:nb+3*ns]; spill = values[:, nb+3*ns:]
    previous = np.vstack([initial, soc[:-1]])
    water = float(abs(soc-previous*p['phi']-charge*p['eta_c']
                      + discharge/p['eta_d']-p['inflow']+spill).max())
    cycles = int(np.count_nonzero((charge > 1e-6) & (discharge > 1e-6)))
    if error > TOL or water > TOL or cycles:
        raise ValueError('Daily physical replay/cycling failed')
    return dict(values=values,
                prices=np.asarray(sol.row_dual).reshape(end-start, p['rowwidth'])[:, :m['nz']],
                bid_objective_eur=float(p['cost']@x), operating_cost_eur=float(p['operating_cost']@x),
                maximum_primal_residual=error, maximum_water_residual=water,
                simultaneous_storage_hours=cycles, solver_seconds=seconds,
                preparation_seconds=preparation, solver_attempts=attempts), cache


def run(args):
    original_clear, original_write = producer.clear_day, producer.write_json
    adapter_sha = digest(__file__)
    def write(path, value):
        if path.name in ('manifest.json', 'summary.json'):
            manifest = value.get('provenance', value if path.name == 'manifest.json' else None)
            if manifest is not None:
                manifest['execution_driver'] = dict(file='fast_daily_market.py', sha256=adapter_sha,
                    changes='Invariant daily matrix reuse; cumulative-clock-aware solver deadlines; iteration telemetry')
                manifest['dependencies']['fast_daily_market.py'] = adapter_sha
        original_write(path, value)
    try:
        producer.clear_day, producer.write_json = clear_day, write
        producer.run(args)
    finally:
        producer.clear_day, producer.write_json = original_clear, original_write


def benchmark(reference, output, days):
    """Compare original/adapter on identical saved bids; replay is not a new year."""
    import json
    import pypsa
    from european_reservoir_clearing_2025 import setup
    from simple_resource_bids import compile_case
    from synthetic_bids_2025 import SOURCE
    reference = Path(reference)
    summary = json.loads((reference/'summary.json').read_text())
    provenance = summary['provenance']
    for name, sha in provenance['dependencies'].items():
        if digest(producer.ROOT/'tools'/name) != sha:
            raise ValueError('Retained dependency changed: '+name)
    if digest(SOURCE) != provenance['source'] or digest(producer.__file__) != provenance['producer']:
        raise ValueError('Retained source/producer changed')
    market = json.loads((reference/'fuel-inputs.json').read_text())
    if digest(reference/'fuel-inputs.json') != provenance['saved_price_inputs_sha256']:
        raise ValueError('Fuel inputs changed')
    n, original, *_ = setup()
    weather = pypsa.Network(SOURCE).get_switchable_as_dense('Generator', 'p_max_pu')
    case, m, _ = compile_case(n, original, [], weather, provenance['settings'],
                              provenance['thermal_assumptions'], market)
    terminal = np.asarray(provenance['initial_inventory_mwh'])
    row = next(r for r in summary['cases'] if r['case'] == 'baseline')
    folder = reference/'baseline'; cache = None; problems = []
    for day in range(provenance['hours']//24):
        path = folder/f'{day:03d}.npz'; receipt_path = folder/f'{day:03d}.json'
        receipt = json.loads(receipt_path.read_text())
        if (digest(path) != receipt['witness_sha256'] or
                digest(receipt_path) != row['receipts_sha256'][receipt_path.name]):
            raise ValueError('Retained witness changed')
        with np.load(path, allow_pickle=False) as a:
            witness = {k:a[k].copy() for k in a.files}
        p, cache = cached_daily_lp(case, m, day*24, day*24+24,
                                   witness['initial'], terminal, witness, cache)
        full = producer.daily_lp(case, m, day*24, day*24+24,
                                 witness['initial'], terminal, witness)
        if (p['A'] != full['A']).nnz:
            raise ValueError('Cached matrix changed')
        for key, value in full.items():
            if isinstance(value, np.ndarray):
                np.testing.assert_array_equal(p[key], value, err_msg='Day '+str(day)+' '+key)
        if day in days:
            problems.append((day, witness, receipt))
    records = []
    for label, engine in [('original', producer.clear_day), ('adapter', clear_day)]:
        cache = None; rows = []
        for day, witness, receipt in problems:
            begin = time.perf_counter()
            result, cache = engine(case, m, day*24, day*24+24, witness['initial'],
                                   terminal, witness, cache, 60)
            elapsed = time.perf_counter()-begin
            difference = result['bid_objective_eur']-receipt['bid_objective_eur']
            if abs(difference) > max(.05, abs(receipt['bid_objective_eur'])*1e-8):
                raise ValueError('Matched bid objective changed')
            price_difference = float(abs(result['prices']-witness['prices']).max())
            if price_difference > 1e-5:
                raise ValueError('Matched prices changed materially')
            rows.append(dict(day=day, elapsed_seconds=elapsed, preparation_seconds=result['preparation_seconds'],
                             solver_seconds=result['solver_seconds'], objective_difference_eur=difference,
                             maximum_primal_residual=result['maximum_primal_residual'],
                             price_maximum_difference_eur_mwh=price_difference, attempts=result['solver_attempts']))
            print(label, day, round(elapsed, 3), flush=True)
        records.append(dict(engine=label, elapsed_seconds=sum(r['elapsed_seconds'] for r in rows), days=rows))
    producer.write_json(Path(output), dict(status='matched_saved_day_benchmark',
        reference_summary_sha256=digest(reference/'summary.json'), execution_driver_sha256=digest(__file__),
        packages=provenance['packages'], coefficient_days_checked=provenance['hours']//24,
        selected_days=sorted(days), records=records,
        scope='Same saved inputs/bids; exact full-year coefficient check, representative day timings; not chronological annual runtime'))


if __name__ == '__main__':
    logging.getLogger('pypsa').setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hours', type=int, default=48)
    parser.add_argument('--investments'); parser.add_argument('--rules'); parser.add_argument('--fuel-prices')
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--time-limit', type=float, default=60)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--benchmark-reference', type=Path)
    args = parser.parse_args()
    if args.hours < 24 or args.hours > 8760 or args.hours % 24 or not np.isfinite(args.time_limit) or args.time_limit <= 0:
        parser.error('Whole UTC days and finite positive time limit required')
    resource.setrlimit(resource.RLIMIT_AS, (6*1024**3, 6*1024**3)); signal.alarm(3600)
    if args.benchmark_reference:
        if args.output.exists():
            parser.error('Fresh benchmark output required')
        benchmark(args.benchmark_reference, args.output, set(list(range(10))+[53,68,88,182,291,327,357,364]))
        raise SystemExit(0)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output/'driver.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (args.output/'manifest.json').exists():
            parser.error('Fresh output root required')
        try:
            run(args)
        except Exception as exc:
            producer.write_json(args.output/'status.json', dict(status='failed', error=str(exc)))
            raise
        producer.write_json(args.output/'status.json', dict(status='completed', summary_sha256=digest(args.output/'summary.json')))
