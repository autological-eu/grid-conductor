"""Guarded first-January chunk diagnostic; never an annual optimisation result.

Uses original native availability and coefficients, with inventory boundaries from
an existing sequential dispatch. A shorter block tests solver scalability only.
"""
import argparse
import gc
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from audit_annual_warm_state import guard_reason, terminate_worker
from monthly_dispatch import digest, save


def worker(args):
    import math
    import numpy as np
    import pypsa
    from prepare_annual_coordination import validate_calendar
    from pypsa_storage_blocks import block
    from storage_coordinator import solve_block
    from check_storage_dual_bounds import objective_support

    source = json.loads((args.sequential / '01.json').read_text())
    if digest(args.input) != source['input_sha256']:
        raise ValueError('Prepared source differs from sequential input')
    if digest(args.sequential / '01.nc') != source['result_sha256']:
        raise ValueError('Sequential dispatch fingerprint mismatch')
    network = pypsa.Network(args.input)
    validate_calendar(network, 2025)
    # Only fixed-capacity transmission-volume constraints were permitted above.
    network.global_constraints.drop(network.global_constraints.index, inplace=True)
    reference = pypsa.Network(args.sequential / '01.nc')
    snapshots = network.snapshots[:args.hours]
    if not reference.snapshots[:args.hours].equals(snapshots):
        raise ValueError('Reference chunk chronology mismatch')
    ids = network.storage_units.index
    state = np.r_[network.storage_units.state_of_charge_initial.to_numpy(),
                  reference.storage_units_t.state_of_charge.loc[snapshots[-1]].reindex(ids).to_numpy()]
    prepared = block(network, snapshots, 0, 1)
    del network, reference
    gc.collect()
    if args.native_no_crossover:
        from native_storage_solver import solve_native
        result = solve_native(prepared, state, time_limit=args.solver_seconds)
        local = None if result is None else (result, None)
    else:
        local = solve_block(prepared, state, time_limit=args.solver_seconds,
                            first_method='highs-ipm', residual_tolerance=1e-7,
                            primal_tolerance=1e-7)
    if local is None:
        raise RuntimeError('Fixed chunk inventories reported infeasible')
    result, _ = local
    candidate = result.x
    if args.native_no_crossover:
        from sparse_primal_correction import correct_sparse
        candidate, checks = correct_sparse(prepared, state, candidate)
        if not checks['original_unit_gate_passed']:
            raise RuntimeError('Corrected native primal fails original-unit gate')
    eq = float(np.max(abs(prepared.equality @ candidate + prepared.coupling @ state - prepared.rhs), initial=0))
    ub = float(np.max(prepared.inequality @ candidate + prepared.inequality_coupling @ state - prepared.limit, initial=0))
    bound = max([0.] + [lo - x for x, (lo, hi) in zip(candidate, prepared.bounds) if lo is not None]
                + [x - hi for x, (lo, hi) in zip(candidate, prepared.bounds) if hi is not None])
    if max(eq, ub, bound) > 1e-7:
        raise RuntimeError('Original-unit primal gate failed')
    upper = math.fsum(float(c) * float(x) for c, x in zip(prepared.cost, candidate))
    gradient, intercept = objective_support(prepared, state, result)
    lower = float(intercept + gradient @ state)
    if not np.isfinite(lower) or not np.isfinite(upper) or lower > upper + 1e-7:
        raise RuntimeError('Original-unit primal/dual consistency gate failed')
    save(args.output / 'result.json', dict(
        status='fixed_chunk_numerical_gates_passed', hours=args.hours,
        backend='native-highs-no-crossover' if args.native_no_crossover else 'scipy-highs',
        dependency_sha256={name:digest(Path(__file__).with_name(name)) for name in ['native_storage_solver.py','pypsa_storage_blocks.py','storage_coordinator.py','check_storage_dual_bounds.py','sparse_primal_correction.py']},
        start=str(snapshots[0]), last=str(snapshots[-1]),
        input_sha256=digest(args.input), sequential_result_sha256=source['result_sha256'],
        tool_sha256=digest(Path(__file__)),
        cost_eur=upper, dual_support_eur=lower, local_gap_eur=upper-lower,
        max_equality_residual=eq, max_inequality_violation=max(0., ub), max_bound_violation=bound,
        scope='Fixed initial/final January inventories; scalability diagnostic only. Not annual optimisation or empirical validation.'))


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / 'status.json').exists() or (args.output / 'result.json').exists():
        raise ValueError('Use a new diagnostic output directory; do not overwrite results')
    started = time.monotonic()
    command = [sys.executable, __file__, '--input', str(args.input), '--sequential', str(args.sequential),
               '--output', str(args.output), '--hours', str(args.hours), '--solver-seconds', str(args.solver_seconds), '--worker']
    if args.native_no_crossover:command.append('--native-no-crossover')
    with (args.output / 'worker.log').open('w') as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        save(args.output / 'status.json', dict(status='running', pid=child.pid, hours=args.hours))
        peak = 0
        while child.poll() is None:
            try:
                rss = sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
            except FileNotFoundError:
                rss = 0
            peak = max(peak, rss)
            elapsed = time.monotonic() - started
            reason = guard_reason(elapsed, rss, 6., args.wall_seconds)
            if reason:
                terminate_worker(child)
                save(args.output / 'status.json', dict(status=reason, peak_rss_bytes=peak, elapsed_seconds=elapsed))
                raise RuntimeError(reason)
            time.sleep(1)
        elapsed = time.monotonic() - started
        if child.returncode:
            save(args.output / 'status.json', dict(status='failed_not_accepted', returncode=child.returncode, peak_rss_bytes=peak, elapsed_seconds=elapsed))
            raise RuntimeError('Chunk diagnostic failed; inspect worker.log')
    result = json.loads((args.output / 'result.json').read_text())
    result.update(peak_rss_bytes=peak, elapsed_seconds=elapsed)
    save(args.output / 'result.json', result)
    save(args.output / 'status.json', dict(status='completed', hours=args.hours, peak_rss_bytes=peak, elapsed_seconds=elapsed))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--sequential', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--hours', type=int, choices=[24, 168], default=168)
    parser.add_argument('--solver-seconds', type=float, default=120.)
    parser.add_argument('--wall-seconds', type=float, default=480.)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--native-no-crossover', action='store_true', help='Isolated native IPM diagnostic; coordinator default unchanged')
    args = parser.parse_args()
    if not 0 < args.solver_seconds <= 300 or not 0 < args.wall_seconds <= 1020:
        parser.error('Resource limit outside diagnostic bounds')
    worker(args) if args.worker else run(args)
