"""Four predeclared annual oil controls, with saved complete primal/dual witnesses."""
import argparse, fcntl, json, logging, resource, signal, sys, time
from pathlib import Path
import numpy as np
from oil_supply_2025 import anchor, inputs, compile_case, oil_quantities, ROOT, PLAN, CAPACITY, INPUTS, LATEST, CASE
from generation_mix_2025 import digest, MONTH
from bid_calibration_2025 import month_quantities, loss, immutable_hashes
from run_seasonal_calendar_bids_2025 import summary_prices
from joint_network_clear_2025 import clear_or_reject


def write(p, v):
    p.write_text(json.dumps(v, indent=2, allow_nan=False, default=lambda a: a.tolist()) + '\n')


def run(out):
    began = time.perf_counter(); design = json.loads(PLAN.read_text()); write(out / 'design.json', design)
    n, base, off, m, ctx, layout, c, flow, target = anchor()
    monthly, daily, co2, assumption, additions, oil = inputs(n, m, layout)
    write(out / 'oil-columns.json', dict(existing=oil, additions=additions, assumption=assumption))
    source_files = [PLAN, CAPACITY, INPUTS / 'summary.json', INPUTS / 'inputs.npz', LATEST / 'summary.json', LATEST / 'verification-v1/audit.json']
    capacity = json.loads(CAPACITY.read_text())
    source_files += [ROOT / row['raw_path'] for row in capacity['countries']]
    sources = {str(p.relative_to(ROOT)): digest(p) for p in source_files}
    prepared = time.perf_counter() - began; annuals = {}; outcomes = {}
    for key in design['cases']:
        case, context = compile_case(m, ctx, c, monthly, daily, co2, assumption, additions, oil, key)
        x, y, obj, info = clear_or_reject(case, flow, case['cost'], out / (key + '.npz'))
        annuals[key] = info
        if x is None:
            write(out / 'failure.json', annuals); raise RuntimeError('Annual oil case unresolved; no partial metrics')
        emergency = float(x[:, :case['ng']][:, case['emergency_mask']].sum()); assert emergency <= 1e-6
        mon = month_quantities(context, x, 0)
        oil_q = oil_quantities(case, x, ctx['countries'], oil, additions if key in ['missing_capacity', 'capacity_and_daily_oil'] else [])
        np.savez_compressed(out / (key + '-oil.npz'), generation_mwh=oil_q)
        metrics = summary_prices(y[:, :case['nz']], target['prices'], case['zones'])
        outcomes[key] = dict(prices=metrics, quantity_errors=loss(y[:, :case['nz']], mon, target),
                             monthly_quantities=mon, oil_generation_twh=oil_q.sum(axis=0) / 1e6,
                             oil_by_month_twh=np.array([oil_q[MONTH == month].sum(axis=0) / 1e6 for month in range(1, 13)]),
                             emergency_mwh=emergency, physical_inputs=immutable_hashes(case, flow),
                             oil_arrays_sha256=digest(out / (key + '-oil.npz')))
        if key == 'control':
            old = json.loads((LATEST / 'summary.json').read_text())['outcomes'][CASE]['prices']
            assert abs(metrics['equal_zone_mae'] - old['equal_zone_mae']) < 1e-7
        write(out / 'progress.json', dict(annuals=annuals, outcomes=outcomes))
        print(key, 'MAE', metrics['equal_zone_mae'], 'oil TWh', oil_q.sum()/1e6, flush=True)
    deps = {Path(v.__file__).name: digest(v.__file__) for v in list(sys.modules.values()) if getattr(v, '__file__', None) and Path(v.__file__).parent == ROOT/'tools' and Path(v.__file__).suffix == '.py'}
    write(out / 'summary.json', dict(status='oil_supply_controls_computed_not_promoted', design=design,
          source_hashes=sources, dependencies=deps, producer_sha256=digest(__file__), helper_sha256=digest(ROOT/'tools/oil_supply_2025.py'),
          oil_columns_sha256=digest(out/'oil-columns.json'), zones=m['zones'], countries=ctx['countries'], annuals=annuals, outcomes=outcomes,
          preparation_seconds=prepared, end_to_end_seconds=time.perf_counter()-began,
          peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))


if __name__ == '__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser(); p.add_argument('out',type=Path); out=p.parse_args().out.resolve(); out.mkdir(parents=True,exist_ok=False)
    lock=(out/'driver.lock').open('w'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3)); signal.alarm(2400); run(out)
