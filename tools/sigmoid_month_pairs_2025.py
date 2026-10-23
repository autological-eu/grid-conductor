"""Shared sigmoid technology curves, isolated month pairs, and exact LP checks."""
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.optimize import least_squares
from generation_mix_2025 import ROOT, MONTH, EMBER, CARRIER, digest

OUT = ROOT / 'data/bidding-zone-network-2025/sigmoid-month-pairs-v1'
PLAN = ROOT / 'config/sigmoid-month-pairs-2025.json'
FAMILIES = list(EMBER)
TECH = [v for v in CARRIER.values() if v != 'emergency']
TECH = list(dict.fromkeys(TECH))
FAMILY = {tech: family for family, types in EMBER.items() for tech in types}


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def split(train, test):
    if train not in [1, 3, 5, 7, 9, 11] or test != train+1:
        raise ValueError('Require an odd month and its immediate even successor')
    return np.flatnonzero(MONTH == train), np.flatnonzero(MONTH == test)


def local_features(zones):
    from intraday_offer_bids_2025 import TIMEZONES
    clock = pd.date_range('2025-01-01', periods=8760, freq='h', tz='UTC')
    features = np.ones((8760, len(zones), 5))
    for j, zone in enumerate(zones):
        h = clock.tz_convert(TIMEZONES[zone[:2]]).hour.to_numpy()
        features[:, j, 1:] = np.column_stack([f(2*np.pi*k*h/24) for k in [1, 2] for f in [np.sin, np.cos]])
    return features


def prepare():
    """Keep current physics, replace inherited fitted costs/PV with source inputs."""
    import pypsa
    from scipy.sparse import hstack, save_npz
    from europe_linked_clearing_2025 import load
    from hybrid_fixed_hydro_2025 import resource_costs, verified_fuel, FUEL
    from simple_resource_bids import cost_assumptions
    from solar_fleet_audit_2025 import load as physical_load
    start = time.perf_counter()
    design = json.loads(PLAN.read_text())
    _, active, p, source, m, _, _, reference, layout_path = load()
    # This control has generic PV losses, but no fitted annual country factor.
    _, _, _, av = physical_load()
    av += source['solar_aligned'] * (86/90-1)
    anchor = ROOT / 'data/bidding-zone-network-2025/annual-solar-alignment-v1'
    fleet = ROOT / 'data/bidding-zone-network-2025/solar-fleet-audit-v1'
    n = pypsa.Network(anchor/'native.nc')
    raw_cost = resource_costs(n, None, verified_fuel(FUEL), cost_assumptions()[0], 'resource_bids')
    native_av = n.get_switchable_as_dense('Generator', 'p_max_pu').to_numpy()*n.generators.p_nom.to_numpy()
    countries_by_native = [str(n.buses.loc[g.bus, 'country']) for _, g in n.generators.iterrows()]
    tech_by_native = [CARRIER[g.carrier] for _, g in n.generators.iterrows()]
    fi = json.loads((fleet/'inputs.json').read_text())
    assert digest(fleet/'components.npz') == fi['components_sha256']
    with np.load(fleet/'components.npz') as z:
        pv = z['pv']*(86/90); mapping = z['mapping']
    pv_pool = pv @ mapping
    layout = json.loads(layout_path.read_text())
    comparison = ROOT / 'data/bidding-zone-network-2025/europe-linked-clearing-robust-v1/observed-comparison-v1'
    cs = json.loads((comparison/'summary.json').read_text())
    assert digest(comparison/'hourly-comparison.npz') == cs['hourly_sha256']
    for path, sha in cs['sources'].items():
        assert digest(ROOT/path) == sha, path
    countries = cs['countries']
    groups = {}; emergency = []
    def add(zone, country, tech, capacity, cost, parent):
        if np.max(capacity) < 1e-8:
            return
        key = (zone, country, tech, digest_bytes(cost))
        if key in groups:
            groups[key]['capacity'] += capacity
        else:
            groups[key] = dict(zone=zone, country=country, technology=tech, family=FAMILY[tech], capacity=capacity.copy(), cost=cost.copy(), parent=parent)
    error = 0.
    for j in range(p['original_ng']):
        if source['emergency_mask'][j]:
            emergency.append(j); continue
        ids = layout['members'][j]; fraction = layout['fractions'][j]
        nonpv = [i for i in ids if tech_by_native[i] != 'solar']
        denom = native_av[:, nonpv].sum(axis=1)*fraction
        remainder = np.maximum(av[:, j]-pv_pool[:, j], 0)
        assert not ((denom < 1e-9) & (remainder > 1e-5)).any()
        parts = []
        for country, tech in sorted({(countries_by_native[i], tech_by_native[i]) for i in nonpv}):
            selected = [i for i in nonpv if (countries_by_native[i], tech_by_native[i]) == (country, tech)]
            cap = native_av[:, selected].sum(axis=1)*fraction
            cap = np.divide(cap*remainder, denom, out=np.zeros(8760), where=denom > 0)
            cost = source['cost'][:, j] if tech == 'oil' else raw_cost[:, selected[0]]
            add(str(source['offer_zones'][j]), country, tech, cap, cost, j); parts.append(cap)
        for country in sorted(set(fi['native_countries'])):
            selected = [i for i, c in enumerate(fi['native_countries']) if c == country and mapping[i, j] > 0]
            if selected:
                cap = pv[:, selected] @ mapping[selected, j]
                add(str(source['offer_zones'][j]), country, 'solar', cap, np.zeros(8760), j); parts.append(cap)
        error = max(error, float(abs(sum(parts, np.zeros(8760))-av[:, j]).max()))
    assert error < 1e-5
    for j in range(p['original_ng'], p['ng']):
        country = next(r['country'] for r in p['additions'] if r['zone'] == source['offer_zones'][j]) if j < p['reference_ng'] else None
        if country is None:
            parent = next(r['parent'] for r in p['extras'] if r['column'] == j)
            ids = layout['members'][parent]
            cc = set(countries_by_native[i] for i in ids); assert len(cc) == 1
            country = cc.pop()
        add(str(source['offer_zones'][j]), country, 'oil', av[:, j], source['cost'][:, j], j)
    gg = list(groups.values()); pairs = sorted({(r['country'], r['family']) for r in gg})
    K = design['segments']; parents = []; group_id = []; fractions = []
    for i, r in enumerate(gg):
        parents.extend([r['parent']]*K); group_id.extend([i]*K); fractions.extend([1/K]*K)
    parents.extend(emergency)
    A = hstack([m['A'][:, parents], m['A'][:, p['ng']:]], format='csc')
    cap = np.column_stack([r.pop('capacity') for r in gg]); cost = np.column_stack([r.pop('cost') for r in gg])
    original_total = av[:, ~source['emergency_mask']].sum(axis=1)
    np.testing.assert_allclose(cap.sum(axis=1), original_total, rtol=0, atol=1e-5)
    for r in gg:
        r['parameter'] = pairs.index((r['country'], r['family']))
        r['zone_id'] = p['zones'].index(r['zone']); r['country_id'] = countries.index(r['country'])
    arrays = dict(capacity=cap, source_cost=cost, emergency_cost=source['cost'][:, emergency], emergency_available=av[:, emergency],
                  load=source['load'], island_rhs=source['island_rhs'], link_min=source['link_min'], link_max=source['link_max'],
                  flow=source['flow'], ratings=source['ratings'], features=local_features(p['zones']))
    # Only raw observations feed fitting; baseline quantities below are evaluation-only.
    with np.load(comparison/'hourly-comparison.npz') as z:
        arrays.update(observed_generation=z['observed_generation'], accepted_generation=z['baseline_generation'], accepted_prices=z['baseline_prices'])
    target = ROOT / 'data/price-trace/sdac-hourly-2025-v1'
    ts = json.loads((target/'summary.json').read_text()); assert ts['zones'] == p['zones'] and digest(target/'prices.npz') == ts['prices_sha256']
    arrays['observed_prices'] = np.load(target/'prices.npz')['prices']
    from generation_mix_2025 import ember_rows
    import pycountry
    bankpath = ROOT/'data/pypsa-eur/ember-current-release/monthly.csv'
    receipt = json.loads(bankpath.with_name('receipt.json').read_text()); assert digest(bankpath) == receipt['sha256']
    bank = ember_rows(bankpath); monthly = np.full((12, len(countries), len(FAMILIES)), np.nan)
    for ci, c in enumerate(countries):
        iso = 'XKX' if c == 'XK' else pycountry.countries.get(alpha_2=c).alpha_3
        for f, family in enumerate(FAMILIES):
            for month in range(1, 13):
                if (iso, family, month) in bank:
                    monthly[month-1, ci, f] = bank[iso, family, month]
    arrays['ember'] = monthly
    # Derive fixed reservoir directly from the independently checked unchanged witness.
    arrays['fixed_generation'] = np.zeros_like(arrays['observed_generation'])
    ti = cs['technologies'].index('reservoir')
    arrays['fixed_generation'][:, :, ti] = arrays['accepted_generation'][:, :, ti]
    OUT.mkdir(exist_ok=False)
    np.savez_compressed(OUT/'inputs.npz', **arrays); save_npz(OUT/'network.npz', A)
    paths = [PLAN, layout_path, anchor/'inputs.json', anchor/'inputs.npz', anchor/'network.npz', anchor/'native.nc', fleet/'inputs.json', fleet/'components.npz',
             comparison/'summary.json', comparison/'hourly-comparison.npz', bankpath, bankpath.with_name('receipt.json'), target/'prices.npz', target/'summary.json',
             FUEL, ROOT/'data/fuel-prices/daily-inputs-v1/inputs.npz', ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/costs_2025_processed.csv']
    sources = {str(path.relative_to(ROOT)):digest(path) for path in paths}
    dependencies = {f:digest(ROOT/'tools'/f) for f in ['sigmoid_month_pairs_2025.py', 'generation_mix_2025.py', 'europe_linked_clearing_2025.py', 'solar_fleet_audit_2025.py', 'hybrid_fixed_hydro_2025.py', 'simple_resource_bids.py', 'global_bidding_zone_2025.py', 'run_regional_water_candidate_2025.py']}
    write(OUT/'inputs.json', dict(design=design, groups=gg, parameters=[list(v) for v in pairs], countries=countries, technologies=cs['technologies'],
          families=FAMILIES, zones=p['zones'], ng=len(parents), nl=p['nl'], nz=p['nz'], original_ng=p['ng'], emergency_count=len(emergency),
          producer_sha256=digest(__file__), sources=sources, dependencies=dependencies, input_sha256=digest(OUT/'inputs.npz'), network_sha256=digest(OUT/'network.npz'),
          maximum_partition_error_mw=error, preparation_seconds=time.perf_counter()-start, active_baseline=active['model']+'/'+active['annual_case']))
    print('Prepared', len(gg), 'source groups,', len(pairs), 'country/resource parameter sets,', len(parents), 'LP offers', flush=True)


def digest_bytes(a):
    import hashlib
    return hashlib.sha256(np.asarray(a).tobytes()).hexdigest()


def load():
    from scipy.sparse import load_npz
    sealed = json.loads((OUT/'inputs.json').read_text())
    assert sealed['producer_sha256'] == digest(__file__)
    for path, sha in sealed['sources'].items():
        assert digest(ROOT/path) == sha, path
    for path, sha in sealed['dependencies'].items():
        assert digest(ROOT/'tools'/path) == sha, path
    assert digest(OUT/'inputs.npz') == sealed['input_sha256'] and digest(OUT/'network.npz') == sealed['network_sha256']
    with np.load(OUT/'inputs.npz') as z:
        data = {k:z[k] for k in z.files}
    return sealed, data, load_npz(OUT/'network.npz')


def offer_costs(theta, groups, source_cost, features, K, bound=80):
    pi = np.array([r['parameter'] for r in groups]); zi = np.array([r['zone_id'] for r in groups])
    shift = np.clip(np.einsum('tgf,gf->tg', features[:, zi], theta[pi, :5]), -bound, bound)
    spread = np.exp(theta[pi, 5]); quantiles = logit((np.arange(K)+.5)/K)
    # Inverse logistic sampled at volume-bin midpoints. Each bin is divisible.
    return (source_cost[:, :, None] + shift[:, :, None] + spread[None, :, None]*quantiles).reshape(len(source_cost), -1)


def neutral(sealed):
    theta = np.zeros((len(sealed['parameters']), 6)); theta[:, 5] = np.log(sealed['design']['spread_prior_eur_mwh'])
    return theta


def generation(sealed, data, values, hours):
    K = sealed['design']['segments']; G = len(sealed['groups'])
    q = values[:, :G*K].reshape(len(hours), G, K).sum(axis=2)
    out = data['fixed_generation'][hours].copy()
    for j, group in enumerate(sealed['groups']):
        out[:, group['country_id'], sealed['technologies'].index(group['technology'])] += q[:, j]
    return out


def metric(sealed, data, prices, gen, hours, month):
    target = data['observed_prices'][hours]
    complete = np.isfinite(data['observed_prices']).all(axis=0)
    mae = float(abs(prices[:, complete]-target[:, complete]).mean())
    monthly = np.zeros((len(sealed['countries']), len(FAMILIES)))
    for f, family in enumerate(FAMILIES):
        ids = [sealed['technologies'].index(t) for t in EMBER[family]]
        monthly[:, f] = gen[:, :, ids].sum(axis=(0, 2))/1e6
    observed = data['ember'][month-1]; known = np.isfinite(observed)
    err = abs(monthly-observed); normal = err/np.maximum(observed, sealed['design']['generation_floor_twh'])
    return dict(price_mae=mae, generation_mae_twh=float(err[known].mean()), generation_normalized_mae=float(normal[known].mean()),
                generation_cells=int(known.sum()), price_zones=int(complete.sum())), monthly


def penalty(theta, sealed):
    return float(sealed['design']['ridge']*np.mean(np.c_[theta[:, :5]/80, (theta[:, 5]-np.log(12))[:, None]/np.log(100)]**2))


def objective(metrics, theta, sealed):
    d = sealed['design']
    return d['price_weight']*metrics['price_mae']/d['price_scale_eur_mwh'] + d['generation_weight']*metrics['generation_normalized_mae'] + penalty(theta, sealed)


def inverse_fit(sealed, data, hours, control_prices, train_month):
    """Use only supplied training rows; no access to even-month observations."""
    d = sealed['design']; groups = sealed['groups']; theta = neutral(sealed); records = []
    price = data['observed_prices'][hours].copy(); imputed = ~np.isfinite(price)
    price[imputed] = control_prices[imputed]
    for k, (country, family) in enumerate(sealed['parameters']):
        ci = sealed['countries'].index(country); ids = [j for j, g in enumerate(groups) if g['parameter'] == k]
        zi = [groups[j]['zone_id'] for j in ids]
        cap = data['capacity'][hours][:, ids]; cost = data['source_cost'][hours][:, ids]
        features = data['features'][hours][:, zi]
        ti = [sealed['technologies'].index(t) for t in EMBER[family]]
        observed = data['observed_generation'][hours, ci][:, ti]
        valid = np.isfinite(observed).all(axis=1)
        fixed = data['fixed_generation'][hours, ci][:, ti].sum(axis=1)
        hourly = observed.sum(axis=1)-fixed
        obs_month = data['ember'][train_month-1, ci, FAMILIES.index(family)]
        fixed_twh = fixed.sum()/1e6
        scale = max(float(np.mean(hourly[valid])) if valid.any() else 0., 1000.)
        def residual(v):
            shift = np.clip(np.einsum('tgf,f->tg', features, v[:5]), -80, 80)
            q = (cap*expit((price[:, zi]-cost-shift)/np.exp(v[5]))).sum(axis=1)
            parts = []
            if valid.any():
                parts.append((q[valid]-hourly[valid])/scale/np.sqrt(valid.sum()))
            if np.isfinite(obs_month):
                parts.append(np.array([(q.sum()/1e6+fixed_twh-obs_month)/max(obs_month, .25)]))
            parts.append(np.sqrt(d['ridge'])*np.r_[v[:5]/80, (v[5]-np.log(12))/np.log(100)])
            return np.concatenate(parts)
        support = int(valid.sum())
        if support or np.isfinite(obs_month):
            result = least_squares(residual, theta[k], bounds=(np.r_[np.full(5, -80), np.log(1)], np.r_[np.full(5, 80), np.log(100)]), max_nfev=d['inverse_max_evaluations'], ftol=1e-7)
            theta[k] = result.x
            records.append(dict(country=country, family=family, hourly_targets=support, monthly_target=bool(np.isfinite(obs_month)), converged=bool(result.success), evaluations=int(result.nfev), inverse_loss=float(result.fun@result.fun)))
        else:
            records.append(dict(country=country, family=family, hourly_targets=0, monthly_target=False, converged=None, evaluations=0, inverse_loss=None))
    return theta, records, int(imputed.sum())


def certify(A, cost, availability, data, hours, x, y, obj, ng, nl, nz):
    maximum = dict(primal_mw=0., duality_gap_eur=0., complementarity_eur=0., free_reduced_cost_eur_mwh=0.)
    n = A.shape[1]; finite = ng+nl
    for start in range(0, len(hours), 96):
        sl = slice(start, min(start+96, len(hours))); hh = hours[sl]; T = len(hh)
        lo = np.c_[data['load'][hh], data['island_rhs'][hh], -data['ratings']-data['flow'][hh]]
        hi = np.c_[data['load'][hh], data['island_rhs'][hh], data['ratings']-data['flow'][hh]]
        lower = np.c_[np.zeros((T, ng)), data['link_min'][hh]]; upper = np.c_[availability[sl], data['link_max'][hh]]
        xx = x[sl]; yy = y[sl]; ax = (A@xx.T).T; cc = np.c_[cost[sl], np.zeros((T, n-ng))]; rc = cc-(A.T@yy.T).T
        primal = float(max(np.maximum(lower-xx[:, :finite], 0).max(), np.maximum(xx[:, :finite]-upper, 0).max(), np.maximum(lo-ax, 0).max(), np.maximum(ax-hi, 0).max()))
        actual = (cc*xx).sum(axis=1)
        dual = (np.maximum(yy, 0)*lo+np.minimum(yy, 0)*hi).sum(axis=1)+(np.maximum(rc[:, :finite], 0)*lower+np.minimum(rc[:, :finite], 0)*upper).sum(axis=1)
        gap = float(max(abs(actual-dual).max(), abs(actual-obj[sl]).max()))
        comp = float(max(abs(np.maximum(yy, 0)*(ax-lo)).max(), abs(np.minimum(yy, 0)*(ax-hi)).max(), abs(np.maximum(rc[:, :finite], 0)*(xx[:, :finite]-lower)).max(), abs(np.minimum(rc[:, :finite], 0)*(xx[:, :finite]-upper)).max()))
        free = float(abs(rc[:, finite:]).max())
        if primal > 1e-4 or gap >= .05 or comp >= .05 or free >= 1e-5:
            raise ValueError(f'LP certificate failed: {primal,gap,comp,free}')
        for key, value in zip(maximum, [primal, gap, comp, free], strict=True):
            maximum[key] = max(maximum[key], value)
    return maximum


def clear(sealed, data, A, theta, hours):
    from nve_hydro_diagnostics import solver
    from run_regional_water_candidate_2025 import guarded_hour
    started = time.perf_counter(); K = sealed['design']['segments']; G = len(sealed['groups'])
    cost = offer_costs(theta, sealed['groups'], data['source_cost'][hours], data['features'][hours], K)
    cost = np.c_[cost, data['emergency_cost'][hours]]
    av = np.c_[np.repeat(data['capacity'][hours]/K, K, axis=1), data['emergency_available'][hours]]
    m = {k:data[k][hours] for k in ['load', 'island_rhs', 'link_min', 'link_max']}
    m.update(A=A, cost=cost, availability=av, ng=sealed['ng'], nl=sealed['nl'], nz=sealed['nz'], zones=sealed['zones'], ratings=data['ratings'], islands=[None]*data['island_rhs'].shape[1])
    h = solver(m); h.setOptionValue('primal_feasibility_tolerance', 1e-8)
    x = np.zeros((len(hours), A.shape[1])); y = np.zeros((len(hours), A.shape[0])); obj = np.zeros(len(hours))
    for t, hour in enumerate(hours):
        r, value = guarded_hour(h, m, t, data['flow'][hour])
        if value is None:
            h = solver(m); h.setOptionValue('primal_feasibility_tolerance', 1e-8); r, value = guarded_hour(h, m, t, data['flow'][hour])
        if value is None:
            raise RuntimeError(f'Clearing failed at {hour}: {r}')
        x[t] = value; y[t] = h.getSolution().row_dual; obj[t] = r['objective_eur']
    emergency = float(np.maximum(x[:, G*K:sealed['ng']], 0).sum())
    if emergency > 1e-6:
        raise ValueError(f'Emergency generation {emergency}')
    checks = certify(A, cost, av, data, hours, x, y, obj, sealed['ng'], sealed['nl'], sealed['nz'])
    gen = generation(sealed, data, x, hours)
    return dict(values=x, row_duals=y, objectives=obj, generation=gen, hours=hours), dict(seconds=time.perf_counter()-started, emergency_mwh=emergency, certificate=checks)


def update(sealed, data, theta, witness, monthly, train):
    """Training-only price/quantity direction, accepted only after exact re-clearing."""
    hours = witness['hours']; prices = witness['row_duals'][:, :sealed['nz']]; target = data['observed_prices'][hours]
    K = sealed['design']['segments']; G = len(sealed['groups']); q = witness['values'][:, :G*K].reshape(len(hours), G, K).sum(axis=2)
    cap = data['capacity'][hours]; proposed = theta.copy()
    for k, (country, family) in enumerate(sealed['parameters']):
        ids = [j for j, group in enumerate(sealed['groups']) if group['parameter'] == k]
        zi = sorted({sealed['groups'][j]['zone_id'] for j in ids})
        xx = []; yy = []
        for z in zi:
            js = [j for j in ids if sealed['groups'][j]['zone_id'] == z]
            total = cap[:, js].sum(axis=1); fraction = np.divide(q[:, js].sum(axis=1), total, out=np.zeros(len(hours)), where=total > 0)
            good = np.isfinite(target[:, z]) & (fraction > .01) & (fraction < .99) & (total > 1)
            if good.sum() >= 12:
                xx.append(np.c_[data['features'][hours, z][good], logit(fraction[good])]); yy.append(np.clip(target[good, z]-prices[good, z], -100, 100))
        if xx:
            X = np.concatenate(xx); Y = np.concatenate(yy)
            beta = np.linalg.solve(X.T@X+168*np.eye(6), X.T@Y)
            proposed[k, :5] += beta[:5]
            proposed[k, 5] = np.log(np.clip(np.exp(theta[k, 5])+beta[5], 1, 100))
        ci = sealed['countries'].index(country); f = FAMILIES.index(family); obs = data['ember'][train-1, ci, f]
        if np.isfinite(obs):
            proposed[k, 0] += np.clip(20*(monthly[ci, f]-obs)/max(obs, .25), -20, 20)
    proposed[:, :5] = np.clip(proposed[:, :5], -80, 80)
    return proposed
