"""Run declared investment scenarios on the retained annual joint LP.

The driver only replays the accepted LP with a frozen scenario delta. It never
changes the active baseline pointer, the retained witness or the fitted curves.
Every run is one full 8,760-hour clear with the accepted physical gates.

Usage (pinned scientific interpreter, repository root)::

    python -m baselines.compact.run_scenario candidates
    python -m baselines.compact.run_scenario plan
    python -m baselines.compact.run_scenario run [--plan PATH] [--only NAME]
    python -m baselines.compact.run_scenario report [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import numpy as np

from .evaluation import ANNUAL, physical_lp, saved_annual
from .lp import clear_hour, solver
from .metrics import (branch_congestion, compare, emergency_mwh, link_candidates)
from .scenario import (GeneratorAddition, LinkUpgrade, Scenario, apply, link_endpoints)
from .source import ROOT, digest, grouped_fit_inputs

OUT = ROOT / 'data/bidding-zone-network-2025/compact-scenarios-v1'
PROFILE_TECHNOLOGIES = ('solar', 'onshore_wind', 'offshore_wind')
DEFAULT_SOLAR_MW = (500, 1000, 2000)
DEFAULT_WIND_MW = (500, 1000, 2000)
DEFAULT_LINK_FACTORS = (1.25, 1.5, 2.0)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def read(path):
    return json.loads(Path(path).read_text())


def profile_sources(schema, data, model):
    """Use sealed technology availability, even when accepted offers are pooled.

    A new generator gets its own zonal offer column in ``scenario.apply``.
    Requiring an old pure-technology offer would discard every solar/wind
    group in this retained LP, whose renewable offers are pooled.
    """
    sources = {}
    zones = set(map(str, model['zones']))
    for group, row in enumerate(schema['groups']):
        technology, zone = str(row['technology']), str(row['zone'])
        if technology not in PROFILE_TECHNOLOGIES:
            continue
        if zone not in zones:
            raise ValueError(f'Availability source outside accepted zones: {zone}')
        capacity = np.asarray(data['capacity'][:, group], dtype=float)
        if capacity.shape != (len(model['availability']),) or not np.isfinite(capacity).all():
            raise ValueError(f'Invalid fitted capacity in {zone}/{technology}')
        if capacity.min() < -1e-5:
            raise ValueError(f'Negative fitted capacity in {zone}/{technology}')
        # The source loader tolerates a -1e-5 MW solar-correction residue; an
        # offer column cannot be negative, so clip only within that tolerance.
        capacity = np.clip(capacity, 0.0, None)
        peak = float(capacity.max())
        if peak <= 0:
            continue
        sources[(zone, technology)] = dict(group=int(group),
                                           peak_mw=peak,
                                           annual_gwh=float(capacity.sum() / 1000),
                                           capacity=capacity)
    return sources


def best_source(sources, technologies):
    """Highest annual availability zone for a technology family."""
    candidates = [(key, value) for key, value in sources.items() if key[1] in technologies]
    if not candidates:
        raise ValueError(f'No fitted availability source for {technologies}')
    return max(candidates, key=lambda item: item[1]['annual_gwh'])[0]


def baseline_evidence():
    """Accepted LP, its annual witness and the diagnostic rankings."""
    model = physical_lp()
    cost, witness = saved_annual()
    schema, data, _ = grouped_fit_inputs()
    endpoints = link_endpoints(model['zones'], model['nl'])
    return dict(model=model, cost=cost, witness=witness, schema=schema, data=data,
                endpoints=endpoints,
                sources=profile_sources(schema, data, model))


def candidates(evidence=None):
    """Baseline congestion evidence; no re-solve and no scenario delta."""
    evidence = evidence or baseline_evidence()
    links = link_candidates(evidence['model'], evidence['witness'],
                            evidence['endpoints'], evidence['model']['zones'])
    return dict(baseline=dict(witness_sha256=digest(ANNUAL / 'annual.npz')),
                links=links,
                branches=branch_congestion(evidence['model'], evidence['witness']))


def default_plan(evidence=None):
    """The declared pilot matrix: zero delta, two generator ladders, one link ladder."""
    evidence = evidence or baseline_evidence()
    ranked = link_candidates(evidence['model'], evidence['witness'],
                             evidence['endpoints'], evidence['model']['zones'])
    if not ranked:
        raise ValueError('No commercial link in the accepted model')
    solar_zone, solar_tech = best_source(evidence['sources'], ('solar',))
    wind_zone, wind_tech = best_source(evidence['sources'], ('onshore_wind', 'offshore_wind'))
    top = ranked[0]
    scenarios = [dict(name='zero-delta', kind='none')]
    for mw in DEFAULT_SOLAR_MW:
        scenarios.append(dict(name=f'gen-solar-{solar_zone}-{mw}', kind='generator',
                              zone=solar_zone, technology=solar_tech, capacity_mw=mw))
    for mw in DEFAULT_WIND_MW:
        scenarios.append(dict(name=f'gen-wind-{wind_zone}-{mw}', kind='generator',
                              zone=wind_zone, technology=wind_tech, capacity_mw=mw))
    for factor in DEFAULT_LINK_FACTORS:
        scenarios.append(dict(name=f'line-{top["from_zone"]}-{top["to_zone"]}-x{factor}',
                              kind='link', link=int(top['link']),
                              from_zone=top['from_zone'],
                              to_zone=top['to_zone'], factor=factor,
                              release_envelope=True))
    return dict(plan_version=1, baseline='mixed_curve_fitting',
                ranking_rule='highest annual absolute congestion rent in the accepted witness',
                scenarios=scenarios)


def build_scenario(entry, sources, endpoints):
    """Resolve one plan entry into a declared scenario delta."""
    if entry['kind'] == 'portfolio':
        if set(entry) != {'name', 'kind', 'assets'}:
            raise ValueError('Unrecognized portfolio field')
        assets = entry.get('assets')
        if not isinstance(assets, list) or not assets:
            raise ValueError('A portfolio needs at least one asset')
        if any(not isinstance(asset, dict) or asset.get('kind') not in {'generator', 'link'}
               for asset in assets):
            raise ValueError('Portfolio assets must be generators or existing links')
        parts = [build_scenario(dict(asset, name=f'{entry["name"]}-{i}'), sources, endpoints)
                 for i, asset in enumerate(assets)]
        links = tuple(link for part in parts for link in part.links)
        if len({link.link for link in links}) != len(links):
            raise ValueError('A portfolio cannot upgrade the same link twice')
        return Scenario(name=str(entry['name']),
                        generators=tuple(g for part in parts for g in part.generators),
                        links=links)
    if entry['kind'] == 'none':
        if set(entry) != {'name', 'kind'}:
            raise ValueError('A zero-delta case cannot contain asset fields')
        return Scenario(name=str(entry['name']))
    if entry['kind'] == 'generator':
        if set(entry) - {'name', 'kind', 'zone', 'technology', 'capacity_mw', 'bid_eur_mwh'}:
            raise ValueError('Unrecognized generator field')
        key = (str(entry['zone']), str(entry['technology']))
        if key not in sources:
            raise ValueError(f'No fitted availability source for {key}')
        source = sources[key]
        capacity = float(entry['capacity_mw'])
        if not np.isfinite(capacity) or capacity <= 0 or capacity > 100000:
            raise ValueError('Generator capacity must be in (0, 100000] MW')
        if float(entry.get('bid_eur_mwh', 0.0)) != 0:
            raise ValueError('Only zero-bid solar/wind additions are source-supported')
        profile = capacity * source['capacity'] / source['peak_mw']
        return Scenario(name=str(entry['name']), generators=(
            GeneratorAddition(name=f'{key[1]}-{key[0]}-{int(capacity)}',
                              zone=key[0], capacity_mw=capacity, profile_mw=profile,
                              bid_eur_mwh=float(entry.get('bid_eur_mwh', 0.0))),))
    if entry['kind'] == 'link':
        if set(entry) - {'name', 'kind', 'link', 'from_zone', 'to_zone', 'factor', 'release_envelope'}:
            raise ValueError('Unrecognized link field')
        start, end = str(entry['from_zone']), str(entry['to_zone'])
        if 'link' in entry:
            link = int(entry['link'])
            if not 0 <= link < len(endpoints) or endpoints[link] != (start, end):
                raise ValueError(f'Declared link {link} does not match {start}->{end}')
        else:
            matches = [k for k, pair in enumerate(endpoints) if pair == (start, end)]
            if len(matches) != 1:
                raise ValueError(f'Expected one link {start}->{end}, found {len(matches)}')
            link = matches[0]
        factor = float(entry['factor'])
        if not np.isfinite(factor) or factor <= 1 or factor > 5:
            raise ValueError('Link factor must be in (1, 5]')
        return Scenario(name=str(entry['name']), links=(
            LinkUpgrade(link=link, factor=factor,
                        release_envelope=bool(entry.get('release_envelope', True))),))
    raise ValueError(f'Unknown scenario kind: {entry["kind"]}')


def baseline_gate(model, cost, witness, hours=(0, 1, 730, 2160, 4380, 6576, 8759)):
    """Cheap accepted-LP gate: saved bids must reproduce the retained witness."""
    highs = solver(model, cost)
    for hour in hours:
        _, duals, objective, _ = clear_hour(highs, model, cost, hour)
        if abs(objective - witness['objectives'][hour]) > 0.01:
            raise ValueError(f'Hour {hour}: accepted objective changed')
        gap = float(np.abs(duals[:model['nz']] - witness['row_duals'][hour, :model['nz']]).max())
        if gap > 1e-5:
            raise ValueError(f'Hour {hour}: accepted zonal price changed by {gap} EUR/MWh')


def clear_scenario(model, cost):
    """One full-year clear under the unchanged physical gates."""
    highs = solver(model, cost)
    values = np.empty((8760, model['A'].shape[1]))
    duals = np.empty((8760, model['A'].shape[0]))
    objectives = np.empty(8760)
    residual = 0.0
    started = time.perf_counter()
    for hour in range(8760):
        values[hour], duals[hour], objectives[hour], error = clear_hour(highs, model, cost, hour)
        residual = max(residual, error)
    return dict(values=values, row_duals=duals, objectives=objectives,
                hours=np.arange(8760), optimal=np.ones(8760, bool),
                solve_seconds=time.perf_counter() - started,
                maximum_primal_residual_mw=residual)


def validate_plan(plan):
    """Reject ambiguous, unsupported or path-unsafe declarations before any solve."""
    if plan.get('plan_version') != 1 or plan.get('baseline') != 'mixed_curve_fitting':
        raise ValueError('Unsupported scenario plan or baseline')
    entries = plan.get('scenarios')
    if not isinstance(entries, list) or not entries:
        raise ValueError('Scenario plan needs at least one entry')
    names = [entry.get('name') for entry in entries]
    if any(not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', name)
           or '..' in name
           for name in names) or len(names) != len(set(names)):
        raise ValueError('Scenario names must be unique safe directory names')
    return hashlib.sha256(json.dumps(plan, sort_keys=True, allow_nan=False).encode()).hexdigest()


def run(plan, only=None, evidence=None, output=OUT):
    # The compute host is Linux; the non-blocking lock guards a shared output
    # folder and must fail before any solve rather than after it.
    import fcntl

    plan_hash = validate_plan(plan)
    if only and set(only) - {entry['name'] for entry in plan['scenarios']}:
        raise ValueError('Requested scenario is absent from the plan')
    evidence = evidence or baseline_evidence()
    model, cost, witness = evidence['model'], evidence['cost'], evidence['witness']
    # Resolve every entry up front, before touching saved runs or solving.
    resolved = {entry['name']: build_scenario(entry, evidence['sources'], evidence['endpoints'])
                for entry in plan['scenarios']}
    baseline_gate(model, cost, witness)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'job.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan_file = output / 'plan.json'
        if plan_file.exists():
            if validate_plan(read(plan_file)) != plan_hash:
                raise ValueError('Output folder already belongs to a different scenario plan')
        else:
            write(plan_file, plan)
        results = []
        for entry in plan['scenarios']:
            if only and entry['name'] not in only:
                continue
            folder = output / str(entry['name'])
            if (folder / 'annual.npz').exists():
                summary_path = folder / 'summary.json'
                if not summary_path.exists():
                    raise ValueError(f'{entry["name"]}: witness exists without a passed summary')
                prior = read(summary_path)
                if (prior.get('status') != 'scenario_replay_passed'
                        or prior.get('scenario') != entry
                        or prior.get('baseline', {}).get('witness_sha256') != digest(ANNUAL / 'annual.npz')
                        or prior.get('witness_sha256') != digest(folder / 'annual.npz')
                        or (prior.get('plan_sha256') is not None
                            and prior['plan_sha256'] != plan_hash)):
                    raise ValueError(f'{entry["name"]}: saved witness does not match this declaration')
                results.append(dict(name=entry['name'], status='skipped_existing'))
                continue
            scenario = resolved[entry['name']]
            declared, declared_cost, description = apply(model, cost, scenario)
            cleared = clear_scenario(declared, declared_cost)
            emergency = emergency_mwh(cleared['values'], declared['emergency_mask'],
                                      declared['ng'])
            if emergency > 1e-6:
                write(folder / 'failure.json',
                      dict(status='no_emergency_gate_failed', emergency_mwh=emergency,
                           scenario=entry, description=description))
                raise ValueError(f'{entry["name"]}: emergency dispatch {emergency} MWh')
            if not description['generators'] and not description['links']:
                zero_delta_gate(cleared, witness, declared['nz'])
            result = compare(model, witness, declared, cleared, description,
                             evidence['endpoints'])
            folder.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(folder / 'annual.npz', **{key: cleared[key] for key in
                                                          ('values', 'row_duals', 'objectives',
                                                           'optimal', 'hours')})
            summary = dict(
                status='scenario_replay_passed',
                plan_sha256=plan_hash,
                scenario=entry, delta=description,
                baseline=dict(witness_sha256=digest(ANNUAL / 'annual.npz'),
                              pointer_sha256=digest(ROOT / 'config/active-research-baseline.json')),
                hours=8760, optimal_hours=8760,
                maximum_primal_residual_mw=cleared['maximum_primal_residual_mw'],
                emergency_mwh=emergency, solve_seconds=cleared['solve_seconds'],
                witness_sha256=digest(folder / 'annual.npz'),
                result=result,
                limitations=[
                    'declared delta on the accepted in-sample fitted-offer LP; no forward test',
                    'fixed hydro and original renewable availability unchanged',
                    'new generator follows its zone-technology availability shape at declared nameplate',
                    'released link envelopes are a flow proxy, not verified NTC/ATC',
                    '311-row linear PTDF network; no N-1 and no AC upgrade row mapping',
                ])
            write(folder / 'summary.json', summary)
            results.append(dict(name=entry['name'], status='passed',
                                welfare_meur=result['welfare']['gain_meur']))
            print(entry['name'], result['welfare']['gain_meur'], 'M EUR', flush=True)
        return results


def zero_delta_gate(cleared, witness, nz, objective_tolerance=0.01, price_tolerance=1e-5):
    """A scenario without deltas must reproduce the retained witness exactly.

    Only zonal prices are compared: branch duals can differ between equally
    optimal primal solutions, so they are not a reproducibility witness.
    """
    objective_gap = float(np.abs(cleared['objectives'] - witness['objectives']).max())
    price_gap = float(np.abs(cleared['row_duals'][:, :int(nz)]
                             - witness['row_duals'][:, :int(nz)]).max())
    if objective_gap > objective_tolerance or price_gap > price_tolerance:
        raise ValueError(f'Zero-delta drift: objective {objective_gap}, price {price_gap}')


def report(folder=OUT, out=None):
    """Aggregate passed scenario summaries into a reviewable markdown table."""
    rows = {}
    for path in sorted(Path(folder).glob('*/summary.json')):
        summary = read(path)
        if summary.get('status') != 'scenario_replay_passed':
            continue
        result = summary['result']
        generators = '; '.join(
            f'{g["zone"]} {g["capacity_mw"]:.0f} MW: {g["income_meur"]:.1f} M EUR'
            for g in result['generators']) or '—'
        links = '; '.join(
            f'{l["from_zone"]}->{l["to_zone"]} x{l["factor"]}: '
            f'{l["baseline"]["signed_meur"]:.1f} -> {l["scenario"]["signed_meur"]:.1f} M EUR rent'
            for l in result['links']) or '—'
        name = summary['scenario']['name']
        rows[name] = (result['welfare']['gain_meur'], generators, links,
                      result['prices']['mean_abs_change_eur_mwh'], summary['emergency_mwh'])
    plan = Path(folder) / 'plan.json'
    declared = ([entry['name'] for entry in read(plan)['scenarios']] if plan.exists() else [])
    order = [name for name in declared if name in rows]
    order.extend(sorted(set(rows) - set(order)))
    lines = ['| scenario | welfare gain (M EUR) | investor income | link rent | '
             'mean absolute price change (EUR/MWh) | emergency (MWh) |',
             '| --- | --- | --- | --- | --- | --- |']
    lines += [f'| {name} | {rows[name][0]:.2f} | {rows[name][1]} | {rows[name][2]} | '
              f'{rows[name][3]:.3f} | {rows[name][4]:.3f} |' for name in order]
    text = '\n'.join(lines) + '\n'
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['candidates', 'plan', 'run', 'report'])
    parser.add_argument('--plan', type=Path, default=OUT / 'plan.json')
    parser.add_argument('--only', nargs='*', default=None)
    parser.add_argument('--out', type=Path, default=None)
    parser.add_argument('--output', type=Path, default=OUT,
                        help='Isolated folder for this plan and its full-year witnesses')
    args = parser.parse_args()
    if args.stage == 'candidates':
        write(OUT / 'candidates.json', candidates())
        print(json.dumps(read(OUT / 'candidates.json')['links'][:10], indent=2))
    elif args.stage == 'plan':
        write(args.plan, default_plan())
        print(args.plan)
    elif args.stage == 'run':
        plan = read(args.plan) if args.plan.exists() else default_plan()
        print(json.dumps(run(plan, only=args.only, output=args.output), indent=2))
    else:
        print(report(folder=args.output, out=args.out))


if __name__ == '__main__':
    main()
