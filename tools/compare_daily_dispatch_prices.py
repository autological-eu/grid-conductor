"""Untuned annual A44 comparison; physical-area prices remain labelled proxies."""
import gzip
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from hourly_renewable_estimates import digest
from flow_tracing import parse_day_ahead_prices, hourly

ROOT = Path(__file__).resolve().parents[1]


def metrics(model, observed):
    model = np.asarray(model, dtype=float); observed = np.asarray(observed, dtype=float)
    valid = np.isfinite(model) & np.isfinite(observed)
    m = model[valid]; o = observed[valid]
    if not len(m):
        return dict(known_hours=0)
    error = m - o
    corr = float(np.corrcoef(m, o)[0, 1]) if np.std(m) > 1e-12 and np.std(o) > 1e-12 else None
    return dict(known_hours=len(m), observed_mean_eur_mwh=float(o.mean()),
                model_mean_eur_mwh=float(m.mean()), bias_eur_mwh=float(error.mean()),
                mae_eur_mwh=float(abs(error).mean()), rmse_eur_mwh=float(np.sqrt((error**2).mean())),
                correlation=corr, median_absolute_error_eur_mwh=float(np.median(abs(error))),
                p95_absolute_error_eur_mwh=float(np.quantile(abs(error), .95)),
                within_10_eur_mwh_fraction=float(np.mean(abs(error) <= 10)),
                observed_negative_hours=int(np.sum(o < 0)), model_negative_hours=int(np.sum(m < 0)),
                maximum_absolute_error_eur_mwh=float(abs(error).max()))


def audit_observations(zone, meta, values):
    """Rehash cached A44 receipts and reproduce hourly aggregation from XML."""
    samples = {}
    for receipt in meta['receipts']:
        request = receipt['request']
        if (request['documentType'] != 'A44' or request['processType'] != 'A01'
                or request['in_Domain'] != meta['price_eic']
                or request['out_Domain'] != meta['price_eic']):
            raise ValueError('Observation request scope mismatch')
        key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()[:24]
        raw_path = ROOT / 'data/price-trace/entsoe' / zone / (key + '.xml')
        if digest(raw_path) != receipt['sha256']:
            raise ValueError('Raw observation hash mismatch')
        metadata = json.loads(raw_path.with_suffix('.json').read_text())
        if metadata['request'] != request or metadata['sha256'] != receipt['sha256']:
            raise ValueError('Raw observation metadata mismatch')
        begin = dt.datetime.strptime(request['periodStart'], '%Y%m%d%H%M').replace(tzinfo=dt.timezone.utc)
        end = dt.datetime.strptime(request['periodEnd'], '%Y%m%d%H%M').replace(tzinfo=dt.timezone.utc)
        for stamp, value in parse_day_ahead_prices(raw_path.read_bytes()).items():
            if begin <= stamp < end:
                if stamp in samples and samples[stamp] != value:
                    raise ValueError('Conflicting raw observations')
                samples[stamp] = value
    start = dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)
    rebuilt = np.array([np.nan if (v := hourly(samples, start + dt.timedelta(hours=i))) is None else v
                        for i in range(8760)])
    np.testing.assert_allclose(values, rebuilt, rtol=0, atol=0, equal_nan=True)


def model_area(zone):
    # Explicit proxies, never a claim of an audited commercial-zone mapping.
    if zone == 'DE-LU':
        return '0:DE', 'German country proxy excludes Luxembourg'
    if zone.startswith('NO'):
        return '1:NO', 'One Norway country price reused; internal bidding-zone constraints absent'
    if zone.startswith('SE'):
        return '1:SE', 'One Sweden country price reused; internal bidding-zone constraints absent'
    if zone == 'DK1':
        return '0:DK', 'Danish continental AC-area proxy; commercial mapping unvalidated'
    if zone == 'DK2':
        return '1:DK', 'Danish Nordic AC-area proxy; commercial mapping unvalidated'
    if zone == 'GB':
        return '4:GB', 'British mainland AC-area proxy; commercial mapping unvalidated'
    if zone == 'IE':
        return '5:IE', 'Irish country proxy excludes Northern Ireland from the all-island market'
    if zone in ('IT-North', 'IT-CNOR', 'IT-CSUD', 'IT-SUD', 'IT-CALA'):
        return '0:IT', 'One Italian mainland price reused; internal bidding-zone constraints absent'
    if zone in ('IT-SARD', 'IT-SICI'):
        return None, 'Island-to-commercial-zone mapping unresolved; excluded rather than guessed'
    if zone == 'FI':
        return '1:FI', 'Finnish country/AC-area proxy; commercial mapping unvalidated'
    return '0:' + zone, 'Country/mainland physical-area proxy; commercial mapping unvalidated'


def shortage_areas(folder, summary, case):
    """Rebuild offer identities; attribute audited emergency columns by area."""
    import pypsa
    from simple_resource_bids import compile_case
    from european_reservoir_clearing_2025 import setup
    from synthetic_bids_2025 import SOURCE
    p = summary['provenance']
    n, reference, *_ = setup()
    weather = pypsa.Network(SOURCE).get_switchable_as_dense('Generator', 'p_max_pu')
    market = json.loads((folder / 'fuel-inputs.json').read_text())
    _, m, _ = compile_case(n, reference, [], weather, p['settings'], p['thermal_assumptions'], market)
    if m['zones'] != case['zones']:
        raise ValueError('Shortage attribution area mismatch')
    emergency = []
    for day in range(365):
        with np.load(folder / 'baseline' / f'{day:03d}.npz', allow_pickle=False) as f:
            generators = f['values'][:, :m['ng']]
        emergency.append(np.column_stack([generators[:, m['emergency_mask'] & (m['offer_zones'] == area)].sum(axis=1)
                                          for area in case['zones']]))
    emergency = np.concatenate(emergency)
    return [dict(area=area, emergency_supply_mwh=float(emergency[:, j].sum()),
                 shortage_hours=int(np.count_nonzero(emergency[:, j] > 1e-6)),
                 source_demand_mwh=float(m['load'][:, j].sum()))
            for j, area in enumerate(case['zones'])]


def compare(folder, observed_root, output):
    s = json.loads((folder / 'summary.json').read_text())
    replay = json.loads((folder / 'replay.json').read_text())
    if (s['provenance']['hours'] != 8760 or replay['summary_sha256'] != digest(folder / 'summary.json')
            or replay['status'] != 'saved_daily_rules_and_physics_replayed'):
        raise ValueError('Completed and independently replayed annual simulation required')
    case = next(c for c in s['cases'] if c['case'] == 'baseline')
    if set(case['receipts_sha256']) != {f'{d:03d}.json' for d in range(365)}:
        raise ValueError('Exactly 365 daily receipts required')
    areas = case['zones']; records = []; prices = []
    for day in range(365):
        path = folder / 'baseline' / f'{day:03d}.npz'
        receipt = folder / 'baseline' / f'{day:03d}.json'
        r = json.loads(receipt.read_text())
        if case['receipts_sha256'][receipt.name] != digest(receipt) or r['witness_sha256'] != digest(path):
            raise ValueError('Witness/receipt mismatch')
        if r['start_hour'] != day * 24 or r['end_hour'] != (day + 1) * 24:
            raise ValueError('Missing chronology')
        with np.load(path, allow_pickle=False) as f:
            values = f['prices'].copy()
        if values.shape != (24, len(areas)) or not np.isfinite(values).all():
            raise ValueError('Invalid model prices')
        prices.append(values)
    prices = np.concatenate(prices)
    dates = pd.date_range('2025-01-01', periods=8760, freq='h', tz='UTC')
    source = json.loads((observed_root / 'manifest.json').read_text())
    if source['hours'] != 8760 or source['start_utc'] != '2025-01-01T00:00:00Z':
        raise ValueError('Observation calendar mismatch')
    observations = {}; mappings = {}; excluded = []
    for zone, meta in sorted(source['zones'].items()):
        area, scope = model_area(zone)
        if area not in areas:
            excluded.append(dict(zone=zone, reason=scope if area is None else 'No corresponding model area'))
            continue
        path = observed_root / (zone + '.json')
        if digest(path) != meta['hourly_sha256'] or meta['source'] != 'ENTSO-E A44 day-ahead prices':
            raise ValueError('Observed source/hash mismatch')
        o = np.array([np.nan if v is None else v for v in json.loads(path.read_text())])
        if o.shape != (8760,):
            raise ValueError('Observed calendar length')
        audit_observations(zone, meta, o)
        m = prices[:, areas.index(area)]
        record = dict(zone=zone, model_area=area, mapping_scope=scope, price_source=meta,
                      **metrics(m, o))
        record['closing_48h'] = metrics(m[-48:], o[-48:])
        record['preceding_8712h'] = metrics(m[:-48], o[:-48])
        record['monthly'] = [dict(month=month, **metrics(m[dates.month == month], o[dates.month == month]))
                             for month in range(1, 13)]
        records.append(record); observations[zone] = o; mappings[zone] = area
    borders = json.loads((ROOT / 'public/research/zone-prices-2025/coverage.json').read_text())['coverage']
    spread_records = []
    for edge in borders:
        a, b = edge['zone_a'], edge['zone_b']
        if a not in observations or b not in observations:
            continue
        observed = observations[b] - observations[a]
        model = prices[:, areas.index(mappings[b])] - prices[:, areas.index(mappings[a])]
        valid = np.isfinite(observed)
        selected = valid & (abs(observed) > 5)
        spread_records.append(dict(zone_a=a, zone_b=b,
            collapsed_model_areas=mappings[a] == mappings[b], **metrics(model, observed),
            observed_spread_above_5_hours=int(selected.sum()),
            model_spread_above_5_hours=int(np.sum((abs(model) > 5) & valid)),
            direction_agreement_selected_fraction=float(np.mean(np.sign(model[selected]) == np.sign(observed[selected]))) if selected.any() else None))
    output.mkdir(parents=True, exist_ok=True)
    shortage = shortage_areas(folder, s, case)
    audited = next(r for r in replay['checks'] if r['case'] == 'baseline')['emergency_supply_mwh']
    if abs(sum(r['emergency_supply_mwh'] for r in shortage) - audited) > .05:
        raise ValueError('Shortage attribution disagrees with annual replay')
    result = dict(shortage_areas=shortage, scope='Untuned descriptive 2025 physical-area price diagnostic; not held-out validation',
                  run_summary_sha256=digest(folder / 'summary.json'), replay_sha256=digest(folder / 'replay.json'),
                  observed_manifest_sha256=digest(observed_root / 'manifest.json'),
                  exporter_sha256=digest(__file__), calendar='8760 UTC hours; each hour equally weighted',
                  metrics='Model minus observed; no percentage error or missing-hour imputation',
                  acceptance='No selected thresholds, fitting or empirical acceptance claim',
                  zones=records, excluded=excluded, borders=spread_records,
                  model_areas_without_observed_comparison=sorted(set(areas) - {r['model_area'] for r in records if r['known_hours']}))
    (output / 'price-comparison.json').write_text(json.dumps(result, separators=(',', ':'), allow_nan=False) + '\n')
    for name in ('summary.json', 'replay.json'):
        (output / name).write_bytes((folder / name).read_bytes())
    with (output / 'zone-errors.csv').open('w') as f:
        keys = ['zone', 'model_area', 'known_hours', 'mae_eur_mwh', 'bias_eur_mwh', 'rmse_eur_mwh', 'correlation', 'p95_absolute_error_eur_mwh']
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore'); writer.writeheader(); writer.writerows(records)
    with (output / 'border-errors.csv').open('w') as f:
        keys = ['zone_a', 'zone_b', 'collapsed_model_areas', 'known_hours', 'mae_eur_mwh', 'bias_eur_mwh', 'direction_agreement_selected_fraction', 'observed_spread_above_5_hours', 'model_spread_above_5_hours']
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore'); writer.writeheader(); writer.writerows(spread_records)
    eligible = [r for r in records if r['known_hours']]
    fig, ax = plt.subplots(figsize=(11, 9), layout='constrained')
    ax.barh([r['zone'] for r in eligible], [r['mae_eur_mwh'] for r in eligible])
    ax.set(xlabel='Mean absolute error, EUR/MWh', title='All available zones: physical-area proxy versus ENTSO-E'); ax.invert_yaxis()
    fig.savefig(output / 'zone-errors.png'); plt.close(fig)
    if 'DE-LU' in observations:
        de = prices[:, areas.index('0:DE')]; obs = observations['DE-LU']; valid = np.isfinite(obs)
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), layout='constrained')
        axes[0].plot(dates[:168], de[:168], label='Model German country proxy')
        axes[0].plot(dates[:168], obs[:168], label='ENTSO-E DE-LU', alpha=.8)
        axes[0].set(ylabel='EUR/MWh', title='First calendar week: no example-week selection'); axes[0].legend()
        axes[1].hist(de[valid] - obs[valid], bins=70)
        axes[1].set(xlabel='Model minus observed, EUR/MWh', ylabel='Hours', title='Germany: annual hourly error distribution (all matched hours)')
        fig.savefig(output / 'germany-prices.png'); plt.close(fig)
        with (output / 'germany-hourly.csv').open('w') as f:
            writer = csv.writer(f); writer.writerow(['utc', 'model_de_country_eur_mwh', 'observed_entsoe_de_lu_eur_mwh'])
            for t in range(8760):
                writer.writerow([dates[t].isoformat(), de[t], obs[t] if valid[t] else ''])
    fig, ax = plt.subplots(figsize=(11, 9), layout='constrained')
    heat = np.array([[m.get('mae_eur_mwh', np.nan) for m in r['monthly']] for r in eligible])
    im = ax.imshow(heat, aspect='auto', interpolation='nearest')
    ax.set(xticks=range(12), xticklabels=range(1, 13), yticks=range(len(eligible)), yticklabels=[r['zone'] for r in eligible], xlabel='UTC month', title='Monthly absolute price errors: no gap filling')
    fig.colorbar(im, ax=ax, label='MAE, EUR/MWh'); fig.savefig(output / 'monthly-errors.png'); plt.close(fig)
    return s, replay, result


def document(s, replay, comparison):
    c = next(c for c in s['cases'] if c['case'] == 'baseline')
    r = next(c for c in replay['checks'] if c['case'] == 'baseline')
    zones = [z for z in comparison['zones'] if z['known_hours']]
    de = next((z for z in zones if z['zone'] == 'DE-LU'), None)
    text = f'''# Full-year daily dispatch and observed prices — 2025

The current simple-resource model completed **365 daily clearings / 8,760 hourly
periods** across {len(c['zones'])} European country/AC-island areas. Storage carries
between days, with original weather availability, demand, water and exact closing
inventories. Gas/oil bids use observed monthly TTF/Brent benchmark prices with
explicit conversions; carbon remains EUR80/t and oil remains a crude proxy.

This is an **untuned comparison against observed ENTSO-E A44 prices**, not an
annual optimum, commercial EUPHEMIA reconstruction or accepted investment model.
The browser workbench has not changed. No parameters were fitted to these prices.

## Annual execution and numerical checks

| Check | Result |
| --- | ---: |
| Calendar | 365 days, 8,760 UTC hours |
| Approximate price-forecast preparation | {c['forecast_seconds']:.2f} seconds |
| Arithmetic target/reachability preparation | {c['strategy_preparation_seconds']:.2f} seconds |
| Daily bidding, including closing-mode prepasses | {c['daily_rule_seconds']:.2f} seconds |
| Daily clearing time | {c['clearing_seconds']:.2f} seconds |
| Full command, including preparation/native checks | {s['elapsed_seconds']:.2f} seconds |
| Peak memory | {s['peak_rss_mib']:.0f} MiB |
| Maximum replayed primal residual | {r['maximum_primal_residual']:.3g} |
| Maximum replayed water residual | {r['maximum_water_residual']:.3g} MWh |
| Overnight inventory join residual | {r['maximum_join_residual_mwh']:.3g} MWh |
| Year-end inventory residual | {r['closure_residual_mwh']:.3g} MWh |
| Emergency supply | {r['emergency_supply_mwh']/1e6:.6f} TWh |
| Simultaneous charge/discharge | {c['simultaneous_storage_hours']} unit-hours |
| Physical variable operating cost | EUR {c['operating_cost_eur']/1e9:.3f} billion |

Independent replay reproduces daily bid rules (including the two terminal mode-selection prepasses) and checks every saved daily primal,
source/code/input hashes, water, network limits, stock joins and closure. Forecast
optimality and all-day price dual optimality are not independently replayed.
Native PyPSA checks cover the first, middle and final day under the same bids:

| UTC day number | Native minus custom bid objective, EUR | Maximum price difference, EUR/MWh |
| --- | ---: | ---: |
'''
    for n in c['native_checks']:
        text += f"| {n['day'] + 1} | {n['difference_eur']:.6g} | {n['price_maximum_difference_eur_mwh']:.6g} |\n"
    text += '''
These are computational checks, not errors against ENTSO-E prices. The bid
objective includes storage opportunity offers and purchase willingness; it is
separate from physical operating cost, congestion rent and market expenditure.

## Closing-window feasibility exception

The purely arithmetic threshold policy reached 29 December but made the next
clearing infeasible. Diagnostics found a feasible, cycling-free physical path to
the same final inventories: the submitted storage directions were the blocker.
The final model therefore has an explicit **last-48-hour settlement exception**.

For each of those two days, a short network prepass keeps the same storage bid
prices, inflows, capacities, water/network equations and closing-stock bounds,
but makes both power directions available. It must finish optimal with no
simultaneous charging/discharging. Its nonzero storage directions then define
exclusive submitted modes for the ordinary daily clearing. The actual cleared
inventory still carries into tomorrow; no intermediate reference stock is fixed.
All earlier days retain the arithmetic rules. This is two additional daily LPs,
not per-unit annual strategy optimisation or a guarantee that other scenarios
will remain jointly feasible. No water gifts, slack or relaxed final stocks are
introduced. Exact annual closure and no-cycling checks remain mandatory.

The exception is a simulation-horizon boundary convention, not real market
practice. Annual and monthly error statistics below include both final days;
separate closing-48h metrics are downloadable to inspect boundary sensitivity.
The first failed attempt remains retained locally and is not an annual result.

## Observed price comparison

Hourly [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) A44 observations are parsed from source-receipted EUR/MWh price
responses. All four quarter-hours must be present to report an hourly mean;
negative prices remain valid and gaps remain missing. The model uses hourly UTC
24-hour days, rather than actual market-day daylight-saving and quarter-hour
clearing calendars. Weights here are one per complete hourly pair.

MAE is mean absolute error; bias is model minus observed; RMSE highlights large
errors. Correlation measures hourly co-movement, not price-level agreement. No
percentage error is used because electricity prices can be negative or near zero.
All available zones are reported; no favourable subset or calibration split was
selected after seeing errors. Quantitative acceptance thresholds remain unselected:
this report is descriptive and does not claim held-out validation.

'''
    shortage_rows = [row for row in comparison['shortage_areas'] if row['emergency_supply_mwh'] > 1.]
    text += '**Emergency supply is artificial shortage generation at the declared penalty, not observed generation.** Its use means the annual simulation is not a shortage-free market baseline; local price errors can be dominated by the penalty.\n\n| Model area | Emergency supply TWh | Shortage hours |\n| --- | ---: | ---: |\n'
    for row in shortage_rows:
        text += f"| {row['area']} | {row['emergency_supply_mwh']/1e6:.6f} | {row['shortage_hours']} |\n"
    text += '\n'
    if de:
        text += f"For Germany, {de['known_hours']:,} matched hours give **MAE EUR{de['mae_eur_mwh']:.2f}/MWh**, bias EUR{de['bias_eur_mwh']:+.2f}/MWh and RMSE EUR{de['rmse_eur_mwh']:.2f}/MWh. Correlation is {de['correlation']:.3f}; {100*de['within_10_eur_mwh_fraction']:.1f}% of matched hours lie within EUR10/MWh. Observed negative-price hours: {de['observed_negative_hours']}; model negative-price hours: {de['model_negative_hours']}. The model is Germany-only; observed DE-LU also includes Luxembourg.\n\n"
    unavailable = [z['zone'] for z in comparison['zones'] if not z['known_hours']]
    if unavailable:
        text += 'No 2025 A44 observations were retrieved for: ' + ', '.join(unavailable) + '. They remain unavailable, not zero-priced, and their failed-month records are retained.\n\n'
    text += '''![Hourly German example and annual errors](../research/daily-fuel-annual-2025/germany-prices.png)

| Observed zone | Model area | Matched hours | MAE EUR/MWh | Bias EUR/MWh | RMSE EUR/MWh | Correlation |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
'''
    for z in zones:
        corr = 'unavailable' if z['correlation'] is None else f"{z['correlation']:.3f}"
        text += f"| {z['zone']} | {z['model_area']} | {z['known_hours']} | {z['mae_eur_mwh']:.2f} | {z['bias_eur_mwh']:+.2f} | {z['rmse_eur_mwh']:.2f} | {corr} |\n"
    text += '''
![Errors for every available mapped zone](../research/daily-fuel-annual-2025/zone-errors.png)

![Monthly price-error patterns](../research/daily-fuel-annual-2025/monthly-errors.png)

## Geography and border-price separation

Model prices belong to country/AC-island areas with fixed generation-shift keys
and model-derived N-0 physical constraints, not validated commercial bidding
zones or JAO domains. Norway and Sweden each have one country price reused
against several observed zones. Italian mainland zones similarly share one
model price. Internal zone price separation is therefore absent by construction;
these comparisons reveal a scope limitation rather than validating zone identity.
Danish AC-area assignment is a proxy; Germany excludes Luxembourg. Island
comparisons with unresolved identities are excluded explicitly, not guessed.

Border diagnostics compare signed B-minus-A price spreads on jointly observed
hours, mean absolute spread errors and direction agreement when observed absolute
spread exceeds EUR5/MWh. This threshold selects price separation, not proof of
physical congestion. Same-model-area borders are flagged as collapsed. All border
rows are downloadable; congestion rent is not recalculated from these price errors.

'''
    collapsed = [e for e in comparison['borders'] if e['collapsed_model_areas']]
    text += f"Of {len(comparison['borders'])} comparable observed borders, {len(collapsed)} collapse to one model area. No cross-zone spread recovery is possible on those borders without finer geography.\n\n"
    text += 'Model areas without a comparable collected price series: ' + ', '.join(comparison['model_areas_without_observed_comparison']) + '. These are not included in price-error statistics.\n\n'
    for e in comparison['excluded']:
        text += f"- {e['zone']}: {e['reason']}.\n"
    text += '''
## Method, sources and limitations

The consolidated resource rules document wind/solar low bids,
fossil fuel/efficiency/carbon/O&M offers, prepared nuclear/other costs, adaptive
reservoir water values and loss/wear-adjusted storage buy/sell thresholds. Clearing
quantities remain decisions under exact storage physics; no daily stock reset or
fixed hydro-generation schedule is used. Price expectations use perfect exogenous
inputs with a storage-free approximation, not realised ENTSO-E prices.

The consolidated fuel inputs document World Bank monthly 2025 TTF
and Brent and ECB reference FX. Monthly prices are held constant over UTC hours.
Heating-basis multiplier1 is an explicit unverified compatibility assumption;
Brent assumes1.7 MWh thermal/barrel and is not a delivered refined oil-product
price. Carbon EUR80/t and coal/lignite fuel costs remain assumptions. No observed
EUA trajectory or local fuel-delivery premium is represented.

The prepared PyPSA-Eur source supplies demand, weather profiles, hydrology,
efficiencies and physical constraints. Original renewable availability is preserved;
IRENA end-2024/end-2025 linear wind/solar capacity interpolation is the declared
baseline commissioning assumption. Source nuclear availability is a previous-year
proxy; unit commitment, detailed outages and nonconvex market orders are absent.
Hydro targets, water values and battery thresholds are heuristics, not optimal or
calibrated operator strategies. Annual closure uses retained-reference initial and
final stocks, without fixed intermediate states. Closing-day settlement can affect
final-day prices and is not real market practice.

## Conclusion and next steps

Completing and replaying the year establishes that this rule-based daily model
can execute within the memory budget. It still takes about nine minutes end to end,
so it has not reached the seconds-scale interactive target. Emergency supply and
negative-price mismatches remain material adequacy/market-validity limitations. Numerical consistency with native PyPSA
checks does not establish realistic market prices. The observed errors above are
the baseline diagnostic for improving fuel/availability, commercial geography,
constraints and resource strategies; they must not be hidden by calibration.
Before accepting scenario values, define training/held-out periods and thresholds,
compare generation and exchanges, and verify matched investment cases. Neither
annual optimality nor avoided emissions follows from these price comparisons.

Reproduce with `tools/terminal_daily_market.py --hours 8760 --fuel-prices ...
--rules config/simple-bidding/defaults.json --native --output <fresh-root>`, then
`tools/audit_terminal_daily_market.py <fresh-root> --native --output <fresh-root>/replay.json`.
`tools/collect_dispatch_validation_prices.py` collects A44 evidence offline;
`tools/compare_daily_dispatch_prices.py` generates this untuned comparison.
Large raw inputs and witnesses remain ignored; public artifacts are compact.

Download [price metrics and source receipts](../research/daily-fuel-annual-2025/price-comparison.json),
[zone errors CSV](../research/daily-fuel-annual-2025/zone-errors.csv),
[border errors CSV](../research/daily-fuel-annual-2025/border-errors.csv),
[German hourly pairs](../research/daily-fuel-annual-2025/germany-hourly.csv.gz),
[run summary](../research/daily-fuel-annual-2025/summary.json.gz) and
[independent replay](../research/daily-fuel-annual-2025/replay.json).
'''
    return text


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--observed', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--document', type=Path, required=True)
    a = p.parse_args()
    s, replay, comparison = compare(a.run, a.observed, a.output)
    rendered = document(s, replay, comparison)
    methods = (Path(__file__).parent / 'report-templates/daily-resource-methods.md').read_text()
    a.document.write_text(rendered.replace('## Conclusion and next steps', methods + '\n## Conclusion and next steps'))
    for artifact in a.output.iterdir():
        if artifact.suffix == '.csv':
            artifact.write_text('\n'.join(line.rstrip() for line in artifact.read_text().splitlines()) + '\n')
    hourly = a.output / 'germany-hourly.csv'
    (a.output / 'germany-hourly.csv.gz').write_bytes(gzip.compress(hourly.read_bytes(), mtime=0))
    hourly.unlink()
