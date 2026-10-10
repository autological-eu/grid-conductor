"""Explicit price-taking thermal bids; no fitting to observed power prices.

Fuel prices are EUR/MWh of thermal input on the same heating-value basis as
efficiency. Output bids are EUR/MWh of electricity. Historical prices must be
supplied with provenance; no default fuel prices or double-counted native costs.
"""
import math
from datetime import datetime, timedelta, timezone

FUEL = {'CCGT': 'gas', 'OCGT': 'gas', 'oil': 'oil'}


def nonnegative(value, name):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError('Finite nonnegative ' + name + ' required')
    return value


def thermal_bid(fuel_eur_mwh_th, efficiency, co2_eur_t,
                emissions_t_mwh_th, variable_om_eur_mwh_el, markup_eur_mwh_el=0):
    """Return an auditable offer breakdown, replacing the native total cost."""
    efficiency = float(efficiency)
    if not math.isfinite(efficiency) or not 0 < efficiency <= 1:
        raise ValueError('Efficiency must be in (0, 1]')
    fuel = nonnegative(fuel_eur_mwh_th, 'fuel price') / efficiency
    carbon = (nonnegative(co2_eur_t, 'CO2 price') *
              nonnegative(emissions_t_mwh_th, 'operational emissions factor') / efficiency)
    om = nonnegative(variable_om_eur_mwh_el, 'variable O&M')
    markup = nonnegative(markup_eur_mwh_el, 'markup')
    cost = fuel + carbon + om
    return dict(fuel_eur_mwh_el=fuel, carbon_eur_mwh_el=carbon,
                variable_om_eur_mwh_el=om, marginal_cost_eur_mwh_el=cost,
                markup_eur_mwh_el=markup, offer_eur_mwh_el=cost + markup)


def oil_barrel_to_thermal_price(price_usd_barrel, eur_per_usd, mwh_th_per_barrel):
    """Explicit currency/heat-content conversion; Brent is not plant fuel cost."""
    heat = float(mwh_th_per_barrel)
    fx = float(eur_per_usd)
    if not math.isfinite(heat) or heat <= 0 or not math.isfinite(fx) or fx <= 0:
        raise ValueError('Positive finite heat content and EUR/USD required')
    return nonnegative(price_usd_barrel, 'oil price') * fx / heat


def validate_market(market, snapshots):
    """Require exact hourly UTC alignment; caller expands documented daily prices."""
    for field in ('gas_eur_mwh_th', 'oil_eur_mwh_th', 'co2_eur_t'):
        source = market['sources'][field]
        if not isinstance(source, str) or not source.strip():
            raise ValueError('Price source/assumption declaration required: ' + field)
    rows = market['hours']
    if len(rows) != len(snapshots) or not rows:
        raise ValueError('Exact nonempty price/calendar coverage required')
    previous = None
    for row, snapshot in zip(rows, snapshots):
        instant = datetime.fromisoformat(row['utc'].replace('Z', '+00:00'))
        if instant.tzinfo is None or instant.utcoffset() != timedelta(0):
            raise ValueError('Explicit UTC price timestamps required')
        expected = datetime.fromisoformat(str(snapshot))
        if expected.tzinfo is None:
            expected = expected.replace(tzinfo=timezone.utc)
        if instant != expected or (previous is not None and instant - previous != timedelta(hours=1)):
            raise ValueError('Price calendar missing, duplicated or misaligned')
        previous = instant
        for field in ('gas_eur_mwh_th', 'oil_eur_mwh_th', 'co2_eur_t'):
            nonnegative(row[field], field)
    return rows


def generator_offers(generators, snapshots, existing_costs, market, assumptions):
    """Replace gas/oil total offers; preserve other offers, including nuclear.

    ``assumptions`` maps each present gas/oil carrier to explicitly sourced
    variable O&M and operational factors. Costs must be unaggregated by asset.
    Availability, nuclear commitment and the network are deliberately untouched.
    """
    rows = validate_market(market, snapshots)
    if len(existing_costs) != len(rows) or any(len(r) != len(generators) for r in existing_costs):
        raise ValueError('Unaggregated hourly generator costs required')
    costs = [[float(v) for v in r] for r in existing_costs]
    if any(not math.isfinite(v) for r in costs for v in r):
        raise ValueError('Nonfinite original generator costs')
    records = []
    for j, generator in enumerate(generators):
        carrier = generator['carrier']
        if carrier not in FUEL:
            continue
        assumption = assumptions[carrier]
        if not isinstance(assumption['source'], str) or not assumption['source'].strip():
            raise ValueError('Thermal assumption source required')
        offers = []
        for t, row in enumerate(rows):
            offer = thermal_bid(row[FUEL[carrier] + '_eur_mwh_th'], generator['efficiency'],
                                row['co2_eur_t'], assumption['emissions_t_mwh_th'],
                                assumption['variable_om_eur_mwh_el'],
                                assumption.get('markup_eur_mwh_el', 0))
            costs[t][j] = offer['offer_eur_mwh_el']
            offers.append(offer)
        records.append(dict(generator=generator['name'], carrier=carrier, offers=offers))
    return costs, records


def compile_thermal_case(n, reference_model, investments, weather, market, assumptions):
    """Opt-in European compiler: replace costs BEFORE merging identical offers.

    Use this instead of compile_case for a fresh, independently verified run.
    Existing daily producers/results are not migrated implicitly. Markups are
    disabled here so solver objective remains the declared operating cost.
    """
    import numpy as np
    from european_physical_bids_2025 import compile_model
    from european_reservoir_clearing_2025 import aggregate_offers
    from perfect_foresight_dispatch import apply_investments
    if any(float(a.get('markup_eur_mwh_el', 0)) != 0 for a in assumptions.values()):
        raise ValueError('Dispatch cost compiler requires zero markup')
    base = n.copy()
    apply_investments(base, [x for x in investments if x['type'] not in ('solar', 'wind')])
    m = compile_model(base)
    if m['weights'] != reference_model['weights']:
        raise ValueError('Investment changed fixed GSK')
    apply_investments(base, [x for x in investments if x['type'] in ('solar', 'wind')], weather)
    m['availability'] = (base.get_switchable_as_dense('Generator', 'p_max_pu').values *
                         base.generators.p_nom.values)
    generators = [dict(name=str(name), carrier=g.carrier, efficiency=g.efficiency)
                  for name, g in base.generators.iterrows()]
    costs, records = generator_offers(generators, base.snapshots, m['cost'], market, assumptions)
    m['cost'] = np.asarray(costs)
    m = aggregate_offers(base, m)
    return base, m, records
