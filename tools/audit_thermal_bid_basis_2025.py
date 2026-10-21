"""Source/unit and saved-book audit, with pinned ASSUME arithmetic parity.

No new clearing, calibration, unit-role assignment or empirical acceptance.
External source checkouts stay outside Git; only selected pure functions execute.
"""
import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from prepare_fuel_prices import compile_prices
from thermal_bid_rules import thermal_bid

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def selected_function(path, name):
    """Extract one inspected function; never import the external package."""
    tree = ast.parse(path.read_text())
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    node.returns = None
    for arg in node.args.args:
        arg.annotation = None
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


def audit(assume, osjmm, out, eua):
    plan = json.loads((ROOT/'config/thermal-bid-audit-2025.json').read_text())
    external = {}
    for key, folder in [('assume', assume), ('osjmm', osjmm)]:
        for file, sha in plan[key]['files'].items():
            assert digest(folder/file) == sha, f'External source changed: {key}/{file}'
            external[key+'/'+file] = sha
    review = ROOT/'data/bidding-zone-network-2025/supply-bid-review-v2'
    summary = json.loads((review/'summary.json').read_text())
    certificate = json.loads((review/'audit.json').read_text())
    assert certificate['status'] == 'passed'
    assert certificate['summary_sha256'] == digest(review/'summary.json')
    assert certificate['auditor_sha256'] == digest(ROOT/'tools/audit_supply_bid_review_2025.py')
    for file, sha in summary['files'].items():
        assert digest(review/file) == sha
    for file, sha in summary['source_hashes'].items():
        assert digest(ROOT/file) == sha

    raw_path = ROOT/'data/pypsa-eur/upstream/data/costs/archive/v0.15.0/costs_2025.csv'
    processed_path = ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/costs_2025_processed.csv'
    raw = {(r['technology'], r['parameter']): r for r in csv.DictReader(raw_path.open())}
    processed = {r['technology']: r for r in csv.DictReader(processed_path.open())}
    provenance = []
    for carrier in ['CCGT', 'OCGT', 'coal', 'lignite', 'oil']:
        for parameter in ['CO2 intensity', 'VOM', 'fuel']:
            source_carrier = 'gas' if carrier in ['CCGT', 'OCGT'] and parameter != 'VOM' else carrier
            source = raw[source_carrier, parameter]
            value = float(processed[carrier][parameter])
            assert value == float(source['value'])
            if parameter == 'CO2 intensity':
                assert source['unit'] == 'tCO2/MWh_th'
            provenance.append(dict(carrier=carrier, parameter=parameter, value=value,
                                   source_technology=source_carrier, source_row=source))

    market_path = ROOT/'data/daily-market-2025/monthly-fuel-annual-v2/fuel-inputs.json'
    market = json.loads(market_path.read_text())
    settings = market['assumptions']
    wb = ROOT/'data/fuel-prices/world-bank-monthly-2026.xlsx'
    fx = ROOT/'data/fuel-prices/ecb-2025-api.csv'
    for path, record in zip([wb, fx], market['provenance']):
        assert digest(path) == record['sha256']
    assert compile_prices(wb, fx, 2025, settings['gas_basis_multiplier'],
                          settings['oil_mwh_th_per_barrel'], settings['co2_eur_t']) == market
    oil_path = ROOT/'data/bidding-zone-network-2025/oil-supply-v2/oil-columns.json'
    columns = json.loads(oil_path.read_text())
    oil_summary = json.loads((oil_path.parent/'summary.json').read_text())
    assert digest(oil_path) == oil_summary['oil_columns_sha256']
    a = columns['assumption']
    assert a == dict(fuel_eur_mwh_th=float(processed['oil']['fuel']),
                     emissions_t_mwh_th=float(processed['oil']['CO2 intensity']),
                     variable_om_eur_mwh_el=float(processed['oil']['VOM']))
    fuel = np.array([r['oil_eur_mwh_th'] for r in market['hours']])
    carbon = np.array([r['co2_eur_t'] for r in market['hours']])
    assert len(fuel) == 8760 and np.all(carbon == 80)
    method = selected_function(assume/'assume/units/powerplant.py', 'calc_simple_marginal_cost')
    metadata = json.loads((review/'offers.json').read_text())
    assert {r['column'] for r in columns['existing']} == {r['column'] for r in metadata if r['category'] == 'Oil'}
    rows = []
    with np.load(review/'offers.npz') as arrays:
        saved = {key: arrays[key] for key in ['raw_cost', 'cost', 'dispatch']}
        for item in columns['existing']:
            j, eta = item['column'], item['efficiency']
            fc = fuel/eta
            cc = carbon*a['emissions_t_mwh_th']/eta
            expected = fc+cc+a['variable_om_eur_mwh_el']
            unit = SimpleNamespace(efficiency=eta, emission_factor=a['emissions_t_mwh_th'],
                                   additional_cost=a['variable_om_eur_mwh_el'],
                                   fuel_type='oil', forecaster=SimpleNamespace(get_price=lambda key: fuel if key == 'oil' else carbon))
            parity = method(unit)
            np.testing.assert_allclose(expected, parity, rtol=0, atol=1e-10)
            for key in ['raw_cost', 'cost']:
                np.testing.assert_allclose(saved[key][:, j], expected, rtol=0, atol=1e-8)
            for t in [0, 348, 4692, 8364, 8759]:
                bid = thermal_bid(fuel[t], eta, carbon[t], a['emissions_t_mwh_th'], a['variable_om_eur_mwh_el'])
                assert abs(bid['offer_eur_mwh_el']-expected[t]) < 1e-10
            rows.append(dict(column=j, zone=item['zone'], efficiency=eta,
                             fuel_min=float(fc.min()), fuel_max=float(fc.max()),
                             carbon=float(cc[0]), vom=a['variable_om_eur_mwh_el'],
                             max_formula_error=float(abs(saved['cost'][:, j]-expected).max()),
                             max_assume_error=float(abs(parity-expected).max()),
                             generation_twh=float(saved['dispatch'][:, j].sum()/1e6)))
    typical_fuel = float(np.median(fuel))
    # Auction observations are a separate benchmark, not a filled daily spot series.
    import pandas as pd
    auctions = pd.read_excel(eua, header=5, sheet_name='Primary Market Auction')
    assert set(auctions['Contract']) == {'T3PA'}
    assert set(auctions['Status']) == {'successful'}
    assert auctions['Date'].dt.year.eq(2025).all()
    assert not auctions[['Date', 'Auction Name']].duplicated().any()
    price = pd.to_numeric(auctions['Auction Price €/tCO2'], errors='raise')
    volume = pd.to_numeric(auctions['Auction Volume tCO2'], errors='raise')
    assert np.isfinite(price).all() and (price > 0).all() and (volume > 0).all()
    auction_benchmark = dict(url='https://public.eex-group.com/eex/eua-auction-report/emission-spot-primary-market-auction-report-2025-data.xlsx',
                            sha256=digest(eua), observations=len(auctions),
                            first=str(auctions['Date'].min().date()), last=str(auctions['Date'].max().date()),
                            min=float(price.min()), max=float(price.max()),
                            mean=float(price.mean()), volume_weighted_mean=float(np.average(price, weights=volume)),
                            limitation='EEX T3PA successful primary auctions; not all calendar days, secondary spot prices or delivered EUA costs')
    examples = {}
    for eta in [.35, .40, .45]:
        examples[str(eta)] = thermal_bid(typical_fuel, eta, 80, a['emissions_t_mwh_th'], a['variable_om_eur_mwh_el'])
    inputs = [raw_path, processed_path, market_path, wb, fx, oil_path,
              review/'summary.json', review/'audit.json', ROOT/'tools/thermal_bid_rules.py',
              ROOT/'tools/prepare_fuel_prices.py', ROOT/'tools/hybrid_fixed_hydro_2025.py']
    result = dict(status='passed', scope='Source/unit and frozen oil-book arithmetic audit; not empirical certification',
                  hours=8760, oil_column_count=len(rows), new_market_solves=0,
                  producer_sha256=digest(__file__), plan_sha256=digest(ROOT/'config/thermal-bid-audit-2025.json'),
                  source_hashes={str(p.relative_to(ROOT)): digest(p) for p in inputs},
                  external_source_hashes=external, thermal_source_rows=provenance,
                  oil_columns=rows, settings=settings, eua_auction_benchmark=auction_benchmark,
                  typical_oil_fuel_eur_mwh_th=typical_fuel,
                  illustrative_efficiency_sensitivity=examples,
                  carbon_bid_change_per_10_eur_t_at_35pct=10*a['emissions_t_mwh_th']/.35,
                  unresolved=['Delivered fuel product and heating-value consistency',
                              'Plant-specific electrical efficiency/part-load and source age',
                              'Observed daily carbon series and jurisdiction/coverage',
                              'CHP heat value, minimum volumes and market eligibility',
                              'Startup/shutdown state and empirical generation scope'])
    out.mkdir(parents=True, exist_ok=False)
    (out/'audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ['status', 'hours', 'oil_column_count', 'new_market_solves', 'typical_oil_fuel_eur_mwh_th', 'illustrative_efficiency_sensitivity']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assume', type=Path, required=True)
    parser.add_argument('--osjmm', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--eua', type=Path, required=True)
    args = parser.parse_args()
    audit(args.assume, args.osjmm, args.output, args.eua)
