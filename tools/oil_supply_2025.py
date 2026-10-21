"""Targeted, source-backed oil additions to the frozen joint/weekly model."""
import json
from pathlib import Path
import numpy as np
from scipy.sparse import hstack, coo_matrix
from generation_mix_2025 import ROOT, digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from bid_calibration_2025 import prepare, immutable_hashes
from hourly_offer_curves_2025 import compile_curves
from seasonal_calendar_bids_2025 import bids
from inverse_bid_ensemble_2025 import costs
from weekly_supply_bids_2025 import offers
from nve_hydro_diagnostics import branch_offsets
from hybrid_fixed_hydro_2025 import verified_fuel, FUEL
from simple_resource_bids import cost_assumptions
from collect_oil_capacity_2025 import parse

LATEST = ROOT / 'data/bidding-zone-network-2025/weekly-bids-v1'
ACCEPTED = ROOT / 'data/bidding-zone-network-2025/seasonal-calendar-v1'
CASE = 'inverse_joint-nordic_higher-w100'
INPUTS = ROOT / 'data/fuel-prices/daily-inputs-v1'
CAPACITY = ROOT / 'data/oil-market-2025/capacity.json'
PLAN = ROOT / 'config/oil-supply-2025.json'


def anchor():
    s = json.loads((LATEST / 'summary.json').read_text())
    audit = json.loads((LATEST / 'verification-v1/audit.json').read_text())
    assert audit['summary_sha256'] == digest(LATEST / 'summary.json')
    for p, sha in s['source_hashes'].items():
        assert digest(ROOT / p) == sha
    for p, sha in s['dependencies'].items():
        assert digest(ROOT / 'tools' / p) == sha
    old = json.loads((ACCEPTED / 'summary.json').read_text())
    joint = ROOT / 'data/bidding-zone-network-2025/joint-network-calibration-v4'
    js = json.loads((joint / 'summary.json').read_text())
    prior = ROOT / js['prior_inverse_folder']; ps = json.loads((prior / 'summary.json').read_text())
    n, raw, fixed, *_ = build(); base, off = compile_global(n, raw, fixed, 'bidding_zone')
    flow = branch_offsets(n, off)
    m, ctx, layout = compile_curves(base, prepare(n, base, raw, fixed))
    assert immutable_hashes(m, flow) == old['expanded_physical_inputs']
    with np.load(ACCEPTED / 'calendar.npz') as z:
        cal, season, shares = z['features'], z['season'], z['country_shares']
    prop = json.loads((ACCEPTED / 'proposal-refit.json').read_text())
    c = bids(m, layout, cal, season, np.array(prop['beta']), np.array(prop['gamma']), shares, old['refit_variant'])
    state = json.loads((prior / (js['bid_parent'] + '-parameters.json')).read_text())
    c = costs(m, layout, c, cal[:, :, [0, 1, 2, 3, 4]], shares, state, ps['design'])
    coef = json.loads((LATEST / 'coefficients.json').read_text())[CASE]['coefficients']
    c = offers(m, layout, c, np.array(coef))
    catalogue = json.loads((joint / 'branches.json').read_text())
    m['ratings'] = m['ratings'] * np.array([1.15 if b['nordic'] else 1. for b in catalogue])
    rec = next(r for r in s['results'] if r['anchor'] == CASE)
    assert immutable_hashes(m, flow) == rec['physical_inputs']
    from inverse_bid_ensemble_2025 import fingerprint
    assert fingerprint(c) == rec['bid_sha256']
    with np.load(ACCEPTED / 'development-targets.npz') as z:
        target = {k: z[k] for k in z.files}
    with np.load(ACCEPTED / 'evaluation-targets.npz') as z:
        target = {k: np.concatenate([v, z[k]]) for k, v in target.items()}
    return n, base, off, m, ctx, layout, c, flow, target


def inputs(n, m, layout):
    market = verified_fuel(FUEL); assumptions, _ = cost_assumptions()
    monthly = np.array([r['oil_eur_mwh_th'] for r in market['hours']])
    co2 = np.array([r['co2_eur_t'] for r in market['hours']])
    summary = json.loads((INPUTS / 'summary.json').read_text())
    assert digest(INPUTS / 'inputs.npz') == summary['inputs_sha256']
    assert digest(INPUTS / 'brent-quotes-2025.csv') == summary['eia']['quote_csv_sha256']
    for p, sha in summary['sources'].items():
        assert digest(ROOT / p) == sha
    with np.load(INPUTS / 'inputs.npz') as z:
        daily = z['oil']
    capacity = json.loads(CAPACITY.read_text()); rows = capacity['countries']
    for row in rows:
        path = ROOT / row['raw_path']; assert digest(path) == row['sha256']
        assert parse(path.read_bytes(), row['domain'])['mw'] == row['mw']
    additions = []
    for country in json.loads(PLAN.read_text())['capacity_fill_countries']:
        assert country in m['zones'] and sum(z.startswith(country) for z in m['zones']) == 1
        old = n.generators[(n.generators.carrier == 'oil') & n.generators.bus.map(n.buses.country).eq(country)].p_nom.sum()
        assert old == 0, 'Never overwrite an existing fleet with a missing-capacity rule'
        mw = next(r['mw'] for r in rows if r['country'] == country)
        assert mw > 0
        additions.append(dict(country=country, zone=country, mw=mw, efficiency=.35))
    oil = []
    for j, members in enumerate(layout['members']):
        selected = [i for i in members if n.generators.iloc[i].carrier == 'oil']
        if not selected:
            continue
        assert selected == members, 'Do not average oil and unrelated resource bids'
        efficiency = n.generators.iloc[selected].efficiency.to_numpy()
        assert np.ptp(efficiency) < 1e-10
        labels = n.generators.iloc[selected].bus.map(n.buses.country)
        weights = n.generators.iloc[selected].p_nom.groupby(labels).sum()
        oil.append(dict(column=j, zone=str(m['offer_zones'][j]), efficiency=float(efficiency[0]),
                        countries={k: float(v / weights.sum()) for k, v in weights.items()}))
    return monthly, daily, co2, assumptions['oil'], additions, oil


def compile_case(m, ctx, c, monthly, daily, co2, assumption, additions, oil, key):
    if key not in json.loads(PLAN.read_text())['cases']:
        raise ValueError('Undeclared annual case')
    fuel = daily if key in ['daily_oil', 'capacity_and_daily_oil'] else monthly
    cost = c.copy()
    for row in oil:
        cost[:, row['column']] += (fuel - monthly) / row['efficiency']
    result = m.copy(); context = ctx.copy()
    if key in ['missing_capacity', 'capacity_and_daily_oil']:
        ng, count = m['ng'], len(additions)
        cols = coo_matrix((np.ones(count), ([m['zones'].index(r['zone']) for r in additions], np.arange(count))), shape=(m['A'].shape[0], count)).tocsc()
        result['A'] = hstack([m['A'][:, :ng], cols, m['A'][:, ng:]], format='csc')
        result['ng'] = ng + count
        extra = np.tile([r['mw'] for r in additions], (8760, 1))
        result['availability'] = np.c_[m['availability'], extra]
        result['offer_zones'] = np.r_[m['offer_zones'], [r['zone'] for r in additions]]
        result['emergency_mask'] = np.r_[m['emergency_mask'], np.zeros(count, bool)]
        extra_cost = np.column_stack([(fuel + co2 * assumption['emissions_t_mwh_th']) / r['efficiency'] + assumption['variable_om_eur_mwh_el'] for r in additions])
        cost = np.c_[cost, extra_cost]
        first = ctx['availability'].shape[1]
        context['availability'] = np.c_[ctx['availability'], extra]
        context['groups'] = ctx['groups'] + [[first + j] for j in range(count)]
        context['generation_keys'] = ctx['generation_keys'] + [None] * count
        context['country_keys'] = ctx['country_keys'] + [r['country'] for r in additions]
    result['cost'] = cost
    return result, context


def oil_quantities(m, x, countries, oil, additions):
    q = np.zeros((8760, len(countries)))
    for row in oil:
        for country, share in row['countries'].items():
            q[:, countries.index(country)] += x[:, row['column']] * share
    original_ng = max([r['column'] for r in oil], default=-1)
    # Appended columns are identified by the explicitly added count, not oil ordering.
    if additions:
        for j, row in enumerate(additions):
            q[:, countries.index(row['country'])] += x[:, m['ng'] - len(additions) + j]
    return q
