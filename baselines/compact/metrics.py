"""Welfare and investor-income accounting for declared scenario runs.

Two numbers are reported for every scenario and they answer different questions:

* model welfare gain — the annual reduction in total offer cost with fixed,
  price-inelastic demand. Within the fitted-offer model this equals the change
  in total surplus, because consumer payments and producer revenue cancel.
  It is bid-welfare, not verified resource cost or social welfare.
* investor income — what the added asset earns inside the same clearing. For a
  generator that is revenue minus its own declared bid cost; for a commercial
  link it is the congestion rent on the price spread across the link.
"""
from __future__ import annotations

import numpy as np

RENT_TOLERANCE_EUR = 1e-6


def zone_prices(row_duals, nz):
    """Zonal day-ahead price: dual of the zone's balance row, in zone order."""
    prices = np.asarray(row_duals, dtype=float)[:, :int(nz)]
    if not np.isfinite(prices).all():
        raise ValueError('Nonfinite zonal price in witness')
    return prices


def welfare_gain_meur(base_objectives, scenario_objectives):
    """Annual offer-cost reduction, in million EUR."""
    base = float(np.sum(base_objectives))
    scenario = float(np.sum(scenario_objectives))
    return dict(baseline_cost_meur=base / 1e6, scenario_cost_meur=scenario / 1e6,
                gain_meur=(base - scenario) / 1e6)


def generator_income(values, prices, zone_index, column, capacity_mw, bid_eur_mwh):
    """Revenue minus the asset's own declared bid cost, in million EUR."""
    dispatch = np.asarray(values, dtype=float)[:, int(column)]
    price = np.asarray(prices, dtype=float)[:, int(zone_index)]
    revenue = float(np.sum(price * dispatch))
    bid_cost = float(bid_eur_mwh) * float(dispatch.sum())
    return dict(column=int(column), dispatch_twh=float(dispatch.sum() / 1e6),
                mean_price_eur_mwh=float(price.mean()),
                revenue_meur=revenue / 1e6, bid_cost_meur=bid_cost / 1e6,
                income_meur=(revenue - bid_cost) / 1e6,
                capacity_factor=float(dispatch.sum() / (capacity_mw * len(dispatch))))


def link_rent(values, ng, link, price_from, price_to):
    """Congestion rent on one commercial link, signed and absolute."""
    flow = np.asarray(values, dtype=float)[:, int(ng) + int(link)]
    spread = np.asarray(price_to, dtype=float) - np.asarray(price_from, dtype=float)
    rent = flow * spread
    return dict(signed_meur=float(rent.sum() / 1e6),
                absolute_meur=float(np.abs(rent).sum() / 1e6),
                nonzero_hours=int(np.count_nonzero(np.abs(rent) > RENT_TOLERANCE_EUR)),
                mean_abs_spread_eur_mwh=float(np.abs(spread).mean()),
                mean_flow_mw=float(flow.mean()))


def binding_hours(values, ng, link, link_min, link_max, tolerance_mw=1e-6):
    """Hours where the link flow sits on either bound of its declared envelope."""
    flow = np.asarray(values, dtype=float)[:, int(ng) + int(link)]
    lower = np.asarray(link_min, dtype=float)[:, int(link)]
    upper = np.asarray(link_max, dtype=float)[:, int(link)]
    return int(np.count_nonzero((flow - lower <= tolerance_mw) | (upper - flow <= tolerance_mw)))


def emergency_mwh(values, emergency_mask, ng):
    """Emergency offer dispatch, which the retained gates require to be zero."""
    offers = np.asarray(values, dtype=float)[:, :int(ng)]
    mask = np.asarray(emergency_mask, dtype=bool)
    if mask.size != offers.shape[1]:
        raise ValueError('Emergency mask does not match the offer block')
    return float(offers[:, mask].sum())


def link_candidates(model, witness, endpoints, zones):
    """Rank every commercial link by annual congestion rent in the baseline."""
    zones = [str(zone) for zone in zones]
    ng, nz = int(model['ng']), int(model['nz'])
    prices = zone_prices(witness['row_duals'], nz)
    rows = []
    for link, (start, end) in enumerate(endpoints):
        rent = link_rent(witness['values'], ng, link,
                         prices[:, zones.index(start)], prices[:, zones.index(end)])
        rows.append(dict(link=link, from_zone=start, to_zone=end,
                         binding_hours=binding_hours(witness['values'], ng, link,
                                                     model['link_min'], model['link_max']),
                         **rent))
    return sorted(rows, key=lambda row: row['absolute_meur'], reverse=True)


def branch_congestion(model, witness, limit=20):
    """Rank PTDF branch rows by binding hours and shadow-price rent proxy.

    The proxy is ``|dual| * rating`` summed over hours: the congestion rent the
    retained PTDF rows collect. It is a diagnostic of where the baseline network
    binds, not a claim about any specific physical circuit.
    """
    nz, islands = int(model['nz']), len(model['islands'])
    duals = np.asarray(witness['row_duals'], dtype=float)[:, nz + islands:]
    ratings = np.asarray(model['ratings'], dtype=float)
    if duals.shape[1] != ratings.size:
        raise ValueError('Branch dual and rating dimensions differ')
    active = np.abs(duals) > 1e-7
    rows = []
    for row in range(ratings.size):
        hours = active[:, row]
        rows.append(dict(row=int(row), binding_hours=int(hours.sum()),
                         mean_abs_dual_eur_mwh=float(np.abs(duals[hours, row]).mean())
                         if hours.any() else 0.0,
                         rent_proxy_meur=float((np.abs(duals[:, row]) * ratings[row]).sum() / 1e6)))
    return sorted(rows, key=lambda row: row['rent_proxy_meur'], reverse=True)[:limit]


def generation_by_zone(model, values):
    """Total offered generation per zone, including any added scenario columns."""
    zones = [str(zone) for zone in model['zones']]
    offers = np.asarray(values, dtype=float)[:, :int(model['ng'])]
    offer_zones = np.asarray(model['offer_zones']).astype(str)
    if offer_zones.size != offers.shape[1]:
        raise ValueError('Offer-zone map does not match the offer block')
    return {zone: float(offers[:, offer_zones == zone].sum() / 1e6) for zone in zones}


def compare(base_model, base_witness, scenario_model, scenario_witness, description,
            endpoints):
    """Pair the accepted witness with one scenario witness on identical coverage."""
    zones = [str(zone) for zone in base_model['zones']]
    nz = int(base_model['nz'])
    base_prices = zone_prices(base_witness['row_duals'], nz)
    scenario_prices = zone_prices(scenario_witness['row_duals'], nz)

    generators = []
    for addition in description['generators']:
        zone_index = zones.index(addition['zone'])
        generators.append(dict(
            name=addition['name'], zone=addition['zone'],
            capacity_mw=addition['capacity_mw'],
            **generator_income(scenario_witness['values'], scenario_prices, zone_index,
                               addition['column'], addition['capacity_mw'],
                               addition['bid_eur_mwh'])))

    links = []
    for upgrade in description['links']:
        link = upgrade['link']
        start, end = endpoints[link]
        links.append(dict(
            link=link, from_zone=start, to_zone=end, factor=upgrade['factor'],
            release_envelope=upgrade['release_envelope'],
            baseline=link_rent(base_witness['values'], base_model['ng'], link,
                               base_prices[:, zones.index(start)],
                               base_prices[:, zones.index(end)]) | dict(
                binding_hours=binding_hours(base_witness['values'], base_model['ng'], link,
                                            base_model['link_min'], base_model['link_max'])),
            scenario=link_rent(scenario_witness['values'], scenario_model['ng'], link,
                               scenario_prices[:, zones.index(start)],
                               scenario_prices[:, zones.index(end)]) | dict(
                binding_hours=binding_hours(scenario_witness['values'], scenario_model['ng'],
                                            link, scenario_model['link_min'],
                                            scenario_model['link_max']))))

    price_change = (scenario_prices - base_prices).mean(axis=0)
    order = np.argsort(-np.abs(price_change))
    return dict(
        welfare=welfare_gain_meur(base_witness['objectives'], scenario_witness['objectives']),
        prices=dict(mean_abs_change_eur_mwh=float(np.abs(price_change).mean()),
                    zones=[dict(zone=zones[i], mean_change_eur_mwh=float(price_change[i]))
                           for i in order[:10]]),
        generators=generators, links=links,
        emergency=dict(
            baseline_mwh=emergency_mwh(base_witness['values'], base_model['emergency_mask'],
                                       base_model['ng']),
            scenario_mwh=emergency_mwh(scenario_witness['values'],
                                       scenario_model['emergency_mask'],
                                       scenario_model['ng'])),
        generation=dict(
            baseline_twh=generation_by_zone(base_model, base_witness['values']),
            scenario_twh=generation_by_zone(scenario_model, scenario_witness['values'])))
