"""Declared scenario deltas on the retained annual joint LP.

A scenario is a frozen, explicitly declared change to the accepted physical LP:
added generator columns and scaled commercial-link capacity. Nothing here edits
the retained witness, the active baseline pointer or the fitted monthly curves.

Scope of a delta, deliberately narrow:

* a new generator is one extra offer column priced at a declared constant bid,
  available in its own zone only. It participates in the network exactly like
  every other offer, through the endogenous zonal net-injection variable.
* a link upgrade scales the hourly commercial-exchange envelope of one existing
  link column. The envelope is historical observed exchange, so releasing it is
  declared separately and never done implicitly.
* PTDF branch ratings are not modified. The model has no retained row-to-branch
  mapping, so a physical AC upgrade cannot be declared without new provenance.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import coo_matrix, hstack


@dataclass(frozen=True)
class GeneratorAddition:
    """One new offer column with a declared hourly availability profile."""

    name: str
    zone: str
    capacity_mw: float
    profile_mw: np.ndarray
    bid_eur_mwh: float = 0.0


@dataclass(frozen=True)
class LinkUpgrade:
    """One commercial link column whose observed envelope is scaled."""

    link: int
    factor: float
    release_envelope: bool


@dataclass(frozen=True)
class Scenario:
    name: str
    generators: tuple[GeneratorAddition, ...] = ()
    links: tuple[LinkUpgrade, ...] = ()


def link_endpoints(zones, nl):
    """Return the (from_zone, to_zone) pair of every link column in native order."""
    import xarray as xr

    from .network import NATIVE

    with xr.open_dataset(NATIVE) as grid:
        if len(grid['links_i']) != int(nl):
            raise ValueError('Link column count changed')
        labels = grid['buses_bidding_zone'].values.astype(str)
        labels = np.where(labels == 'ES-IB-MA', 'ES', labels)
        buses = dict(zip(grid['buses_i'].values.astype(str), labels))
        pairs = [(buses[str(a)], buses[str(b)])
                 for a, b in zip(grid['links_bus0'].values, grid['links_bus1'].values)]
    known = set(map(str, zones))
    for start, end in pairs:
        if start not in known or end not in known:
            raise ValueError(f'Link endpoint outside modeled zones: {start}->{end}')
    return pairs


def apply(model, costs, scenario):
    """Return a declared scenario copy of the LP and its extended offer costs.

    ``costs`` is the accepted annual (8760, ng) bid matrix. The accepted arrays
    are never modified in place, and a scenario without deltas must reproduce
    them exactly.
    """
    zones = [str(zone) for zone in model['zones']]
    ng, nl = int(model['ng']), int(model['nl'])
    hours = np.asarray(model['availability']).shape[0]
    bid = np.asarray(costs, dtype=float)
    if bid.shape != (hours, ng):
        raise ValueError('Offer cost matrix does not match the accepted LP')

    availability = np.array(model['availability'], dtype=float, copy=True)
    link_min = np.array(model['link_min'], dtype=float, copy=True)
    link_max = np.array(model['link_max'], dtype=float, copy=True)
    matrix = model['A'].tocsc(copy=True)

    rows, columns, values, additions = [], [], [], []
    for position, addition in enumerate(scenario.generators):
        if addition.zone not in zones:
            raise ValueError(f'Unknown generator zone: {addition.zone}')
        profile = np.asarray(addition.profile_mw, dtype=float)
        if profile.shape != (hours,):
            raise ValueError(f'{addition.name}: profile is not one full year')
        if not np.isfinite(profile).all() or profile.min() < 0:
            raise ValueError(f'{addition.name}: invalid availability profile')
        if addition.capacity_mw <= 0 or profile.max() > addition.capacity_mw * (1 + 1e-9):
            raise ValueError(f'{addition.name}: profile exceeds declared capacity')
        if not np.isfinite(addition.bid_eur_mwh):
            raise ValueError(f'{addition.name}: invalid bid')
        rows.append(zones.index(addition.zone))
        columns.append(position)
        values.append(1.0)
        additions.append(dict(name=addition.name, zone=addition.zone,
                              capacity_mw=float(addition.capacity_mw),
                              bid_eur_mwh=float(addition.bid_eur_mwh),
                              annual_gwh=float(profile.sum() / 1000),
                              column=ng + position))

    offer_zones = np.asarray(model['offer_zones']).astype(str)
    emergency_mask = np.asarray(model['emergency_mask'], dtype=bool)
    if offer_zones.size != ng or emergency_mask.size != ng:
        raise ValueError('Offer metadata does not match the accepted offer block')
    if scenario.generators:
        extra = coo_matrix((values, (rows, columns)),
                           shape=(matrix.shape[0], len(scenario.generators))).tocsc()
        # New offers must sit inside the offer block: the accepted solver reads
        # columns as [offers, links, zonal injections], so appending after the
        # injections would silently reinterpret a link column as an offer.
        matrix = hstack([matrix[:, :ng], extra, matrix[:, ng:]], format='csc')
        availability = np.column_stack([availability] + [
            np.asarray(g.profile_mw, dtype=float) for g in scenario.generators])
        bid = np.column_stack([bid, np.broadcast_to(
            np.array([g.bid_eur_mwh for g in scenario.generators], dtype=float),
            (hours, len(scenario.generators)))])
        offer_zones = np.concatenate(
            [offer_zones, np.array([g.zone for g in scenario.generators], dtype=str)])
        emergency_mask = np.concatenate(
            [emergency_mask, np.zeros(len(scenario.generators), dtype=bool)])

    upgrades = []
    for upgrade in scenario.links:
        if not 0 <= upgrade.link < nl:
            raise ValueError(f'Unknown link column: {upgrade.link}')
        if not np.isfinite(upgrade.factor) or upgrade.factor <= 0:
            raise ValueError(f'Invalid link factor: {upgrade.factor}')
        peak = float(max(abs(link_min[:, upgrade.link]).max(),
                         abs(link_max[:, upgrade.link]).max()))
        if peak <= 0:
            raise ValueError(f'Link {upgrade.link} has no observed envelope')
        if upgrade.release_envelope:
            band = upgrade.factor * peak
            link_min[:, upgrade.link] = -band
            link_max[:, upgrade.link] = band
        else:
            link_min[:, upgrade.link] *= upgrade.factor
            link_max[:, upgrade.link] *= upgrade.factor
        upgrades.append(dict(link=int(upgrade.link), factor=float(upgrade.factor),
                             release_envelope=bool(upgrade.release_envelope),
                             baseline_peak_mw=peak))

    declared = dict(model)
    declared.update(A=matrix, availability=availability, cost=bid,
                    link_min=link_min, link_max=link_max,
                    ng=ng + len(scenario.generators),
                    offer_zones=offer_zones, emergency_mask=emergency_mask)
    description = dict(name=scenario.name, generators=additions, links=upgrades)
    return declared, bid, description
