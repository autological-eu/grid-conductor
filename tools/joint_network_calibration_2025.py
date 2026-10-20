"""Declared effective-limit and weather-availability parameterization, not topology fitting."""
import numpy as np
from generation_mix_2025 import ROOT

PLAN = ROOT / 'config/joint-network-calibration-2025.json'


def states(design):
    rows = []
    for bid in design['bid_anchors']:
        for mode in design['network_modes']:
            for wind in design['wind_factors']:
                rows.append(dict(bid=bid, network=mode, wind=float(wind)))
        for mode in design['additional_network_modes_at_original_wind']:
            rows.append(dict(bid=bid, network=mode, wind=1.))
    return [dict(id=f"{r['bid']}-{r['network']}-w{int(round(r['wind']*100))}", **r) for r in rows]


def branches(n, design):
    rows = []
    for _, island in n.sub_networks.iterrows():
        for component, name in island.obj.branches_i():
            b = n.df(component).loc[name]
            c0, c1 = [str(n.buses.loc[b[k], 'country']) for k in ['bus0', 'bus1']]
            rows.append(dict(component=component, name=str(name), country0=c0, country1=c1,
                             nordic=c0 in design['nordic_countries'] or c1 in design['nordic_countries'],
                             original_limit_mw=float(b.s_nom*b.s_max_pu), nameplate_mva=float(b.s_nom)))
    return rows


def transform(m, ctx, layout, source_availability, source_wind, catalogue, state, design):
    assert state in states(design), 'Outside declared joint grid'
    factors = np.ones(len(catalogue))
    if state['network'] != 'unchanged':
        level = design['network_factor_lower' if state['network'].endswith('lower') else 'network_factor_higher']
        mask = np.ones(len(factors), bool) if state['network'].startswith('all_') else np.array([r['nordic'] for r in catalogue])
        factors[mask] = level
    av = source_availability.copy()
    av[:, source_wind] *= state['wind']
    case = m.copy()
    case['ratings'] = m['ratings']*factors
    case['availability'] = np.column_stack([av[:, ids].sum(axis=1)*f for ids, f in zip(layout['members'], layout['fractions'])])
    context = ctx.copy()
    mask = np.array([key is not None and key[1] == 'Wind' for key in ctx['generation_keys']])
    context['availability'] = ctx['availability'].copy()
    context['availability'][:, mask] *= state['wind']
    assert np.isfinite(case['availability']).all() and (case['availability'] >= 0).all()
    assert np.all(case['ratings'] <= np.array([r['nameplate_mva'] for r in catalogue])+1e-7)
    return case, context, factors


def score(metrics, reference, bid_reg, state, design, complete=True):
    level = 0. if state['network'] == 'unchanged' else (design['network_factor_lower' if state['network'].endswith('lower') else 'network_factor_higher']-1)/.15
    coords = [(state['wind']-1)/.1, level, level if state['network'].startswith('all_') else 0.]
    reg = bid_reg + float(np.mean(np.square(coords)))
    norm = {k: float(metrics[k]/reference[k]) for k in reference}
    d = design['research_filters']
    eligible = complete and norm['price'] <= d['price_ratio_maximum']+1e-12 and all(norm[k] <= d[b]+1e-12 for k,b in [('daily_demeaned_price','daily_demeaned_ratio_maximum'),('generation','generation_ratio_maximum'),('trade','trade_ratio_maximum')])
    value = sum(design['objective_weights'][k]*norm[k] for k in norm)+design['regularization_weight']*reg
    return dict(score=float(value), penalty=reg, normalized=norm, eligible=bool(eligible))


def choose(records):
    return min((r for r in records if r['eligible']), key=lambda r:(r['score'], r['penalty'], r['ordinal']))['id']
