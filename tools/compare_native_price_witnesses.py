"""Inventory-witness sensitivity of provisional observed-price diagnostics.

Neither witness is inferred to be an annual optimum. Conditional nodal duals
remain distinct from observed zonal prices and accepted empirical validation.
"""
import argparse
import json
import math
from pathlib import Path

from compare_native_price_observations import compare
from monthly_dispatch import digest, save
from submonthly_inventory_driver import verify_annual


METRICS = ['bias_eur_mwh', 'mae_eur_mwh', 'rmse_eur_mwh', 'correlation']


def differences(reference, candidate):
    if (reference['status'] != 'provisional_fixed_inventory_price_diagnostic_not_validation'
            or candidate['status'] != reference['status']
            or any(candidate[key] != reference[key] for key in
                   ['year', 'hours', 'input_sha256', 'price_manifest_sha256', 'observed_price_sha256'])
            or reference['year'] != 2025 or reference['hours'] != 8760):
        raise ValueError('Same complete source and observations required')
    def index(report):
        rows = report['nodes']
        result = {row['node']: row for row in rows}
        if len(result) != len(rows):
            raise ValueError('Duplicate native price node')
        return result
    before, after = index(reference), index(candidate)
    if set(before) != set(after):
        raise ValueError('Native node domains differ')
    result = []
    for node, first in sorted(before.items()):
        second = after[node]
        if first['status'] != second['status']:
            raise ValueError('Changed node mapping or native price availability')
        row = dict(node=node, status=first['status'])
        if first['status'] == 'conditional_nodal_vs_observed_zonal_diagnostic_not_validation':
            for name in ['country', 'provisional_observed_zone', 'matched_hours']:
                if first[name] != second[name]:
                    raise ValueError('Unmatched observed geography or hourly coverage')
                row[name] = first[name]
            changes = {}
            for name in METRICS:
                a, b = first[name], second[name]
                if any(value is not None and (type(value) not in (int, float) or not math.isfinite(value))
                       for value in [a, b]):
                    raise ValueError('Nonfinite diagnostic metric')
                changes[name] = dict(reference=a, candidate=b, difference=None if a is None or b is None else b-a)
            row['metrics'] = changes
        elif first['status'] not in ['native_nodal_price_row_absent', 'unresolved_geographic_mapping']:
            raise ValueError('Unknown price interpretation status')
        result.append(row)
    return result


def audit(args):
    domain = json.loads((args.workspace/'master-workspace.json').read_text())
    source = digest(args.network)
    if source != domain['input_sha256']:
        raise ValueError('Matched original annual source required')
    reports = []
    witnesses = []
    for folder, annual in [(args.reference, args.reference_annual), (args.candidate, args.candidate_annual)]:
        cost = verify_annual(annual, domain)
        report = compare(folder, args.network, args.prices)
        if report['annual_replay_sha256'] != digest(annual/'annual-replay.json'):
            raise ValueError('Mapped prices belong to another annual witness')
        reports.append(report)
        witnesses.append(dict(id=annual.name, annual_replay_sha256=report['annual_replay_sha256'],
                              mapping_calendar_sha256=report['mapping_calendar_sha256'],
                              annual_feasible_cost_eur=cost))
    if witnesses[0]['annual_replay_sha256'] == witnesses[1]['annual_replay_sha256']:
        raise ValueError('Two distinct independently replayed inventory witnesses required')
    rows = differences(*reports)
    compared = [row for row in rows if 'metrics' in row]
    return dict(status='fixed_inventory_price_sensitivity_not_validation', year=2025, hours=8760,
                input_sha256=source, inventory_domain_sha256=digest(args.workspace/'master-workspace.json'),
                price_manifest_sha256=reports[0]['price_manifest_sha256'],
                observed_price_sha256=reports[0]['observed_price_sha256'],
                reference=witnesses[0], candidate=witnesses[1], nodes=rows,
                compared_nodes=len(compared),
                annual_feasible_cost_change_eur=witnesses[1]['annual_feasible_cost_eur']-witnesses[0]['annual_feasible_cost_eur'],
                maximum_absolute_bias_change_eur_mwh=max((abs(row['metrics']['bias_eur_mwh']['difference'])
                    for row in compared if row['metrics']['bias_eur_mwh']['difference'] is not None), default=None),
                acceptance=dict(annual_optimum=False, bidding_zone_mapping=False,
                                empirical_validation=False, investment_validation=False),
                producer_sha256=digest(Path(__file__)),
                dependencies={name:digest(Path(__file__).parent/name) for name in
                              ['compare_native_price_observations.py', 'submonthly_inventory_driver.py', 'monthly_dispatch.py']},
                limitations=['Two feasible fixed-inventory trajectories, not annual optima or solver implementations.',
                    'Same original capacities, costs and renewable availability; only linked inventory states differ.',
                    'Conditional nodal dual versus observed zonal diagnostics use provisional national mapping.',
                    'Differences of error metrics are not dispatch cost differences or investment benefits.',
                    'No empirical acceptance, held-out calibration, avoided emissions or investment validity inferred.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['workspace', 'network', 'prices', 'reference', 'candidate', 'reference-annual', 'candidate-annual', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve previous sensitivity evidence')
    report = audit(args)
    save(args.output, report)
    print(f"Compared {report['compared_nodes']} provisional price nodes; no empirical acceptance inferred.")
