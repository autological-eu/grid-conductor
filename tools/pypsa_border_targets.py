"""Paired PyPSA-Eur border capacity-relief experiments; never annualise January.

Run with the pinned upstream environment. Input must be an operational network,
not an expansion-planning result. Report all existing international AC/DC borders.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT = 'a5408e9db5402c53345d7339fffb52afe96d6e43'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def border_catalog(network, allow_zero_capacity=False):
    """Country borders, including subsea DC; exclude domestic zone boundaries.

    When allow_zero_capacity is set, placeholder assets with nonpositive or
    nonfinite nominal capacity are skipped instead of raising; such assets
    carry no power and contribute nothing to border diagnostics.
    """
    buses = network.buses
    grouped = {}
    for component, table, nominal in [('Line', network.lines, 's_nom'),
                                       ('Link', network.links, 'p_nom')]:
        for name, row in table.iterrows():
            if component == 'Link' and row.carrier != 'DC':
                continue
            a, b = (str(buses.at[row[key], 'country']) for key in ['bus0', 'bus1'])
            if not a or not b or a == 'nan' or b == 'nan':
                raise ValueError(f'Missing country for {component}/{name}')
            if a == b:
                continue
            capacity = float(row[nominal])
            if not math.isfinite(capacity) or capacity <= 0:
                if allow_zero_capacity:
                    continue
                raise ValueError(f'Invalid existing capacity for {component}/{name}')
            a, b = sorted([a, b])
            entry = grouped.setdefault(f'{a}-{b}', dict(id=f'{a}-{b}', a=a, b=b, assets=[]))
            entry['assets'].append(dict(component=component, id=str(name), nominal_mw=capacity))
    return sorted(grouped.values(), key=lambda row: row['id'])


def relax_border(network, border, additional_mw):
    """Add aggregate MW allowance, holding AC impedance and topology unchanged.

    Proportional to original nominal capacity; dynamic limits keep their hourly
    shape with a constant additive allowance. This is not a new AC circuit.
    """
    if not math.isfinite(additional_mw) or additional_mw < 0:
        raise ValueError('Additional MW must be finite and nonnegative')
    total = sum(a['nominal_mw'] for a in border['assets'])
    if total <= 0:
        raise ValueError('Empty border')
    for asset in border['assets']:
        name = asset['id']
        increment_pu = additional_mw / total
        if asset['component'] == 'Line':
            if name in network.lines_t.s_max_pu:
                network.lines_t.s_max_pu[name] += increment_pu
            else:
                network.lines.at[name, 's_max_pu'] += increment_pu
        else:
            for attr, sign in [('p_max_pu', 1), ('p_min_pu', -1)]:
                dynamic = getattr(network.links_t, attr)
                if name in dynamic:
                    dynamic[name] += sign * increment_pu
                else:
                    network.links.at[name, attr] += sign * increment_pu


def verify_operational(network, manifest, network_path):
    import pandas as pd
    expected = pd.date_range(manifest['start'], manifest['end_exclusive'],
                             freq='h', inclusive='left').tz_localize(None)
    if not network.snapshots.equals(expected):
        raise ValueError('Network must contain every requested UTC hour in order')
    if not (network.snapshot_weightings == 1).all().all():
        raise ValueError('Hourly objective/storage weights must equal one; no annualisation')
    if manifest.get('network_sha256') != digest(network_path):
        raise ValueError('Network hash does not match preparation manifest')
    if manifest.get('upstream_commit') != UPSTREAM_COMMIT:
        raise ValueError('Unrecognised PyPSA-Eur source revision')
    for table in [network.generators, network.links, network.lines, network.transformers,
                  network.storage_units, network.stores]:
        for flag in ['p_nom_extendable', 's_nom_extendable', 'e_nom_extendable']:
            if flag in table and table[flag].any():
                raise ValueError('Disable all investment decisions before baseline dispatch')
    if network.generators.empty or network.loads.empty:
        raise ValueError('Base topology has no operational generation/demand inputs')
    if not manifest.get('assumptions') or not manifest.get('sources'):
        raise ValueError('Preparation assumptions and source provenance are required')


def solve(network):
    status, condition = network.optimize(solver_name='highs', assign_all_duals=True,
                                         include_objective_constant=False)
    if status != 'ok' or condition != 'optimal':
        raise ValueError(f'Dispatch did not reach optimality: {status}/{condition}')
    cost = float(network.objective)
    if not math.isfinite(cost):
        raise ValueError('Nonfinite objective')
    shortage = network.generators.index[network.generators.carrier.isin(
        ['load', 'load shedding', 'load_shedding'])]
    if len(shortage) and (network.generators_t.p[shortage].abs() > 1e-6).any().any():
        raise ValueError('Baseline/scenario uses artificial shortage supply; do not rank its penalty as market opportunity')
    return cost


def operational_emissions(network):
    """Tonnes of direct generator CO2; missing factors are never zero-filled.

    Electricity-only formulation: fuel conversion Links/Stores need a separate
    fuel-balance account and are explicitly unsupported here.
    """
    import numpy as np
    for table in [network.links, network.stores, network.storage_units]:
        for carrier in table.carrier.unique():
            if carrier in network.carriers.index:
                factor = network.carriers.at[carrier, 'co2_emissions']
                if not np.isfinite(factor) or factor != 0:
                    raise ValueError('Emitting non-generator assets require fuel-balance accounting')
    dispatch = network.generators_t.p
    efficiency = network.get_switchable_as_dense('Generator', 'efficiency')
    factors = network.generators.carrier.map(network.carriers.co2_emissions)
    if factors.isna().any() or not np.isfinite(factors).all():
        raise ValueError('Missing/nonfinite generator emission factors')
    if not np.isfinite(efficiency.to_numpy()).all() or (efficiency <= 0).any().any():
        raise ValueError('Invalid generator efficiency')
    if not np.isfinite(dispatch.to_numpy()).all() or (dispatch < -1e-6).any().any():
        raise ValueError('Invalid generator dispatch for emissions accounting')
    hourly = (dispatch.clip(lower=0) / efficiency).mul(factors).sum(axis=1)
    return float(hourly.mul(network.snapshot_weightings.generators).sum())


def validation(network, observations):
    """Price comparison is diagnostic: nodal duals are not zonal auction prices.

    Observations carry explicit bus->bidding-zone mappings; never infer split
    market zones from country prefixes. Missing points remain missing.
    """
    results = {}
    mapping = observations.get('bus_to_zone', {})
    for zone, actual in observations.get('price_eur_mwh', {}).items():
        buses = [b for b in network.buses.index if mapping.get(str(b)) == zone]
        pairs = []
        if buses:
            predicted = network.buses_t.marginal_price[buses].mean(axis=1)
            for stamp, modelled in predicted.items():
                value = actual.get(stamp.isoformat() + 'Z')
                if value is not None and math.isfinite(value) and math.isfinite(modelled):
                    pairs.append((float(modelled), value))
        results[zone] = dict(matched_hours=len(pairs), expected_hours=len(network.snapshots),
                            mae_eur_mwh=sum(abs(a-b) for a, b in pairs)/len(pairs) if pairs else None)
    return dict(status='diagnostic_not_validated', prices=results,
                price_basis='unweighted_mean_nodal_duals_not_zonal_auction_replay',
                entsoe_quantities='pending_generation_flow_and_load_reconciliation',
                jao='pending_physical_to_market_domain_reconciliation')


def run(network_path, manifest_path, observations_path, output, additional_mw=100):
    import pypsa
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    original = pypsa.Network(network_path)
    verify_operational(original, manifest, network_path)
    borders = border_catalog(original)
    baseline = original.copy()
    baseline_cost = solve(baseline)
    try:
        baseline_co2 = operational_emissions(baseline)
        climate_error = None
    except ValueError as exc:
        baseline_co2, climate_error = None, str(exc)
    if observations_path and Path(observations_path).exists():
        observations = json.loads(Path(observations_path).read_text(encoding='utf-8'))
        if observations.get('start') != manifest['start'] or observations.get('end_exclusive') != manifest['end_exclusive']:
            raise ValueError('Observation period mismatch')
        evidence = validation(baseline, observations)
        observations_sha256 = digest(observations_path)
    else:
        evidence = dict(status='observations_unavailable',
                        price_basis=None,
                        entsoe_quantities='pending_generation_flow_and_load_reconciliation',
                        jao='pending_physical_to_market_domain_reconciliation')
        observations_sha256 = None
    nodes = []
    for country, buses in original.buses.groupby('country'):
        nodes.append(dict(id=country, x=float(buses.x.mean()), y=float(buses.y.mean())))
    report = dict(schema_version=1, status='experimental_not_validated',
                  start=manifest['start'], end_exclusive=manifest['end_exclusive'],
                  metric='system_operating_cost_reduction', unit='MEUR/period',
                  additional_mw=additional_mw, annual_opportunity_meur=None,
                  network_sha256=digest(network_path), upstream_commit=UPSTREAM_COMMIT,
                  manifest_sha256=digest(manifest_path), observations_sha256=observations_sha256,
                  pypsa_version=pypsa.__version__, baseline_cost_eur=baseline_cost,
                  baseline_co2_tonnes=baseline_co2, climate_error=climate_error,
                  climate_basis='direct_operational_generator_co2_not_lifecycle',
                  validation=evidence, nodes=nodes, targets=[])
    # Every border appears even if interrupted or failed; no missing = zero.
    for border in borders:
        report['targets'].append(dict(**border, status='pending', opportunity_meur=None,
                                      modelled_climate_opportunity_tonnes=None,
                                      modelled_opportunity_meur=None))
    write_json(output, report)
    for row in report['targets']:
        try:
            scenario = original.copy()
            relax_border(scenario, row, additional_mw)
            scenario_cost = solve(scenario)
            benefit = baseline_cost - scenario_cost
            if benefit < -max(.01, abs(baseline_cost)*1e-8):
                raise ValueError('Expanded feasible domain increased objective')
            row.update(status='experimental_not_validated',
                       modelled_opportunity_meur=max(0, benefit)/1e6,
                       scenario_cost_eur=scenario_cost)
            if baseline_co2 is not None:
                try:
                    scenario_co2 = operational_emissions(scenario)
                    row.update(scenario_co2_tonnes=scenario_co2,
                               modelled_climate_opportunity_tonnes=baseline_co2-scenario_co2)
                except ValueError as exc:
                    row['climate_error'] = str(exc)
        except (ValueError, RuntimeError) as exc:
            row.update(status='failed', error=str(exc))
        write_json(output, report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--observations', type=Path,
                        help='Optional ENTSO-E price/bus-zone observations (validation only)')
    parser.add_argument('--add-mw', default=100, type=float)
    parser.add_argument('--output', default=ROOT/'public/research/pypsa-targets.json', type=Path)
    args = parser.parse_args()
    result = run(args.network, args.manifest, args.observations, args.output, args.add_mw)
    print(json.dumps(dict(status=result['status'], borders=len(result['targets']))))
