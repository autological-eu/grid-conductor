"""Derive the independent transport corridor bounds from the native 2025 grid."""
from __future__ import annotations

import numpy as np
import xarray as xr

from .source import ROOT

NATIVE = ROOT / 'data/bidding-zone-network-2025/annual-solar-alignment-v1/native.nc'


def transport_corridors(zones, data):
    pairs = {}
    with xr.open_dataset(NATIVE) as grid:
        labels = grid['buses_bidding_zone'].values.astype(str)
        labels = np.where(labels == 'ES-IB-MA', 'ES', labels)
        buses = dict(zip(grid['buses_i'].values.astype(str), labels))
        if set(labels) != set(zones):
            raise ValueError('Native bidding zones differ')

        def add(a, b, lower, upper):
            i, j = zones.index(buses[str(a)]), zones.index(buses[str(b)])
            if i == j:
                return
            if i > j:
                i, j, lower, upper = j, i, -upper, -lower
            pair = pairs.setdefault((i, j), [np.zeros(8760), np.zeros(8760)])
            pair[0] += lower
            pair[1] += upper

        for kind in ('lines', 'transformers'):
            if kind + '_i' not in grid:
                continue
            for k in range(len(grid[kind + '_i'])):
                rating = float(grid[kind + '_s_nom'].values[k] * grid[kind + '_s_max_pu'].values[k]) / 1000
                if not np.isfinite(rating) or rating <= 0:
                    raise ValueError('Invalid thermal rating')
                add(grid[kind + '_bus0'].values[k], grid[kind + '_bus1'].values[k], -rating, rating)
        if len(grid['links_i']) != data['link_min'].shape[1]:
            raise ValueError('Link count changed')
        efficiency = grid['links_efficiency'].values if 'links_efficiency' in grid else np.ones(len(grid['links_i']))
        if not np.array_equal(efficiency, np.ones_like(efficiency)):
            raise ValueError('Signed link requires unit efficiency')
        for k in range(len(grid['links_i'])):
            add(grid['links_bus0'].values[k], grid['links_bus1'].values[k],
                data['link_min'][:, k] / 1000, data['link_max'][:, k] / 1000)
    edges = sorted(pairs)
    lower = np.column_stack([pairs[k][0] for k in edges])
    upper = np.column_stack([pairs[k][1] for k in edges])
    if not np.isfinite(lower).all() or not np.isfinite(upper).all() or (lower > upper).any():
        raise ValueError('Invalid corridor bounds')
    return np.array(edges), lower, upper
