"""Atlite-compatible compact wind/PV cutout. Resource parameters are immutable.

Only the nonlinear weather conversion is cached; atlite still performs its usual
annual mean, spatial matrix and layout aggregation. Unsupported methods fail.
"""
import hashlib
import json
import atlite
from atlite.convert import convert_and_aggregate

AGGREGATION = {'matrix', 'index', 'layout', 'shapes', 'shapes_crs', 'per_unit',
               'return_capacity', 'aggregate_time', 'capacity_factor',
               'capacity_factor_timeseries', 'show_progress', 'dask_kwargs'}


def resource_key(method, resource):
    payload = dict(method=method, resource=resource)
    return 'cf_'+hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]


class CompactCutout(atlite.Cutout):
    def _converted(self, method, **kwargs):
        aggregation = {k: v for k, v in kwargs.items() if k in AGGREGATION}
        resource = {k: v for k, v in kwargs.items() if k not in AGGREGATION}
        key = resource_key(method, resource)
        if key not in self.data:
            raise ValueError(f'Compact weather has no matching {method} conversion; rebuild for changed resource parameters')
        def convert_cached(data):
            return data[key]
        return convert_and_aggregate(self, convert_cached, **aggregation)

    def wind(self, **kwargs):
        return self._converted('wind', **kwargs)

    def pv(self, **kwargs):
        return self._converted('pv', **kwargs)

    def runoff(self, **kwargs):
        raise ValueError('Use the separately verified full-year hydro cutout')


def open_cutout(path, chunks='auto'):
    cutout = atlite.Cutout(path, chunks=chunks)
    if cutout.data.attrs.get('gridfix_compact') == 1:
        cutout.__class__ = CompactCutout
    return cutout
