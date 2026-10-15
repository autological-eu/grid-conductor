"""Quantity diagnostics with explicit equal-bid allocation and missingness."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ['onshore_wind', 'offshore_wind', 'solar', 'nuclear', 'ror', 'reservoir',
            'gas', 'hard_coal', 'lignite', 'oil', 'biomass', 'waste', 'geothermal', 'emergency']
CARRIER = {'onwind':'onshore_wind', 'offwind-ac':'offshore_wind', 'offwind-dc':'offshore_wind',
           'offwind-float':'offshore_wind', 'solar':'solar', 'solar-hsat':'solar',
           'nuclear':'nuclear', 'ror':'ror', 'CCGT':'gas', 'OCGT':'gas', 'coal':'hard_coal',
           'lignite':'lignite', 'oil':'oil', 'biomass':'biomass', 'waste':'waste',
           'geothermal':'geothermal', 'emergency':'emergency'}
PSR = {'onshore_wind':'B19', 'offshore_wind':'B18', 'solar':'B16', 'nuclear':'B14',
       'ror':'B11', 'reservoir':'B12', 'gas':'B04', 'hard_coal':'B05', 'lignite':'B02',
       'oil':'B06', 'biomass':'B01', 'waste':'B17', 'geothermal':'B09'}
EMBER = {'Wind':['onshore_wind','offshore_wind'], 'Solar':['solar'], 'Nuclear':['nuclear'],
         'Hydro':['ror','reservoir'], 'Gas':['gas'], 'Coal':['hard_coal','lignite'],
         'Bioenergy':['biomass'], 'Other fossil':['oil','waste'], 'Other renewables':['geothermal']}
MONTH = (np.arange('2025-01-01T00', '2026-01-01T00', dtype='datetime64[h]').astype('datetime64[M]').astype(int) % 12 + 1)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def allocate(availability, dispatch, groups, keys, labels):
    """Sharp individual-label bounds; proportional point preserves grouped dispatch.

    Bounds for different labels are not jointly attainable in general.
    """
    point = np.zeros((len(dispatch), len(labels)))
    lower = np.zeros_like(point); upper = np.zeros_like(point); caps = np.zeros_like(point)
    if set(keys) - set(labels) - {None}:
        raise ValueError('Unmapped allocation label')
    for k, ids in enumerate(groups):
        total = availability[:, ids].sum(axis=1); q = dispatch[:, k]
        if (q < -1e-4).any() or (q > total + 1e-4).any():
            raise ValueError('Grouped dispatch violates original available MW')
        q = np.clip(q, 0., total)
        for label in set(keys[i] for i in ids):
            if label is None:
                continue
            j = labels.index(label); selected = [i for i in ids if keys[i] == label]
            a = availability[:, selected].sum(axis=1)
            point[:, j] += np.divide(q * a, total, out=np.zeros_like(q), where=total > 0)
            lower[:, j] += np.maximum(0., q - (total - a))
            upper[:, j] += np.minimum(q, a)
            caps[:, j] += a
    return point, lower, upper, caps


def quantity_metrics(model, observed, lower, upper):
    known = np.isfinite(observed)
    out = dict(known_hours=int(known.sum()), expected_hours=len(observed))
    if not known.any():
        return out | dict(status='unavailable_not_zero')
    p, o = model[known], observed[known]; error = p - o
    r = float(np.corrcoef(p, o)[0, 1]) if len(o) > 1 and p.std() > 1e-8 and o.std() > 1e-8 else None
    return out | dict(status='complete_reported_hours' if known.all() else 'matched_hours_only_not_annualised',
        model_twh=float(p.sum()/1e6), observed_twh=float(o.sum()/1e6),
        lower_twh=float(lower[known].sum()/1e6), upper_twh=float(upper[known].sum()/1e6),
        bias_mw=float(error.mean()), mae_mw=float(abs(error).mean()), rmse_mw=float(np.sqrt((error**2).mean())),
        correlation=r, outside_allocation_range_hours=int(((o < lower[known]-1.) | (o > upper[known]+1.)).sum()))


def ember_rows(path):
    result = {}
    with path.open() as f:
        for row in csv.DictReader(f):
            if not row['Date'].startswith('2025-') or row['Area type'] not in ['Country','Country or economy']:
                continue
            if not row['Generation (TWh)'].strip():
                continue
            name = row['Electricity source']
            if name not in set(EMBER) | {'Demand','Net imports','Total generation'}:
                continue
            key = (row['ISO 3 code'], name, int(row['Date'][5:7]))
            if key in result:
                raise ValueError('Duplicate Ember country/type/month')
            value = float(row['Generation (TWh)'])
            if not np.isfinite(value) or (value < 0 and name != 'Net imports'):
                raise ValueError('Invalid Ember energy')
            result[key] = value
    return result


def observations(replay, country_areas, sources):
    """National source domains or every required constituent zone; never partial sums."""
    area_data = {}
    for area in replay['zones']:
        array = np.full((8760, len(FAMILIES)+3), np.nan)
        for record in area['monthly']:
            if record['status'] != 'raw_interval_energy_replayed':
                continue
            path = ROOT / f"data/carbon-pilot/map-2025/{area['zone']}/{record['month']:02d}.json"
            assert digest(path) == record['processed_sha256']
            sources[str(path.relative_to(ROOT))] = digest(path)
            for row in json.loads(path.read_text()):
                t = int((np.datetime64(row['start'].removesuffix('Z')) - np.datetime64('2025-01-01T00')).astype('timedelta64[h]').astype(int))
                for family, code in PSR.items():
                    if code in row['generation_mwh_by_type']:
                        array[t, FAMILIES.index(family)] = row['generation_mwh_by_type'][code]
                if row['primary_generation_mwh'] is not None:
                    array[t, -3] = row['primary_generation_mwh']
                for col, code in [(-2,'B10'), (-1,'B25')]:
                    if code in row['generation_mwh_by_type']:
                        array[t, col] = row['generation_mwh_by_type'][code]
        area_data[area['zone']] = array
    combined = []; coverage = []
    for country, areas in country_areas.items():
        missing = [a for a in areas if a not in area_data or np.isnan(area_data[a]).all()]
        if not areas or missing:
            combined.append(np.full((8760, len(FAMILIES)+3), np.nan))
        else:
            # np.sum propagates a missing type/hour from any constituent area.
            combined.append(np.stack([area_data[a] for a in areas]).sum(axis=0))
        coverage.append(dict(country=country, expected_areas=areas, missing_areas=missing,
                             scope='reported national/domain scope and gross/net boundaries remain unreconciled'))
    return np.stack(combined, axis=1), coverage
