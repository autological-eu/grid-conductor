"""Source-priced oil and bounded heat-led offer tranches; no target fitting."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack
from shapely.geometry import Point
from bidding_zone_network_2025 import boundaries, locate
from generation_mix_2025 import ROOT, digest

PLAN = ROOT/'config/oil-chp-bids-2025.json'
EUA = ROOT/'data/bidding-zone-network-2025/thermal-bid-audit-v1/eex-eua-auction-2025.xlsx'
PLANTS = ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/powerplants_s_128.csv'
PRIOR = ROOT/'data/bidding-zone-network-2025/oil-supply-v2'


def source_inputs(n, m, layout, oil, additions):
    design = json.loads(PLAN.read_text())
    certificate = json.loads((ROOT/'data/bidding-zone-network-2025/thermal-bid-audit-v2/audit.json').read_text())
    assert digest(EUA) == certificate['eua_auction_benchmark']['sha256']
    table = pd.read_excel(EUA, sheet_name='Primary Market Auction', header=5)
    assert set(table.Contract) == {'T3PA'} and set(table.Status) == {'successful'}
    assert table.Date.dt.year.eq(2025).all()
    table['value'] = table['Auction Price €/tCO2']*table['Auction Volume tCO2']
    daily = table.groupby('Date')[['value', 'Auction Volume tCO2']].sum()
    quotes = daily.value/daily['Auction Volume tCO2']
    clock = pd.date_range('2025-01-01', periods=8760, freq='h')
    carbon = quotes.reindex(clock.normalize(), method='ffill').to_numpy(copy=True)
    fallback = ~np.isfinite(carbon); carbon[fallback] = 80.
    dates = pd.Series(quotes.index.values, index=quotes.index).reindex(clock.normalize(), method='ffill')
    ages = (clock.normalize().values-dates.to_numpy()).astype('timedelta64[D]').astype(float)
    assert fallback.sum() == 144 and np.nanmax(ages) == 16
    market = json.loads((ROOT/'data/daily-market-2025/monthly-fuel-annual-v2/fuel-inputs.json').read_text())
    gas = np.array([r['gas_eur_mwh_th'] for r in market['hours']])
    frame = pd.read_csv(PLANTS)
    frame = frame[(frame.Fueltype=='Oil') & (frame.DateIn.isna() | (frame.DateIn<=2025)) & (frame.DateOut.isna() | (frame.DateOut>2025))]
    shapes, countries, geo_sources = boundaries()
    bus_total, bus_chp, inventory = {}, {}, []
    for idx, row in frame.iterrows():
        if not np.isfinite(row.lon+row.lat):
            continue
        try:
            zone, method, distance = locate(Point(row.lon, row.lat), str(row.Country), shapes, countries)
        except ValueError:
            continue
        bus = str(row.bus)+'::'+zone
        if bus not in n.buses.index:
            continue
        bus_total[bus] = bus_total.get(bus, 0)+float(row.Capacity)
        if row.Set == 'CHP':
            bus_chp[bus] = bus_chp.get(bus, 0)+float(row.Capacity)
        inventory.append(dict(source_row=int(idx), country=str(row.Country), bus=bus, role=str(row.Set), mw=float(row.Capacity)))
    records = []
    for row in oil:
        ids = layout['members'][row['column']]
        native = n.generators.iloc[ids]
        assert native.carrier.eq('oil').all()
        chp = sum(g.p_nom*bus_chp.get(g.bus, 0)/bus_total[g.bus] if bus_total.get(g.bus, 0)>0 else 0 for _,g in native.iterrows())
        share = float(chp/native.p_nom.sum())
        assert 0 <= share <= 1+1e-12
        records.append(row | dict(chp_share=min(1., share)))
    for j, row in enumerate(additions):
        records.append(dict(column=m['ng']-len(additions)+j, zone=row['zone'], efficiency=row['efficiency'], countries={row['country']:1.}, chp_share=0.))
    for row in records:
        assert row['efficiency']+design['useful_heat_efficiency_proxy'] <= 1
        row['carbon_weight'] = sum(v for k,v in row['countries'].items() if k in design['carbon_countries'])
    return dict(carbon=carbon, gas=gas, records=records, inventory=inventory,
                fallback_hours=int(fallback.sum()), max_carbon_age_days=int(np.nanmax(ages)), geography_sources=geo_sources)


def compile_case(m, source, daily_fuel, assumption, key):
    design = json.loads(PLAN.read_text())
    assert key in design['cases']
    fraction = design['chp_tranche_fractions'][key]
    case = m.copy(); cost = m['cost'].copy(); av = m['availability'].copy()
    extras, extra_av, extra_cost = [], [], []
    for row in source['records']:
        j, eta = row['column'], row['efficiency']
        carbon = row['carbon_weight']*source['carbon']+(1-row['carbon_weight'])*80
        if key != 'control':
            cost[:, j] = (daily_fuel+carbon*assumption['emissions_t_mwh_th'])/eta+assumption['variable_om_eur_mwh_el']
        if fraction and row['chp_share'] > 0:
            share = fraction*row['chp_share']
            volume = m['availability'][:, j]*share
            # A cheap offered tranche, NOT a forced minimum or observed schedule.
            heat_per_electric = design['useful_heat_efficiency_proxy']/eta
            credit = heat_per_electric*(source['gas']+carbon*design['alternative_gas_emissions_t_mwh_th'])/design['alternative_gas_boiler_efficiency']
            extra_cost.append(cost[:, j]-credit)
            extra_av.append(volume); av[:, j] -= volume
            extras.append(dict(parent=j, column=m['ng']+len(extras), share=share,
                               zone=row['zone'], efficiency=eta, countries=row['countries']))
    if extras:
        parents = [r['parent'] for r in extras]
        case['A'] = hstack([m['A'][:, :m['ng']], m['A'][:, parents], m['A'][:, m['ng']:]], format='csc')
        av = np.c_[av, np.array(extra_av).T]; cost = np.c_[cost, np.array(extra_cost).T]
        case['offer_zones'] = np.r_[m['offer_zones'], [r['zone'] for r in extras]]
        case['emergency_mask'] = np.r_[m['emergency_mask'], np.zeros(len(extras), bool)]
        case['ng'] = m['ng']+len(extras)
    case['availability'], case['cost'] = av, cost
    return case, extras


def collapse(values, ng, extras):
    q = values[:, :ng].copy()
    for row in extras:
        q[:, row['parent']] += values[:, row['column']]
    return np.c_[q, values[:, ng+len(extras):]]


def oil_quantities(case, values, countries, records, extras):
    out = np.zeros((8760, len(countries)))
    for row in records+extras:
        for country, share in row['countries'].items():
            out[:, countries.index(country)] += values[:, row['column']]*share
    return out
