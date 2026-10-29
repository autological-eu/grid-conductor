"""Load the accepted 799-offer LP and independently replay a saved witness."""
from __future__ import annotations

import json

import numpy as np
from scipy.sparse import load_npz

from .source import ROOT

ANCHOR = ROOT / 'data/bidding-zone-network-2025/annual-solar-alignment-v1'
SOLAR = ROOT / 'data/bidding-zone-network-2025/solar-country-fit-v1/delta.npz'
ANNUAL = ROOT / 'data/bidding-zone-network-2025/observed-root-fast-joint-lp-v1'


def physical_lp():
    """Construct unchanged source network and accepted solar availability."""
    metadata = json.loads((ANCHOR / 'inputs.json').read_text())
    with np.load(ANCHOR / 'inputs.npz') as archive:
        source = {key: archive[key] for key in archive.files}
    with np.load(SOLAR) as archive:
        delta = archive['delta']
    availability = source['availability'] + source['solar_aligned'] - source['solar_original']
    for row, thermal in zip(metadata['capacity'], source['thermal'], strict=True):
        availability += (row['factor'] - 1) * thermal
    availability += source['solar_aligned'] * (86 / 90 - 1) + delta
    if availability.min() < -1e-5:
        raise ValueError('Negative accepted availability')
    model = {key: source[key] for key in ('cost', 'load', 'island_rhs', 'link_min', 'link_max',
                                          'ratings', 'emergency_mask', 'offer_zones')}
    model.update(A=load_npz(ANCHOR / 'network.npz'), availability=availability,
                 ng=metadata['ng'], nl=metadata['nl'], nz=metadata['nz'],
                 zones=metadata['zones'], islands=[None] * metadata['islands'], flow=source['flow'])
    if model['ng'] != 799 or model['A'].shape != (311, 884):
        raise ValueError('Changed accepted LP dimensions')
    return model


def saved_annual():
    """Load fitted costs and the 8,760-hour original LP result, without rerunning it."""
    with np.load(ANNUAL / 'costs.npz') as archive:
        cost = archive['cost']
    with np.load(ANNUAL / 'annual.npz') as archive:
        witness = {key: archive[key] for key in archive.files}
    if cost.shape != (8760, 799) or witness['values'].shape != (8760, 884):
        raise ValueError('Changed annual witness dimensions')
    if not np.array_equal(witness['hours'], np.arange(8760)):
        raise ValueError('Annual witness lost UTC chronology')
    return cost, witness

CARRIER = {'onwind': 'onshore_wind', 'offwind-ac': 'offshore_wind',
           'offwind-dc': 'offshore_wind', 'offwind-float': 'offshore_wind',
           'solar': 'solar', 'solar-hsat': 'solar', 'nuclear': 'nuclear',
           'ror': 'ror', 'CCGT': 'gas', 'OCGT': 'gas', 'coal': 'hard_coal',
           'lignite': 'lignite', 'oil': 'oil', 'biomass': 'biomass',
           'waste': 'waste', 'geothermal': 'geothermal', 'emergency': 'emergency'}
ZERO_BID = {'onshore_wind', 'offshore_wind', 'solar', 'ror', 'geothermal'}
FIT = ROOT / 'data/eu-market/flow-adjusted-clearing-2025/aligned-mixed-flow-observed-root-v1-u20-r1'
OFFERS = ROOT / 'data/bidding-zone-network-2025/supply-bid-review-v2/offers.json'
LAYOUT = ROOT / 'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json'
TIMEZONES = {
    'AL': 'Europe/Tirane', 'AT': 'Europe/Vienna', 'BA': 'Europe/Sarajevo',
    'BE': 'Europe/Brussels', 'BG': 'Europe/Sofia', 'CH': 'Europe/Zurich',
    'CZ': 'Europe/Prague', 'DE': 'Europe/Berlin', 'DK': 'Europe/Copenhagen',
    'EE': 'Europe/Tallinn', 'ES': 'Europe/Madrid', 'FI': 'Europe/Helsinki',
    'FR': 'Europe/Paris', 'GB': 'Europe/London', 'GR': 'Europe/Athens',
    'HR': 'Europe/Zagreb', 'HU': 'Europe/Budapest', 'IE': 'Europe/Dublin',
    'IT': 'Europe/Rome', 'LT': 'Europe/Vilnius', 'LU': 'Europe/Luxembourg',
    'LV': 'Europe/Riga', 'ME': 'Europe/Podgorica', 'MK': 'Europe/Skopje',
    'NL': 'Europe/Amsterdam', 'NO': 'Europe/Oslo', 'PL': 'Europe/Warsaw',
    'PT': 'Europe/Lisbon', 'RO': 'Europe/Bucharest', 'RS': 'Europe/Belgrade',
    'SE': 'Europe/Stockholm', 'SI': 'Europe/Ljubljana',
    'SK': 'Europe/Bratislava', 'XK': 'Europe/Belgrade'}


def offer_groups(schema, lp):
    """Map accepted single-technology offers; mixed renewable pools keep old bids."""
    from .source import digest
    layout = json.loads(LAYOUT.read_text())
    audit = json.loads(OFFERS.with_name('audit.json').read_text())
    if audit['status'] != 'passed' or audit['summary_sha256'] != digest(OFFERS.with_name('summary.json')):
        raise ValueError('Offer inventory audit changed')
    rows = json.loads(OFFERS.read_text())
    if len(rows) != len(layout['members']):
        raise ValueError('Offer inventory/layout mismatch')
    keys = {(g['zone'], g['technology']): i for i, g in enumerate(schema['groups'])}
    grouped = {g: [] for g in range(len(schema['groups']))}
    mixed = []
    for j, row in enumerate(rows):
        if row['column'] != j or row['fraction'] != layout['fractions'][j] or row['zone'] != str(lp['offer_zones'][j]):
            raise ValueError('Changed accepted offer metadata')
        kinds = {CARRIER[c] for c in row['source_carriers']}
        if kinds == {'emergency'}:
            if not lp['emergency_mask'][j]:
                raise ValueError('Emergency mapping mismatch')
        elif len(kinds) != 1:
            if not kinds.issubset(ZERO_BID):
                raise ValueError('Nonrenewable mixed offer')
            mixed.append(j)
        else:
            grouped[keys[(str(lp['offer_zones'][j]), next(iter(kinds)))]].append(j)
    for j in range(len(rows), lp['ng']):
        grouped[keys[(str(lp['offer_zones'][j]), 'oil')]].append(j)
    return grouped, mixed


def sampled_anchors(anchors, fraction):
    u = np.clip(fraction, 0, 1) * 5
    left = np.minimum(u.astype(int), 4)
    low = np.take_along_axis(anchors, left[..., None], axis=-1)[..., 0]
    high = np.take_along_axis(anchors, (left + 1)[..., None], axis=-1)[..., 0]
    return low + (u - left) * (high - low)


def transferred_costs(schema, data, market, lp, fit_dir=FIT):
    """Price the existing 799 LP columns using twelve monthly bid tables."""
    import pandas as pd
    grouped, mixed = offer_groups(schema, lp)
    costs = lp['cost'].copy()
    ng = market.ng
    for month in range(1, 13):
        hours = np.flatnonzero((np.arange('2025-01-01T00', '2026-01-01T00', dtype='datetime64[h]')
                                .astype('datetime64[M]').astype(int) % 12 + 1) == month)
        with np.load(fit_dir / f'month-{month:02d}/curves.npz') as archive:
            weights = archive['weights']
        if weights.shape != (24, ng, 6):
            raise ValueError('Changed fitted curve shape')
        for start in range(0, len(hours), 168):
            chunk = hours[start:start + 168]
            utc = pd.Timestamp('2025-01-01', tz='UTC') + pd.to_timedelta(chunk, unit='h')
            clocks = np.column_stack([np.asarray(utc.tz_convert(TIMEZONES[g['zone'][:2]]).hour)
                                      for g in schema['groups']])
            theta = weights[clocks, np.arange(ng)]
            anchors = market.offers(theta, chunk)['anchors']
            for g, ids in grouped.items():
                if not ids or schema['groups'][g]['technology'] in ZERO_BID:
                    continue
                original = lp['cost'][np.ix_(chunk, ids)]
                order = np.argsort(original, axis=1, kind='stable')
                available = np.take_along_axis(lp['availability'][np.ix_(chunk, ids)], order, axis=1)
                np.testing.assert_allclose(available.sum(axis=1), data['capacity'][chunk, g], atol=1e-5, rtol=0)
                midpoint = np.cumsum(available, axis=1) - available / 2
                fraction = np.divide(midpoint, data['capacity'][chunk, g, None],
                                     out=np.zeros_like(midpoint), where=data['capacity'][chunk, g, None] > 0)
                curve = np.broadcast_to(anchors[:, g, None, :], (*fraction.shape, 6))
                costs[np.arange(len(chunk))[:, None] + chunk[0], np.asarray(ids)[order]] = sampled_anchors(curve, fraction)
    if not np.isfinite(costs).all() or len(mixed) != 104:
        raise ValueError('Transferred cost or mixed-offer audit failed')
    return costs
