"""Hypothetical fossil coefficient shifts, not policy coverage or dispatch."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
from types import SimpleNamespace
from audit_2025_operating_cost_inputs import audit as audit_costs
from prepare_2025_eua_reference import audit as audit_auctions
from monthly_dispatch import digest, save

FOSSIL = {'coal', 'lignite', 'CCGT', 'OCGT', 'oil'}


def shifts(carriers, costs, capacities, efficiencies, factors, price):
    if (type(price) not in (int, float) or not math.isfinite(price) or price <= 0
            or len({len(v) for v in [carriers, costs, capacities, efficiencies]}) != 1):
        raise ValueError('Matching asset arrays and positive finite allowance price required')
    groups = defaultdict(list)
    for carrier, cost, capacity, efficiency in zip(carriers, costs, capacities, efficiencies):
        if carrier not in FOSSIL:
            continue
        cost, capacity, efficiency = float(cost), float(capacity), float(efficiency)
        factor = factors.get(carrier)
        if (not all(math.isfinite(v) for v in [cost, capacity, efficiency]) or capacity < 0 or efficiency <= 0
                or type(factor) not in (int, float) or not math.isfinite(factor) or factor <= 0):
            raise ValueError('Explicit positive operational fossil factor and valid asset required')
        if capacity == 0:
            continue
        surcharge = price*factor/efficiency
        groups[carrier].append((cost, surcharge, cost+surcharge))
    return [dict(carrier=carrier, positive_capacity_generators=len(values),
                 baseline_eur_mwh_min=min(v[0] for v in values), baseline_eur_mwh_max=max(v[0] for v in values),
                 hypothetical_surcharge_eur_mwh_min=min(v[1] for v in values), hypothetical_surcharge_eur_mwh_max=max(v[1] for v in values),
                 hypothetical_total_eur_mwh_min=min(v[2] for v in values), hypothetical_total_eur_mwh_max=max(v[2] for v in values))
            for carrier, values in sorted(groups.items())]


def run(args):
    import xarray as xr
    source_hash = digest(args.network)
    costs = audit_costs(args.network)
    config = costs['source_configuration']
    if config['cost_year'] != 2025 or config['emission_price_enabled'] or config['configured_carbon_price_eur_tco2'] != 0 or config['time_varying_cost_or_efficiency_fields']:
        raise ValueError('Zero-price static source required; no implicit double pricing or dynamic approximation')
    auction = audit_auctions(SimpleNamespace(archive=args.archive, manifest=args.manifest, workbook=args.workbook))
    price = auction['volume_weighted_price_eur_tco2']
    with xr.open_dataset(args.network) as ds:
        factors = {str(k): float(v) for k, v in zip(ds['carriers_i'].values, ds['carriers_co2_emissions'].values)}
        rows = shifts([str(v) for v in ds['generators_carrier'].values], ds['generators_marginal_cost'].values,
                      ds['generators_p_nom'].values, ds['generators_efficiency'].values, factors, price)
    if digest(args.network) != source_hash:
        raise ValueError('Source changed during read-only coefficient audit')
    tools = Path(__file__).parent
    return dict(status='hypothetical_operational_eua_cost_coefficients_not_dispatch_or_policy_validation', year=2025,
                input_sha256=source_hash, source_configuration=config, allowance_reference=auction, coefficient_ranges=rows,
                formula='delta cost [EUR/MWh electrical] = price [EUR/tCO2] * fuel factor [tCO2/MWh thermal] / efficiency',
                producer_sha256=digest(Path(__file__)), dependencies={name:digest(tools/name) for name in
                    ['audit_2025_operating_cost_inputs.py','prepare_2025_eua_reference.py','monthly_dispatch.py']},
                limitations=['Hypothetical coefficient shifts wherever the allowance price applies; no jurisdiction or asset-eligibility assertion.',
                    'Annual auction-volume-weighted reference is not hourly spot/futures prices or a fitted power-price parameter.',
                    'Per-asset costs are paired with their own efficiency; ranges do not combine unrelated extrema.',
                    'Source costs/availability/storage and dispatch are unchanged; no new network variant or solve.',
                    'Operational CO2 factors are not lifecycle CO2e factors or avoided emissions.',
                    'Separate country/asset policy coverage, matched baselines and re-solves are required before interpreting market effects.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['network','archive','manifest','workbook','output']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve previous coefficient diagnostic')
    save(args.output, run(args))
    print('Prepared hypothetical fossil coefficient ranges; no source or dispatch changed.')
