"""Fixed annual PV-clock/capacity comparison; original numerical helpers stay frozen."""
import argparse
import fcntl
import gzip
import json
import logging
from pathlib import Path
import resource
import sys
import time

import numpy as np
import pandas as pd
import xarray as xr
from scipy.sparse import load_npz, save_npz
from generation_mix_2025 import ROOT, digest

OUT = ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'
JAN = ROOT/'data/bidding-zone-network-2025/january-supply-balance-v1'
MODEL = ROOT/'data/bidding-zone-network-2025/oil-chp-bids-v2'
TARGET = ROOT/'data/price-trace/sdac-hourly-2025-v1'
GRID = ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025'
WEATHER = ROOT/'data/pypsa-eur/monthly-weather/2025-12/profiles.nc'
PLAN = ROOT/'config/annual-solar-alignment-2025.json'
EU = set('AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE'.split())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def nighttime_endpoint(grid, start='2025-12-31T23:00', stop='2026-01-01T00:00'):
    """Derive a PV zero only with a conservative whole-interval nighttime proof."""
    from atlite.pv.solar_position import SolarPosition
    times = pd.date_range(start, stop, freq='min')
    ds = xr.Dataset(coords={'time': times, 'x': grid.x, 'y': grid.y,
                            'lon': grid.lon, 'lat': grid.lat})
    maximum = float(np.rad2deg(SolarPosition(ds).altitude.max().compute()))
    # Earth's rotation < .26 degrees/minute; 2 degrees also covers the documented
    # solar-position error. Large safety margin, not sunrise interpolation.
    if not np.isfinite(maximum) or maximum+2 >= 1:
        raise ValueError('Missing endpoint is not certified nighttime; retrieve source weather')
    return dict(source_time='2026-01-01T00:00Z', interval_start=start+'Z',
                maximum_sampled_altitude_degrees=maximum,
                conservative_altitude_upper_bound_degrees=maximum+2,
                samples=len(times), grid_cells=int(grid.x.size*grid.y.size),
                coefficient=0., kind='converter-derived nighttime identity; not retrieved ERA5')


def prepare():
    from oil_supply_2025 import anchor, inputs, compile_case as original_case
    from oil_chp_bids_2025 import source_inputs, compile_case
    from bid_calibration_2025 import immutable_hashes
    OUT.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter()
    prior = json.loads((MODEL/'summary.json').read_text())
    cert = json.loads((MODEL/'verification-v2/audit.json').read_text())
    assert cert['status']=='passed' and cert['summary_sha256']==digest(MODEL/'summary.json')
    n, base, off, m, ctx, layout, c, flow, target = anchor()
    monthly, daily, co2, assumption, additions, oil = inputs(n, m, layout)
    reference, _ = original_case(m, ctx, c, monthly, daily, co2, assumption, additions, oil, 'capacity_and_daily_oil')
    source = source_inputs(n, reference, layout, oil, additions)
    case, extras = compile_case(reference, source, daily, assumption, 'chp25')
    assert immutable_hashes(case, flow)==prior['outcomes']['chp25']['physical_inputs']
    assert extras==json.loads((MODEL/'tranches.json').read_text())['chp25']
    assert digest(MODEL/'chp25.npz')==prior['annuals']['chp25']['witness_sha256']
    ja = json.loads((JAN/'clearing-v1/audit.json').read_text())
    assert ja['status']=='sources_and_all_four_network_cases_replayed'
    assert ja['input_summary_sha256']==digest(JAN/'reconciliation-inputs.json')
    jp = json.loads((JAN/'reconciliation-inputs.json').read_text())
    for name, sha in jp['files'].items():
        assert digest(JAN/name)==sha
    for name, sha in jp['source_hashes'].items():
        assert digest(ROOT/name)==sha
    pool = load_npz(JAN/'pooling.npz')
    assert pool.shape[1]==case['ng']
    original = np.zeros((8760, case['ng'])); aligned = original.copy()
    countries = {}; profile_checks = {}
    records = json.loads(gzip.decompress((ROOT/'public/research/irena-capacity-2025/summary.json.gz').read_bytes()))['irena_rows']
    with xr.open_dataset(WEATHER) as grid:
        endpoint = nighttime_endpoint(grid)
    network = GRID/'networks/base_s_128_elec_.nc'
    with xr.open_dataset(network) as ds:
        names = ds.generators_i.values.astype(str); fuels = ds.generators_carrier.values.astype(str)
        nom = ds.generators_p_nom.values; cm = dict(zip(ds.buses_i.values, ds.buses_country.values))
        country = np.array([cm[b] for b in ds.generators_bus.values])
        clock = ds.snapshots_snapshot.values
        np.testing.assert_array_equal(clock, pd.date_range('2025-01-01', periods=8760, freq='h').values)
        raw_names = list(ds.generators_t_p_max_pu_i.values)
        for technology in ['solar', 'solar-hsat']:
            ids = np.flatnonzero(fuels==technology)
            raw = np.zeros((8760, len(ids)))
            with xr.open_dataset(GRID/f'profile_128_{technology}.nc') as p:
                np.testing.assert_array_equal(clock, p.time.values)
                assert p.attrs['module']=='era5'
                for k, j in enumerate(ids):
                    bus, bin_id = names[j].removesuffix(' '+technology).rsplit(' ', 1)
                    values = p.profile.sel(bus=bus, bin=int(bin_id)).isel(year=0).values
                    np.testing.assert_array_equal(values, ds.generators_t_p_max_pu[:, raw_names.index(names[j])].values)
                    raw[:, k] = values
            shifted = np.vstack([raw[1:], np.zeros((1, len(ids)))])
            for code in sorted(set(country[ids])):
                local = np.flatnonzero(country[ids]==code)
                all_ids = np.flatnonzero((country==code)&np.isin(fuels, ['solar', 'solar-hsat']))
                r = next((r for r in records if r['country']==code and r['technology']=='Solar photovoltaic'), None)
                factor = np.ones(8760)
                if r and nom[all_ids].sum()>0:
                    factor = (r['capacity_2024']['mw']+(r['capacity_2025']['mw']-r['capacity_2024']['mw'])*np.arange(8760)/8760)/nom[all_ids].sum()
                old = raw[:, local]*nom[ids[local]]*factor[:, None]
                new = shifted[:, local]*nom[ids[local]]*factor[:, None]
                original += np.asarray(old@pool[ids[local]])
                aligned += np.asarray(new@pool[ids[local]])
                row = countries.setdefault(code, dict(original_available_twh=0., aligned_available_twh=0., pv_generators=0))
                row['original_available_twh'] += float(old.sum()/1e6)
                row['aligned_available_twh'] += float(new.sum()/1e6)
                row['pv_generators'] += len(local)
            profile_checks[technology] = dict(generators=len(ids), all_8760_coefficients_match=True)
        thermal = np.array([np.asarray((nom*((country=='DE')&np.isin(fuels, types)))@pool).ravel() for types in [['coal'], ['lignite'], ['CCGT', 'OCGT']]])
    # Prove that we changed exactly PV: reconstruct the original renewable offer
    # slices against the already source-audited January arrays.
    with np.load(JAN/'reconciliation-inputs.npz') as z:
        np.testing.assert_allclose(original[288:528], z['solar_original'], rtol=0, atol=1e-7)
        np.testing.assert_allclose(aligned[288:528], z['solar_aligned'], rtol=0, atol=1e-7)
        np.testing.assert_allclose(thermal, z['thermal'], rtol=0, atol=1e-7)
    assert np.all(original <= case['availability']+1e-7)
    # Solar and wind can share an equal-price offer. Never shift that pooled
    # offer: change only the independently reconstructed PV contribution.
    arrays = {k: case[k] for k in ['availability','cost','load','island_rhs','link_min','link_max','ratings','emergency_mask','offer_zones']}
    arrays.update(flow=flow, solar_original=original, solar_aligned=aligned, thermal=thermal)
    np.savez_compressed(OUT/'inputs.npz', **arrays); save_npz(OUT/'network.npz', case['A'])
    n.export_to_netcdf(OUT/'native.nc')
    np.savez_compressed(OUT/'native-base.npz', availability=base['availability'], off=off.values)
    ta = json.loads((TARGET/'audit.json').read_text()); assert ta['summary_sha256']==digest(TARGET/'summary.json')
    ts = json.loads((TARGET/'summary.json').read_text()); assert ts['zones']==case['zones'] and ts['prices_sha256']==digest(TARGET/'prices.npz')
    import atlite.pv.irradiation as irradiation
    import atlite.pv.solar_position as solar_position
    source_paths = [PLAN, MODEL/'summary.json', MODEL/'verification-v2/audit.json', MODEL/'chp25.npz',
        JAN/'reconciliation-inputs.json', JAN/'clearing-v1/audit.json', JAN/'pooling.npz',
        TARGET/'summary.json', TARGET/'audit.json', TARGET/'prices.npz', WEATHER, network,
        GRID/'profile_128_solar.nc', GRID/'profile_128_solar-hsat.nc',
        ROOT/'public/research/irena-capacity-2025/summary.json.gz', Path(irradiation.__file__), Path(solar_position.__file__)]
    dependencies = {Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    write(OUT/'inputs.json', dict(status='annual_source_comparison_prepared', producer_sha256=digest(__file__),
        zones=case['zones'], ng=case['ng'], nl=case['nl'], nz=case['nz'], islands=len(case['islands']),
        capacity=jp['capacity'], endpoint=endpoint, countries=countries, profile_checks=profile_checks,
        reference_ng=reference['ng'], extras=extras, base_ng=base['ng'], original_ng=m['ng'],
        parents=layout['parent'], additions=additions,
        weights=base['weights'], base_offer_zones=base['offer_zones'].tolist(),
        native_off_columns=off.columns.tolist(),
        source_hashes={str(p.relative_to(ROOT)):digest(p) for p in source_paths},
        dependencies=dependencies, files={name:digest(OUT/name) for name in ['inputs.npz','network.npz','native.nc','native-base.npz']},
        preparation_seconds=time.perf_counter()-began))
    print('Prepared full-year source comparison', time.perf_counter()-began, 'seconds', flush=True)


def run():
    from joint_network_clear_2025 import clear_or_reject
    from run_seasonal_calendar_bids_2025 import summary_prices
    p = json.loads((OUT/'inputs.json').read_text()); design = json.loads(PLAN.read_text())
    assert p['producer_sha256']==digest(__file__)
    for name, sha in p['source_hashes'].items(): assert digest(ROOT/name)==sha
    for name, sha in p['files'].items(): assert digest(OUT/name)==sha
    for name, sha in p['dependencies'].items(): assert digest(ROOT/'tools'/name)==sha
    assert design['cases']==['control','solar_interval','de_capacity','solar_capacity']
    source = dict(np.load(OUT/'inputs.npz')); A = load_npz(OUT/'network.npz')
    observed = np.load(TARGET/'prices.npz')['prices']; complete = np.isfinite(observed).all(axis=0)
    assert complete.sum()==41
    base = {k:source[k] for k in ['availability','cost','load','island_rhs','link_min','link_max','ratings','emergency_mask','offer_zones']}
    base.update(A=A, ng=p['ng'], nl=p['nl'], nz=p['nz'], zones=p['zones'], islands=[None]*p['islands'])
    results = {}; began = time.perf_counter()
    for name in design['cases']:
        av = source['availability'].copy()
        if name in ['solar_interval','solar_capacity']: av += source['solar_aligned']-source['solar_original']
        if name in ['de_capacity','solar_capacity']:
            for row, vector in zip(p['capacity'], source['thermal'], strict=True): av += (row['factor']-1)*vector
        assert av.min()>-1e-7
        case = base|dict(availability=np.maximum(av,0))
        path = MODEL/'chp25.npz' if name=='control' else OUT/(name+'.npz')
        if name=='control':
            info = dict(witness=str(path.relative_to(ROOT)), witness_sha256=digest(path), clearing_seconds=0., reused=True, complete_year=True)
            with np.load(path) as z: x,y,obj=z['values'],z['row_duals'],z['objectives']; assert z['optimal'].all()
        else:
            x,y,obj,info=clear_or_reject(case,source['flow'],case['cost'],path)
            info = info|dict(witness=str(path.relative_to(ROOT)), reused=False)
        if x is None:
            write(OUT/'failure.json', dict(case=name, info=info)); raise RuntimeError('Incomplete year; no annual comparison')
        emergency = float(x[:,:p['ng']][:,source['emergency_mask']].sum())
        metrics = summary_prices(y[:,:p['nz']], observed, p['zones'])
        known = [r for r in metrics['zones'] if r['known_hours']==8760]
        assert len(known)==41
        eu = [r for r in known if ('IE' if r['zone']=='IE-SEM' else r['zone'].split('-')[0][:2]) in EU]
        results[name] = dict(annual=info, metrics=metrics, complete_zones=len(known), eu_zones=len(eu),
            europe_mae=float(np.mean([r['mae_eur_mwh'] for r in known])),
            eu_mae=float(np.mean([r['mae_eur_mwh'] for r in eu])), emergency_mwh=emergency,
            acceptable_supply=emergency<=1e-6)
        write(OUT/'progress.json', results)
        print(name,'Europe',results[name]['europe_mae'],'EU',results[name]['eu_mae'],'emergency',emergency,flush=True)
        del x,y,obj
    write(OUT/'summary.json', dict(status='four_annual_source_cases_completed', design=design, cases=results,
        producer_sha256=digest(__file__), inputs_sha256=digest(OUT/'inputs.json'), elapsed_seconds=time.perf_counter()-began))


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage', choices=['prepare','run']); args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3))
    lock=(OUT.parent/'annual-solar-alignment-v1.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    prepare() if args.stage=='prepare' else run()
