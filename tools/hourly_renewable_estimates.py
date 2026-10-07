"""Weather-based available MW and separate monthly-constrained generation estimates.

Original PyPSA-Eur capacity/ERA5-derived availability stays unchanged. Monthly
reconstruction is descriptive, not an availability input or out-of-sample test.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def reconstruct(shape, capacity, target):
    shape = np.asarray(shape, dtype=float)
    if not np.isfinite(shape).all() or np.any(shape < 0) or not np.isfinite(capacity) or capacity <= 0:
        raise ValueError('Finite nonnegative shape and positive capacity required')
    if np.any(shape > capacity + 1e-7): raise ValueError('Availability exceeds installed capacity')
    if not np.isfinite(target) or target < 0: raise ValueError('Invalid monthly energy')
    maximum = float(np.count_nonzero(shape > 0) * capacity)
    if target > maximum + 1e-6: return None, 'target_exceeds_positive_weather_support'
    if target == 0: return np.zeros_like(shape), 'zero_reported_generation'
    if maximum == 0: return None, 'no_weather_support'
    lo, hi = 0., 1.
    while float(np.minimum(shape * hi, capacity).sum()) < target - 1e-7:
        hi *= 2
        if hi > 2**60: return None, 'scaling_limit'
    for _ in range(90):
        mid = (lo + hi) / 2
        if np.minimum(shape * mid, capacity).sum() < target: lo = mid
        else: hi = mid
    values = np.minimum(shape * hi, capacity)
    if abs(float(values.sum()) - target) > max(1e-5, target * 1e-10):
        raise ValueError('Monthly reconstruction does not reconcile')
    return values, 'monthly_constrained_shape_not_availability'


def observations(path):
    receipt = json.loads((path.parent/'receipt.json').read_text())
    if digest(path) != receipt['sha256']: raise ValueError('Ember cache changed')
    result = {}
    with path.open() as f:
        for r in csv.DictReader(f):
            if (not r['Date'].startswith('2025') or r['Category'] != 'Electricity generation'
                or r['Subcategory'] != 'Fuel' or r['Variable'] not in ['Wind','Solar'] or r['Unit'] != 'TWh'
                or r['Area type'] not in ['Country','Country or economy']): continue
            key = (r['ISO 3 code'], r['Variable'].lower(), int(r['Date'][5:7]))
            if key in result: raise ValueError('Duplicate national month/fuel')
            value = float(r['Value']) * 1e6
            if not np.isfinite(value) or value < 0: raise ValueError('Invalid observed generation')
            result[key] = value
    return result, receipt


def run(network, ember, output):
    import pycountry
    if output.exists(): raise ValueError('Preserve existing estimate output')
    observed, receipt = observations(ember)
    rows = []; arrays = {}
    with xr.open_dataset(network) as d:
        hours = pd.DatetimeIndex(d.snapshots_snapshot.values)
        expected = pd.date_range('2025-01-01','2026-01-01',freq='h',inclusive='left')
        if not hours.equals(expected): raise ValueError('Exact 8760 UTC hours required')
        if not np.all(d.snapshots_generators.values == 1): raise ValueError('Hourly energy weights required')
        country = dict(zip(d.buses_i.values, d.buses_country.values))
        names = list(d.generators_i.values)
        varying = set(d.generators_t_p_max_pu_i.values)
        for code in sorted(set(country.values())):
            entry = pycountry.countries.get(alpha_2=code)
            if entry is None and code != 'XK': raise ValueError('Unsupported country identity')
            iso = 'XKX' if code == 'XK' else entry.alpha_3
            for tech, carriers in [('solar', {'solar','solar-hsat'}), ('wind', {'onwind','offwind-ac','offwind-dc','offwind-float'})]:
                indices = [i for i,n in enumerate(names) if country[d.generators_bus.values[i]] == code and d.generators_carrier.values[i] in carriers]
                if not indices: continue
                capacity = float(d.generators_p_nom.values[indices].sum())
                if capacity <= 0: continue
                available = np.zeros(8760)
                for i in indices:
                    if names[i] not in varying: raise ValueError('Renewable asset missing hourly weather profile')
                    cf = d.generators_t_p_max_pu.sel(generators_t_p_max_pu_i=names[i]).values
                    if not np.isfinite(cf).all() or np.any(cf < 0) or np.any(cf > 1 + 1e-7): raise ValueError('Invalid weather availability')
                    available += d.generators_p_nom.values[i] * cf
                key = code + '_' + tech
                arrays[key+'_available_mw'] = available
                generated = np.full(8760, np.nan)
                months = []
                for month in range(1,13):
                    mask = hours.month == month
                    target = observed.get((iso,tech,month))
                    status = 'missing_observation'
                    if target is not None:
                        values,status = reconstruct(available[mask],capacity,target)
                        if values is not None: generated[mask] = values
                    energy = float(available[mask].sum())
                    months.append(dict(month=month,available_energy_mwh=energy,observed_generation_mwh=target,
                        observed_to_available_ratio=None if target is None or energy == 0 else target/energy,status=status))
                arrays[key+'_reconstructed_generation_mw'] = generated
                rows.append(dict(country=code,technology=tech,capacity_mw=capacity,assets=len(indices),
                    available_energy_mwh=float(available.sum()),months=months))
    output.mkdir(parents=True)
    np.savez_compressed(output/'hourly.npz',hours_utc=expected.values,**arrays)
    report = dict(status='weather_availability_and_descriptive_reconstruction_not_dispatch_validation',
        year=2025,hours=8760,network_sha256=digest(network),ember_sha256=digest(ember),
        ember_url=receipt['source_url'],hourly_sha256=digest(output/'hourly.npz'),producer_sha256=digest(__file__),
        capacity_scope='Fixed source fleet capacities; additions/retirements during year not reconstructed',
        geography='National aggregation of prepared model assets, not split bidding zones',
        method='Monthly bisection scale of weather shape, capped at installed MW; original availability arrays unchanged',
        limitations=['Old Ember long-format release; current-release reconciliation pending.',
            'Monthly fits are descriptive and cannot validate hourly timing or capacity.',
            'Fitted generation can exceed original weather availability; never use it as dispatch availability.',
            'Model fleet/layout/weather conversion, curtailment and accounting differences remain unreconciled.',
            'No hydro/thermal hourly reconstruction, carbon intensity or scenario solve claimed.'],countries=rows)
    (output/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('Prepared',len(rows),'national technology series, each with 8760 hours')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['network','ember','output']: p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();run(a.network,a.ember,a.output)
