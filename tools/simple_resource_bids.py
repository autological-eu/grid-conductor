"""Transparent generator offers and daily storage rules; no operator LPs."""
import csv
import time
from pathlib import Path

import numpy as np

from thermal_bid_rules import thermal_bid, validate_market
from daily_market_clearing import reachable_bounds
from european_physical_bids_2025 import compile_model
from european_reservoir_clearing_2025 import aggregate_offers
from perfect_foresight_dispatch import apply_investments
from hourly_renewable_estimates import digest

ROOT = Path(__file__).resolve().parents[1]
COSTS = ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/costs_2025_processed.csv'
RENEWABLES = {'solar', 'solar-hsat', 'onwind', 'offwind-ac', 'offwind-dc', 'offwind-float'}
THERMAL = {'CCGT', 'OCGT', 'coal', 'lignite', 'oil'}
OTHER = {'nuclear', 'biomass', 'waste', 'geothermal', 'ror', 'emergency'}
DEFAULTS = dict(renewable_offer_eur_mwh=0., carbon_price_eur_t=80.,
                hydro_reference_days=30, hydro_inventory_adjustment_eur_mwh=40.,
                battery_wear_eur_mwh_discharge=2., phs_wear_eur_mwh_discharge=0.,
                arbitrage_lookahead_hours=48)


def configuration(overrides=None):
    settings = DEFAULTS | (overrides or {})
    if set(settings) != set(DEFAULTS): raise ValueError('Unknown bidding-rule setting')
    if not all(np.isfinite(float(v)) for v in settings.values()): raise ValueError('Nonfinite setting')
    for key in ('carbon_price_eur_t', 'hydro_inventory_adjustment_eur_mwh',
                'battery_wear_eur_mwh_discharge', 'phs_wear_eur_mwh_discharge'):
        if settings[key] < 0: raise ValueError('Negative '+key)
    for key in ('hydro_reference_days', 'arbitrage_lookahead_hours'):
        if settings[key] < 1 or int(settings[key]) != settings[key]: raise ValueError('Positive integer '+key)
    return settings


def cost_assumptions(path=COSTS):
    """Prepared technology assumptions, explicitly NOT historical fuel quotes."""
    with Path(path).open() as f: rows = {r['technology']:r for r in csv.DictReader(f)}
    assumptions = {}
    for carrier in THERMAL:
        row = rows[carrier]
        assumptions[carrier] = dict(fuel_eur_mwh_th=float(row['fuel']),
                                    emissions_t_mwh_th=float(row['CO2 intensity']),
                                    variable_om_eur_mwh_el=float(row['VOM']))
    return assumptions, dict(path=str(Path(path).relative_to(ROOT)), sha256=digest(path),
                             status='prepared_2025_technology_cost_assumptions_not_observed_fuel_prices')


def compile_case(n, reference, investments, weather, settings, assumptions, market=None):
    """Apply a named strategy to every carrier before equivalent-offer merging."""
    base = n.copy()
    apply_investments(base, [x for x in investments if x['type'] not in ('solar', 'wind')])
    m = compile_model(base)
    if m['weights'] != reference['weights']: raise ValueError('Investment changed fixed GSK')
    apply_investments(base, [x for x in investments if x['type'] in ('solar', 'wind')], weather)
    m['availability'] = base.get_switchable_as_dense('Generator', 'p_max_pu').values * base.generators.p_nom.values
    # Start from unmodified prepared costs, not the legacy compiler's carbon/-5 bids.
    costs = base.get_switchable_as_dense('Generator', 'marginal_cost').values.copy()
    rows = validate_market(market, base.snapshots) if market is not None else None
    declarations = []
    for j, (asset, g) in enumerate(base.generators.iterrows()):
        carrier = g.carrier
        if carrier in RENEWABLES:
            costs[:,j] = settings['renewable_offer_eur_mwh']; strategy = 'weather_limited_low_cost'
        elif carrier in THERMAL:
            a = assumptions[carrier]
            for t in range(len(base.snapshots)):
                fuel = a['fuel_eur_mwh_th']; carbon = settings['carbon_price_eur_t']
                if rows is not None:
                    carbon = rows[t]['co2_eur_t']
                    if carrier in ('CCGT', 'OCGT'): fuel = rows[t]['gas_eur_mwh_th']
                    elif carrier == 'oil': fuel = rows[t]['oil_eur_mwh_th']
                costs[t,j] = thermal_bid(fuel, g.efficiency, carbon,
                                         a['emissions_t_mwh_th'], a['variable_om_eur_mwh_el'])['offer_eur_mwh_el']
            strategy = 'fuel_carbon_variable_cost'
        elif carrier in OTHER:
            strategy = {'nuclear':'prepared_low_operating_cost_no_commitment',
                        'ror':'inflow_limited_prepared_cost',
                        'emergency':'explicit_shortage_penalty'}.get(carrier, 'prepared_operating_cost_proxy')
        else: raise ValueError('No explicit generator strategy for '+str(carrier))
        declarations.append(dict(asset=str(asset), carrier=carrier, strategy=strategy))
    if not np.isfinite(costs).all(): raise ValueError('Nonfinite generator offers')
    m['cost'] = costs
    return base, aggregate_offers(base, m), declarations


def battery_thresholds(expected, eta_charge, eta_discharge, wear, operating_cost=0.):
    """Price thresholds around a stored-MWh value, accounting for both losses."""
    expected = np.asarray(expected, dtype=float)
    if not expected.size or not np.isfinite(expected).all(): raise ValueError('Finite expected prices required')
    if not 0 < eta_charge <= 1 or not 0 < eta_discharge <= 1: raise ValueError('Invalid efficiency')
    if not np.isfinite(wear) or wear < 0 or not np.isfinite(operating_cost) or operating_cost < 0:
        raise ValueError('Nonnegative storage operating/wear costs required')
    low, high = float(expected.min()), float(expected.max())
    # A stored MWh costs low/eta_c to buy and earns (high-wear-mc)*eta_d.
    profitable = (high-wear-operating_cost)*eta_discharge > low/eta_charge + 1e-8
    value = max(0., (low/eta_charge + (high-wear-operating_cost)*eta_discharge)/2)
    return dict(buy_eur_mwh=eta_charge*value,
                sell_eur_mwh=value/eta_discharge+wear+operating_cost,
                stored_value_eur_mwh=value, profitable=bool(profitable))


def prepare_storage(n, m, forecast, initial, terminal, settings):
    """Only arithmetic and backward water bounds, never a per-unit solve."""
    begin = time.perf_counter(); T = len(forecast); s = n.storage_units
    cap = (s.p_nom*s.max_hours).values
    cmax = (-s.p_nom*s.p_min_pu).values; dmax = (s.p_nom*s.p_max_pu).values
    inflow = n.get_switchable_as_dense('StorageUnit', 'inflow').iloc[:T].values
    if set(s.carrier) - {'hydro', 'PHS', 'battery'}: raise ValueError('Unsupported storage strategy')
    if np.shape(forecast) != (T,m['nz']) or not np.isfinite(forecast).all(): raise ValueError('Invalid forecast')
    if len(n.stores) or any(not v.empty for k,v in n.storage_units_t.items() if k != 'inflow'):
        raise ValueError('Unsupported Stores or temporal storage physics')
    if (not np.isfinite(inflow).all() or np.any(inflow < 0) or
        np.any(s.efficiency_dispatch <= 0) or np.any(s.efficiency_dispatch > 1) or
        np.any(s.efficiency_store < 0) or np.any(s.efficiency_store > 1) or
        np.any((cmax > 0) & (s.efficiency_store.values <= 0)) or
        np.any(s.standing_loss < 0) or np.any(s.standing_loss >= 1) or
        np.any(s.marginal_cost < 0)):
        raise ValueError('Invalid storage physics/costs')
    for state in (initial, terminal):
        if np.shape(state) != cap.shape or not np.isfinite(state).all() or np.any(state < 0) or np.any(state > cap+1e-6):
            raise ValueError('Invalid inventory boundary')
    lo,hi = reachable_bounds(inflow, np.tile(cmax,(T,1)), np.tile(dmax,(T,1)),cap,
                             s.efficiency_store.values,s.efficiency_dispatch.values,
                             1-s.standing_loss.values,terminal)
    if np.any(initial < lo[0]-1e-4) or np.any(initial > hi[0]+1e-4): raise ValueError('Unreachable terminal')
    # Reference stock from inflow seasonality and a uniform release budget.
    # This is a target, not a dispatch schedule or new water. Losses stay exact in clearing.
    fraction = np.arange(T+1)[:,None]/T
    target = (initial + np.vstack([np.zeros(len(s)),np.cumsum(inflow,axis=0)]) -
              fraction*(inflow.sum(axis=0)+initial-terminal))
    target = np.minimum(np.maximum(target,0),cap)
    return dict(target=target,reachable_lower=lo,reachable_upper=hi,inflow=inflow,
                charge_limit=cmax,discharge_limit=dmax,forecast=forecast,
                preparation_seconds=time.perf_counter()-begin)


def storage_bids(n,m,start,end,current,terminal,prepared,settings):
    """Daily rules adapt to actual carried inventory. No planned hourly dispatch."""
    ns = len(n.storage_units); T = len(prepared['forecast']); hours = end-start
    charge = np.zeros((hours,ns)); discharge = np.zeros((hours,ns))
    buy = np.zeros((hours,ns)); sell = np.zeros((hours,ns)); wear = np.zeros(ns)
    records = []; begin = time.perf_counter()
    for j,(asset,row) in enumerate(n.storage_units.iterrows()):
        area = m['zones'].index(m['buszone'][row.bus]); price = prepared['forecast'][start:end,area]
        cap = row.p_nom*row.max_hours
        if row.carrier == 'hydro':
            if prepared['charge_limit'][j] != 0: raise ValueError('Natural reservoir cannot pump')
            horizon = min(T,start+24*int(settings['hydro_reference_days']))
            reference = max(0.,float(np.median(prepared['forecast'][start:horizon,area])))
            gap = (prepared['target'][start,j]-current[j])/cap if cap > 0 else 0.
            # Water value below is per MWh electricity equivalent.
            water_value = max(0.,reference+settings['hydro_inventory_adjustment_eur_mwh']*gap)
            # Once this declared simulation closes, remaining releasable water
            # has no later trading opportunity; the exact closing stock is protected.
            if end == T: water_value = 0.
            sell[:,j] = row.marginal_cost+water_value
            discharge[:,j] = prepared['discharge_limit'][j]
            record = dict(asset=str(asset),strategy='seasonal_inventory_water_value',
                          target_mwh=float(prepared['target'][start,j]),
                          initial_mwh=float(current[j]),water_value_eur_mwh_el=water_value)
            if end == T:record['closing_day_inventory_settlement'] = True
        else:
            wear[j] = settings['battery_wear_eur_mwh_discharge'] if row.carrier=='battery' else settings['phs_wear_eur_mwh_discharge']
            horizon = min(T,start+int(settings['arbitrage_lookahead_hours']))
            thresholds = battery_thresholds(prepared['forecast'][start:horizon,area],
                                             row.efficiency_store,row.efficiency_dispatch,
                                             wear[j],row.marginal_cost)
            buy[:,j] = thresholds['buy_eur_mwh']; sell[:,j] = thresholds['sell_eur_mwh']
            if thresholds['profitable']:
                charging = price < thresholds['buy_eur_mwh']-1e-8
                selling = price > thresholds['sell_eur_mwh']+1e-8
                charge[charging,j] = prepared['charge_limit'][j]
                discharge[selling,j] = prepared['discharge_limit'][j]
            record = dict(asset=str(asset),strategy='loss_adjusted_low_buy_high_sell',**thresholds)
            # Closing-day rule explicitly settles outstanding initial-stock changes.
            # No reference trajectory is forced on intermediate days.
            if end == T:
                need = terminal[j]-current[j]*(1-row.standing_loss)**hours
                if need > 1e-6:
                    charge[:,j] = prepared['charge_limit'][j]; discharge[:,j] = 0.
                elif need < -1e-6:
                    charge[:,j] = 0.; discharge[:,j] = prepared['discharge_limit'][j]
                record['closing_day_inventory_settlement'] = True
        records.append(record)
    if np.any((charge>0)&(discharge>0)): raise ValueError('Overlapping charge/sell modes')
    return dict(charge_max=charge,discharge_max=discharge,buy=buy,sell=sell,wear=wear,
                reachable_lower=prepared['reachable_lower'][end],
                reachable_upper=prepared['reachable_upper'][end],
                seconds=time.perf_counter()-begin,operators=records)
