"""Dated reserve eligibility, before aggregation; two fixed annual sensitivities.

No fitted capacity, prices or bids. Original sources/witnesses remain immutable.
"""
import argparse
import fcntl
import json
import resource
import time

import numpy as np
import pandas as pd
import xarray as xr
from scipy.sparse import load_npz
from generation_mix_2025 import ROOT, digest

OUT = ROOT/'data/bidding-zone-network-2025/thermal-eligibility-v1'
ANCHOR = ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'
GRID = ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025'
POOL = ROOT/'data/bidding-zone-network-2025/january-supply-balance-v1/pooling.npz'
PLAN = ROOT/'config/thermal-eligibility-2025.json'
TARGET = ROOT/'data/price-trace/sdac-hourly-2025-v1'


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def active(clock, start, stop):
    """Inclusive start, exclusive stop; administrative dates are German local."""
    t = pd.DatetimeIndex(clock)
    if t.tz is None:
        t = t.tz_localize('UTC')
    return ((t >= pd.Timestamp(start, tz='Europe/Berlin')) &
            (t < pd.Timestamp(stop, tz='Europe/Berlin')))


def exact_unit(frame, spec):
    row = frame.loc[spec['source_row']]
    if isinstance(row, pd.DataFrame):
        raise ValueError('Duplicate source identity')
    for key, field in [('name','Name'), ('country','Country'), ('fuel','Fueltype'), ('bus','bus')]:
        if row[field] != spec[key]:
            raise ValueError('Unit identity differs: '+key)
    if abs(float(row.Capacity)-spec['source_mw']) > 1e-9:
        raise ValueError('Source capacity differs')
    return row


def remaining_scale(installed, removed, reported):
    remaining = np.asarray(installed)-np.asarray(removed)
    if np.any(removed < 0) or np.any(remaining <= 0) or np.any(reported > remaining+1e-7):
        raise ValueError('Unsupported stock reconciliation; would invent remaining capacity')
    return reported/remaining


def prepare():
    assert not (OUT/'inputs.json').exists(), 'Never overwrite sealed inputs'
    p = json.loads((ANCHOR/'inputs.json').read_text())
    s = json.loads((ANCHOR/'summary.json').read_text())
    a = json.loads((ANCHOR/'audit.json').read_text())
    assert a['summary_sha256'] == digest(ANCHOR/'summary.json')
    assert a['inputs_sha256'] == digest(ANCHOR/'inputs.json')
    assert a['status'] == 'all_35040_hourly_source_native_and_optimality_replays_passed'
    for file, sha in p['files'].items(): assert digest(ANCHOR/file) == sha
    design = json.loads(PLAN.read_text())
    plants = pd.read_csv(GRID/'powerplants_s_128.csv', index_col=0)
    pool = load_npz(POOL).toarray()
    removal = np.zeros((8760, p['ng']))
    clock = pd.date_range('2025-01-01', periods=8760, freq='h', tz='UTC')
    rows = []
    with xr.open_dataset(GRID/'networks/base_s_128_elec_.nc') as n:
        names = list(n.generators_i.values.astype(str))
        for spec in design['units']:
            unit = exact_unit(plants, spec)
            assert spec['fuel'] == 'Hard Coal'
            native = names.index(unit.bus+' coal')
            # Prove this source group really is the installed native group.
            group = plants.loc[(plants.bus == unit.bus)&(plants.Fueltype == spec['fuel'])]
            assert abs(group.Capacity.sum()-float(n.generators_p_nom[native])) < 1e-7
            mapping = pool[native]
            assert abs(mapping.sum()-1) < 1e-12 and mapping.min() >= 0
            mask = active(clock, spec['start'], spec['stop'])
            removal[mask] += spec['source_mw']*mapping
            rows.append(spec|dict(native_generator=names[native], active_hours=int(mask.sum()),
                                  offers=[dict(column=int(j), share=float(mapping[j])) for j in np.flatnonzero(mapping)]))
    source = dict(np.load(ANCHOR/'inputs.npz'))
    assert np.all(removal <= source['thermal'][0]+1e-7)
    np.savez_compressed(OUT/'removal.npz', removal=removal)
    paths = [PLAN, GRID/'powerplants_s_128.csv', GRID/'networks/base_s_128_elec_.nc', POOL,
             ANCHOR/'inputs.json', ANCHOR/'summary.json', ANCHOR/'audit.json', TARGET/'summary.json', TARGET/'audit.json', TARGET/'prices.npz']
    paths += list((OUT/'sources').glob('*'))
    for name in ['solar_interval','solar_capacity']:
        witness = ROOT/s['cases'][name]['annual']['witness']
        assert digest(witness) == s['cases'][name]['annual']['witness_sha256']
        paths.append(witness)
    # The downloaded regulator PDFs and URLs are pinned, not today's status list.
    write(OUT/'inputs.json', dict(status='sealed', producer_sha256=digest(__file__),
          design=design, units=rows, removal_sha256=digest(OUT/'removal.npz'),
          source_hashes={str(f.relative_to(ROOT)):digest(f) for f in paths},
          anchor_files=p['files'], dependencies={name:digest(ROOT/'tools'/name) for name in
             ['joint_network_clear_2025.py','nve_hydro_diagnostics.py','run_regional_water_candidate_2025.py','run_seasonal_calendar_bids_2025.py','generation_mix_2025.py']},
          removed_mw_min=float(removal.sum(axis=1).min()), removed_mw_max=float(removal.sum(axis=1).max())))


def cases(p, source, removal):
    solar = source['availability']+source['solar_aligned']-source['solar_original']
    stock = solar.copy()
    for row, vector in zip(p['capacity'], source['thermal'], strict=True):
        stock += (row['factor']-1)*vector
    # Reconcile roles BEFORE any national-stock scaling: avoid double subtraction.
    reconciled = stock.copy()
    coal = source['thermal'][0]
    scale = remaining_scale(coal.sum(), removal.sum(axis=1), p['capacity'][0]['reported_2025_mw'])
    reconciled += (coal-removal)*scale[:,None]-coal*p['capacity'][0]['factor']
    return dict(solar_control=solar, eligibility=solar-removal, stock_control=stock, reconciled=reconciled)


def run():
    from joint_network_clear_2025 import clear_or_reject
    from run_seasonal_calendar_bids_2025 import summary_prices
    sealed = json.loads((OUT/'inputs.json').read_text())
    assert sealed['producer_sha256'] == digest(__file__)
    assert sealed['removal_sha256'] == digest(OUT/'removal.npz')
    for file,sha in sealed['source_hashes'].items(): assert digest(ROOT/file) == sha
    for file,sha in sealed['dependencies'].items(): assert digest(ROOT/'tools'/file) == sha
    for file,sha in sealed['anchor_files'].items(): assert digest(ANCHOR/file) == sha
    p = json.loads((ANCHOR/'inputs.json').read_text()); s = json.loads((ANCHOR/'summary.json').read_text())
    source = dict(np.load(ANCHOR/'inputs.npz')); removal = np.load(OUT/'removal.npz')['removal']
    observed = np.load(TARGET/'prices.npz')['prices']
    base = {k:source[k] for k in ['cost','load','island_rhs','link_min','link_max','ratings','emergency_mask','offer_zones']}
    base.update(A=load_npz(ANCHOR/'network.npz'),ng=p['ng'],nl=p['nl'],nz=p['nz'],zones=p['zones'],islands=[None]*p['islands'])
    outcomes = {}
    for name, av in cases(p, source, removal).items():
        assert av.min() >= -1e-7
        if name in ['solar_control','stock_control']:
            original = 'solar_interval' if name == 'solar_control' else 'solar_capacity'
            info = s['cases'][original]['annual']|dict(reused=True)
            path = ROOT/info['witness']
            with np.load(path) as z: x,y=z['values'],z['row_duals']
        else:
            path = OUT/(name+'.npz'); assert not path.exists(), 'No implicit resume'
            x,y,_,info = clear_or_reject(base|dict(availability=av), source['flow'],source['cost'],path)
            info |= dict(witness=str(path.relative_to(ROOT)),reused=False)
            if x is None:
                write(OUT/'failure.json',dict(case=name,annual=info));raise RuntimeError('Incomplete year')
        metrics = summary_prices(y[:,:p['nz']], observed, p['zones'])
        complete = [r for r in metrics['zones'] if r['known_hours']==8760]
        assert len(complete)==41
        emergency = float(x[:,:p['ng']][:,source['emergency_mask']].sum())
        zi = p['zones'].index('DE-LU'); t=19*24+16
        de = next(r for r in complete if r['zone']=='DE-LU')
        coal_ids = source['thermal'][0]>0
        outcomes[name] = dict(annual=info,metrics=metrics,europe_mae=float(np.mean([r['mae_eur_mwh'] for r in complete])),
            german_mae=de['mae_eur_mwh'],event_price=float(y[t,zi]), emergency_mwh=emergency,
            acceptable_supply=emergency<=1e-6,german_coal_dispatch_twh=float(x[:,:p['ng']][:,coal_ids].sum()/1e6),
            german_coal_available_mw=float(av[t,coal_ids].sum()))
        write(OUT/'progress.json',outcomes)
        print(name,{k:v for k,v in outcomes[name].items() if k not in ['annual','metrics']},flush=True)
    write(OUT/'summary.json',dict(status='four_cases_complete',producer_sha256=digest(__file__),inputs_sha256=digest(OUT/'inputs.json'),cases=outcomes))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['prepare','run']);args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3))
    lock=(OUT.parent/'thermal-eligibility-v1.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    prepare() if args.stage=='prepare' else run()
