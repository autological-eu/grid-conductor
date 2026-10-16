"""Render the two-model report from independently replayed saved-run comparisons.

No fitting or clearing. Bulk hourly evidence remains in the ignored input root.
"""
import argparse
import csv
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from generation_mix_2025 import ROOT, digest

PUBLIC = ROOT / 'public/research/dispatch-comparison-2025'
ARTICLE = ROOT / 'docs/european-physical-synthetic-clearing-2025.md'
PREFIX = '/research/dispatch-comparison-2025/'
LABELS = {'control': 'Baseline', 'combined': 'Exploratory'}
FOCUS = ['NO1', 'NO2', 'NO3', 'NO4', 'NO5', 'DE-LU', 'ES', 'FR']
GREY, ORANGE, BLACK = '#8696a8', '#c86616', '#182a3b'


def csv_file(name, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (PUBLIC / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def save(fig, name):
    fig.savefig(PUBLIC / name, dpi=150, facecolor='white', bbox_inches='tight')
    plt.close(fig)


def write(folder):
    s = json.loads((folder / 'summary.json').read_text())
    audit_path = folder / 'verification-v1/audit.json'
    audit = json.loads(audit_path.read_text())
    assert audit['summary_sha256'] == digest(folder / 'summary.json')
    assert audit['generation_areas'] == 38 and audit['price_areas'] == 41
    assert audit['auditor_sha256'] == digest(ROOT / 'tools/audit_concise_dispatch_report_2025.py')
    assert s['producer_sha256'] == digest(ROOT / 'tools/prepare_concise_dispatch_report_2025.py')
    assert s['witness_sha256'] == digest(folder / 'comparison.npz')
    for name, sha in s['source_hashes'].items():
        assert digest(ROOT / name) == sha
    for name, sha in s['dependencies'].items():
        assert digest(ROOT / 'tools' / name) == sha
    with np.load(folder / 'comparison.npz') as f:
        a = {k: f[k] for k in f.files}
    model = ROOT / 'data/bidding-zone-network-2025/hourly-offer-curves-v1'
    with np.load(model / 'evaluation-targets.npz') as f:
        observed_price = f['prices']
    PUBLIC.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.titleweight': 'bold'})
    results = s['results']
    p = {n: {r['zone']: r for r in results[n]['price_summary']['zones']} for n in LABELS}
    g = {n: {r['area']: r for r in results[n]['generation_summary']} for n in LABELS}
    coverage = {r['area']: r for r in s['coverage']}
    price_rows, generation_rows, detail_rows = [], [], []
    for area in s['zones']:
        row = {'area': area}
        for n in LABELS:
            row.update({LABELS[n].lower() + '_' + k: v for k, v in p[n][area].items()
                        if k != 'zone' and not isinstance(v, list)})
        price_rows.append(row)
        row = dict(coverage[area])
        for n in LABELS:
            row.update({LABELS[n].lower() + '_' + k: v for k, v in g[n][area].items() if k != 'area'})
        generation_rows.append(row)
    for i, r in enumerate(results['control']['generation_detail']):
        row = dict(area=r['area'], technology=r['technology'],
                   model_generation_domain=coverage[r['area']]['model_generation_domain'],
                   source_scope=coverage[r['area']]['source_scope'])
        for n in LABELS:
            rr = results[n]['generation_detail'][i]
            assert rr['area'] == r['area'] and rr['technology'] == r['technology']
            row.update({LABELS[n].lower() + '_' + k: v for k, v in rr.items()
                        if k not in ['area', 'technology']})
        detail_rows.append(row)
    csv_file('prices-by-zone.csv', price_rows)
    csv_file('generation-by-area.csv', generation_rows)
    csv_file('generation-by-fuel.csv', detail_rows)
    country_rows = []
    for j, country in enumerate(s['countries']):
        for k, fuel in enumerate(s['ember_fuels']):
            ref = a['ember_reference_twh'][j, k]
            row = dict(country=country, fuel=fuel, observed_twh=float(ref) if np.isfinite(ref) else None)
            for n in LABELS:
                for kind in ['point', 'lower', 'upper']:
                    row[LABELS[n].lower() + '_' + kind + '_twh'] = float(a[n + '_country_' + kind + '_twh'][j, k])
            country_rows.append(row)
    csv_file('national-generation.csv', country_rows)

    # Identical axes: below the diagonal means lower error. All eligible areas.
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), layout='constrained')
    definitions = [(g, 'volume_error_percent', 'Generation: 38 reporting areas', 'Covered-fuel volume error (%)'),
                   (p, 'mae_eur_mwh', 'Prices: 41 bidding zones', 'Hourly price MAE (EUR/MWh)')]
    for ax, (data, key, title, unit) in zip(axes, definitions):
        areas = [area for area in s['zones'] if data['control'][area].get(key) is not None]
        x = [data['control'][area][key] for area in areas]
        y = [data['combined'][area][key] for area in areas]
        top = max(x + y) * 1.12
        ax.plot([0, top], [0, top], '--', color='#b7c2cb', linewidth=1)
        ax.scatter(x, y, s=28, color=GREY, alpha=.7)
        offsets = {'NO2': (8, 10), 'DE-LU': (12, -8), 'ES': (12, -15), 'FR': (-15, 15)} if data is g else {
            'NO2': (8, 10), 'DE-LU': (15, 10), 'ES': (15, -20), 'FR': (-28, 12)}
        for area, delta in offsets.items():
            xv, yv = data['control'][area][key], data['combined'][area][key]
            ax.scatter([xv], [yv], color=ORANGE, s=35, zorder=3)
            ax.annotate('DE' if area == 'DE-LU' and data is g else area, (xv, yv),
                        xytext=delta, textcoords='offset points', fontsize=9,
                        arrowprops=dict(arrowstyle='-', color='#8f9aa3', linewidth=.6))
        ax.set(xlim=(0, top), ylim=(0, top), xlabel='Baseline — ' + unit,
               ylabel='Exploratory — ' + unit, title=title)
        ax.set_aspect('equal')
        ax.grid(alpha=.15)
    fig.suptitle('July–December 2025 · points below the diagonal improve', fontsize=12)
    save(fig, 'overview.png')

    # National references are separate from the zonal ENTSO-E comparison above.
    colors = ['#5697cc', '#edc24d', '#9676b5', '#3d9b9a', '#da8455', '#626b73', '#91ac60', '#bc9c87', '#c7afce']
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout='constrained')
    for j, (country, ax) in enumerate(zip(s['countries'], axes.flat)):
        refs = a['ember_reference_twh'][j]
        known = np.isfinite(refs)
        rows = np.stack([refs, a['control_country_point_twh'][j], a['combined_country_point_twh'][j]])[:, known]
        total = rows.sum(axis=1)
        left = np.zeros(3)
        for k in np.flatnonzero(known):
            vals = np.array([refs[k], a['control_country_point_twh'][j, k], a['combined_country_point_twh'][j, k]]) / total * 100
            ax.barh(range(3), vals, left=left, color=colors[k], height=.58)
            left += vals
        for i, value in enumerate(total):
            ax.text(102, i, f'{value:.1f} TWh', va='center', fontsize=9)
        ax.set(title=country + ' · national, covered fuels', xlim=(0, 130),
               yticks=range(3), yticklabels=['Observed (Ember)', 'Baseline', 'Exploratory'],
               xticks=[0, 25, 50, 75, 100], xlabel='Share of covered generation (%)')
        ax.invert_yaxis()
    fig.legend([plt.Rectangle((0, 0), 1, 1, color=c) for c in colors], s['ember_fuels'],
               loc='outside lower center', ncol=5, frameon=False, fontsize=9)
    fig.suptitle('July–December 2025 · model fuel splits are illustrative', fontsize=12)
    save(fig, 'national-mix.png')

    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout='constrained')
    utc = pd.date_range('2025-07-01', periods=4416, freq='h', tz='UTC')
    timezones = ['Europe/Oslo', 'Europe/Berlin', 'Europe/Madrid', 'Europe/Paris']
    for ax, area, tz in zip(axes.flat, ['NO2', 'DE-LU', 'ES', 'FR'], timezones):
        j = s['zones'].index(area)
        hours = utc.tz_convert(ZoneInfo(tz)).hour
        for values, label, color in [(observed_price[:, j], 'Observed ENTSO-E', BLACK),
                                      (a['control_prices'][:, j], 'Baseline', GREY),
                                      (a['combined_prices'][:, j], 'Exploratory', ORANGE)]:
            ax.plot(range(24), [np.nanmean(values[hours == h]) for h in range(24)], label=label, color=color, linewidth=2)
        ax.set(title=area + ' · ' + tz, xlabel='Local hour (DST applied)', ylabel='Mean price (EUR/MWh)',
               xticks=[0, 6, 12, 18, 23])
        ax.grid(alpha=.15)
    axes[0, 0].legend(frameon=False, fontsize=9)
    fig.suptitle('July–December 2025 · average daily price profile', fontsize=12)
    save(fig, 'daily-prices.png')

    def fmt(value, digits=2):
        return '—' if value is None else f'{value:.{digits}f}'
    focus_table = '\n'.join('| ' + ' | '.join([area,
        fmt(g['control'][area]['volume_error_percent'], 1) + ' → ' + fmt(g['combined'][area]['volume_error_percent'], 1),
        fmt(p['control'][area]['mae_eur_mwh']) + ' → ' + fmt(p['combined'][area]['mae_eur_mwh']),
        fmt(p['control'][area]['correlation'], 3) + ' → ' + fmt(p['combined'][area]['correlation'], 3)]) + ' |' for area in FOCUS)
    aggregate = {n: results[n]['price_summary'] for n in LABELS}
    gm = {n: np.median([r['volume_error_percent'] for r in g[n].values() if r['volume_error_percent'] is not None]) for n in LABELS}
    improved_g = sum(g['combined'][area]['volume_error_percent'] < row['volume_error_percent'] for area, row in g['control'].items() if row['volume_error_percent'] is not None)
    improved_p = sum(p['combined'][area]['mae_eur_mwh'] < row['mae_eur_mwh'] for area, row in p['control'].items() if row['known_hours'])
    report = f'''# European dispatch: baseline and exploratory supply bids

## Summary

The exploratory model makes thermal supply curves steeper while retaining the baseline's demand, fleet, weather, fixed hydro and network constraints. Across **41 price zones**, July–December mean zonal price MAE improves **32.20 → 30.03 EUR/MWh**, and mean correlation **0.407 → 0.448**. Generation agreement improves in some areas, but substantial quantity and Nordic price errors remain. This is a useful bid experiment, not an accepted investment estimator or replacement for the workbench's browser engine.

All comparisons below use **July–December 2025: 4,416 UTC hours**. Both saved runs cover all 8,760 hours; using their evaluation period here keeps generation and price results comparable. Earlier experiments are omitted from this report.

## 1. Baseline model

**Clearing.** The model minimizes accepted supply-bid cost subject to fixed demand, available generation and physical network constraints. A sparse linear program clears each hour independently; zonal balance duals provide hourly prices. Hours are orchestrated in daily batches, but there is **no intertemporal daily optimization**. No ramping, unit commitment, endogenous battery operation or reservoir rescheduling is included.

**Geography and constraints.** The retained European backbone has **48 clearing areas and 145 physical buses**, separating Norway's five zones, Sweden's four, Denmark's two and Italy's seven. DE-LU and Ireland's shared market are combined; peripheral modeled areas are not all certified commercial bidding zones. Capacity-based generation shift keys (GSKs) locate zonal dispatch on physical buses. AC flow sensitivities, separate electrical-island balances, intrazonal branch constraints and HVDC bounds/losses remain. A uniform **0.7 security factor** limits branch ratings. These are model-derived N-0 constraints, not JAO commercial capacity domains, explicit N-1 security or full EUPHEMIA order allocation.

**Supply and demand.** Each generator contributes its original hourly available MW and resource bid. Wind/solar retain low-cost offers; thermal bids use fuel cost divided by efficiency, plus carbon and variable operating costs. Other technologies retain their source cost profiles. Demand is fixed, using the prepared 2025 series; spatial splits across newly separated zones include proxies. It is not yet independently certified observed load in every bidding zone. Emergency offers at 10,000 EUR/MWh diagnose shortage and are excluded from real generation-mix totals.

**Hydro.** Reservoir output is precomputed and fixed hour by hour. Norwegian preparation uses NVE weather-driven HBV inflow and reservoir boundary stocks, preserving turbine limits, chronological inventories and efficiency once on discharge. Other countries retain their reference schedules. Run-of-river remains a dispatchable available offer. Reservoirs cannot respond to changed bids or investments during clearing; national Norwegian water pooling and location assumptions remain limitations.

### Data used

| Component | Source and treatment |
| --- | --- |
| Grid, plants, efficiencies and inherited profiles | Pinned [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) v2026.08.0 backbone; original source/replay evidence retained. Nuclear availability ending in 2024 is a proxy; gas/nuclear available MW can be flat. |
| Wind/solar capacity and weather | [IRENA](https://www.irena.org/Data) end-2024/end-2025 capacities interpolated linearly through 2025, with retained ERA5-derived hourly profiles. This assumes commissioning dates; observed generation is never substituted for availability. Mixed-cluster location shares include proxies. |
| Fuel bids | [World Bank](https://www.worldbank.org/en/research/commodity-markets) monthly TTF gas/Brent oil and [ECB](https://data.ecb.europa.eu/) FX, inherited efficiency/carbon/VOM assumptions. Delivered-fuel, heating-value and EUA assumptions need further validation. |
| Norwegian reservoir inputs | [NVE hydrological data](https://www.nve.no/energi/analyser-og-statistikk/hydrologiske-data-til-kraftsituasjonsrapporten/): weather-driven inflow, stocks and capacity; retrospective revisions and gross-stock/net-inflow compatibility remain caveats. |
| Prices and hourly generation checks | [ENTSO-E Transparency](https://transparency.entsoe.eu/) A44 day-ahead prices and A75 generation by production type, with hashed source replay and UTC alignment. |
| National generation cross-check | [Ember](https://ember-energy.org/data/) monthly generation by fuel, July–December summed separately from hourly ENTSO-E checks. |

## 2. Exploratory model: what changes

Only the **shape of gas and coal/lignite bids** changes. Original available capacity is partitioned into three progressively more expensive blocks; no capacity is added.

| Offer component | Baseline | Exploratory |
| --- | --- | --- |
| Gas available MW | Original resource bid | 50% at original bid; 35% at +21; 15% at +60 EUR/MWh |
| Coal/lignite available MW | Original resource bid | 50% at original bid; 35% at +15.75; 15% at +45 EUR/MWh |
| Nuclear | Original running-cost offer | Same; no peaking blocks |
| Regional offsets / renewable discount | Zero | Zero: tested adjustments were not selected |
| Demand, physical inputs, hydro and other bids | Retained baseline | Identical |

The block adders represent synthetic effective bids, not measured exchange orders. Jan–April fits bounded proposals; May–June selects a predeclared finite configuration using equally weighted, control-normalized price MAE, daily-demeaned price MAE, monthly generation-interval error and implied-trade error, plus regularization. July–December is evaluated afterward. Historical training prices enter this experiment; evaluation prices and generation do not enter fitting or selection. Since 2025 was previously inspected, this is **retrospective temporal evaluation**, not untouched validation.

Both runs use the same split-column representation, with zero adders for the baseline control. This avoids comparing different formulations' arbitrary dual witnesses; even equivalent LP representations can produce different prices when the optimum is non-unique. The retained annual-v7 baseline is not promoted or overwritten.

## 3. Generation and price performance

![Generation and price errors for every covered area; points below the diagonal improve]({PREFIX}overview.png)

Price coverage is **41 of 48 modeled areas**; BA, GB, IE-SEM, ME, IT-CALA, FR-COR and XK have no comparison price. Generation coverage is **38 reporting areas**, with differing fuel/hour coverage. NO1–NO4 have zonal hourly generation, but NO5 has none. Germany's generation comparison is **DE national, excluding LU**, while its price comparison is DE-LU. France's generation comparison uses national model membership including modeled Corsica. National reporting areas and modeled geography are not automatically identical commercial zones.

| Metric, July–December | Baseline | Exploratory |
| --- | ---: | ---: |
| Equal-zone hourly price MAE, EUR/MWh | {aggregate['control']['equal_zone_mae']:.2f} | {aggregate['combined']['equal_zone_mae']:.2f} |
| Mean zonal price correlation | {aggregate['control']['mean_correlation']:.3f} | {aggregate['combined']['mean_correlation']:.3f} |
| Mean within-day price correlation | {aggregate['control']['mean_demeaned_correlation']:.3f} | {aggregate['combined']['mean_demeaned_correlation']:.3f} |
| Daily-demeaned price MAE, EUR/MWh | {aggregate['control']['mean_demeaned_mae']:.2f} | {aggregate['combined']['mean_demeaned_mae']:.2f} |
| Median covered-fuel generation volume error, % | {gm['control']:.1f} | {gm['combined']:.1f} |

Price MAE improves in **{improved_p}/41 zones** and worsens in {41-improved_p}; generation volume error improves in **{improved_g}/38 areas**. Generation error sums absolute fuel-volume differences and divides by observed generation, using only each fuel's known hours. It can exceed 100%; it is not a generation-share percentage-point error or a complete-fleet score. Coverage differs between areas, so comparisons are paired within each area. This descriptive metric differs from the monthly interval-based fitting score.

Saved dispatch is disaggregated proportionally to original available MW within equal-bid groups. These fuel allocations are **illustrative**, not uniquely identified dispatch. Downloads include conditional lower/upper allocations; those bounds are not jointly attainable and do not span all possible LP optima. Missing observations stay missing; pumped-storage production is excluded from primary generation.

## 4. Norway, Germany, Spain and France

![National fuel shares and covered generation totals for Norway, Germany, Spain and France]({PREFIX}national-mix.png)

National Ember cross-check, same six months. Shares and TWh totals cover only fuels with all six observed months: NO nuclear/coal and FR other renewables are unavailable and excluded from all three bars, not filled with zero. National Norwegian totals include NO5; they are not allocated into its missing zonal observations. Model bars use illustrative fuel allocation; the CSV includes bounds and all modeled fuel volumes.

| Area | Generation volume error, %: baseline → exploratory | Price MAE, EUR/MWh: baseline → exploratory | Price correlation: baseline → exploratory |
| --- | ---: | ---: | ---: |
{focus_table}

Generation in the DE-LU row means **Germany national**; FR is national; Norway rows use their available zonal series. A dash denotes unavailable generation verification.

**Norway:** the bid change does not fix the main weakness. National modeled hydro remains about **74.83 TWh**, against Ember's **68.06 TWh** for these months. Yet national agreement cannot establish correct zonal water allocation: NO1's covered-fuel error is about 74%, and price correlations remain weak or negative across the five zones. NO2 is the illustrative price profile below, not a national Norwegian price.

**Germany:** gas rises **18.50 → 25.79 TWh**, closer to Ember's **38.53 TWh**; coal rises **15.88 → 20.30 TWh**, still below **45.32 TWh**. Wind remains **94.05 TWh** versus **71.07 TWh** observed. Better prices coexist with a large generation mismatch; bids alone have not resolved fleet/weather/demand scope.

**Spain:** national mix is comparatively close: gas moves **28.49 → 30.18 TWh** versus **29.66 TWh** observed. Price correlation improves markedly, but mean bias worsens **+3.12 → +7.58 EUR/MWh**. Wind stays about **21.07 TWh** versus Ember's **27.56 TWh**; similarity in totals does not imply each fuel or hour is right.

**France:** nuclear remains **180.18 → 179.74 TWh**, below **190.52 TWh** observed; hydro is **15.92** versus **22.55 TWh**. Generation error slightly worsens despite a small price improvement. Inherited nuclear availability and fixed hydro remain source/operational assumptions to investigate.

![Observed and simulated average local-hour price profiles for NO2, DE-LU, ES and FR]({PREFIX}daily-prices.png)

Profiles average evaluation-period prices by **local clock hour, with DST applied**; they are not a selected day or an hourly forecast trace. Aggregate within-day metrics above remove each UTC day's mean. The exploratory model captures more daily variation, but still misses price extremes: Spain's mean daily range is **81.61** versus observed **98.10 EUR/MWh**, with **zero modeled versus 97 observed negative-price hours**. Hour-to-hour ramp MAE slightly worsens **12.49 → 12.75 EUR/MWh**. A better average profile is not a complete hourly fit.

## Conclusion and verification

Steeper thermal offers improve broad price movement without changing physical supply, but the gains are moderate and uneven. **Retain the baseline; keep this as an exploratory bid model.** Priorities are source timing and operational availability, wind quantities, Nordic water/geography and demand scope, followed by a fresh predeclared evaluation. Matching generation totals or passing numerical replay does not validate investment effects, adaptive storage value or commercial congestion rents.

Both annual witnesses have **8,760 optimal hours and zero emergency generation**. Independent replay covers original component feasibility, block-summed availability, LP duals and chronological selection: maximum physical residual **6.71×10⁻⁶ MW**, duality gap **EUR 0.000138**. Annual clearing took **29.71s baseline / 38.92s exploratory**, excluding preparation; the complete fitting/selection/evaluation command took **337.97s**. These are recorded run measurements, not current job-status claims. A separate source-column replay verifies this report's generation geography, allocations, observations and metrics; rewriting ran no new market solve.

### Data and reproducibility

- [All-zone price metrics]({PREFIX}prices-by-zone.csv), including bias, hourly errors, within-day metrics and missing coverage.
- [Generation coverage and errors by area]({PREFIX}generation-by-area.csv), [fuel volumes, hourly errors and conditional bounds]({PREFIX}generation-by-fuel.csv), and [national Ember comparison]({PREFIX}national-generation.csv).
- [Compact provenance and verification receipt]({PREFIX}summary.json), with hashes linking the original model, source replay and report assets. Full source/hourly witnesses stay locally cached outside Git.
- Model formulation: [hourly_offer_curves_2025.py](tools/hourly_offer_curves_2025.py); [independent model replay](tools/audit_hourly_offer_curves_2025.py). Report derivation: [prepare_concise_dispatch_report_2025.py](tools/prepare_concise_dispatch_report_2025.py), [independent report replay](tools/audit_concise_dispatch_report_2025.py), [figure/report renderer](tools/write_concise_dispatch_report_2025.py).
'''
    ARTICLE.write_text(report)
    assets = {path.name: digest(path) for path in sorted(PUBLIC.iterdir()) if path.name != 'summary.json'}
    receipt = dict(period=s['period'], models=LABELS, generation_reporting_areas=38, observed_price_zones=41,
                   derived_summary_sha256=digest(folder / 'summary.json'), derived_witness_sha256=s['witness_sha256'],
                   report_audit=audit, report_audit_sha256=digest(audit_path),
                   original_model_summary_sha256=s['original_model_summary_sha256'],
                   original_model_audit_sha256=s['original_model_audit_sha256'],
                   derived_producer_sha256=s['producer_sha256'], renderer_sha256=digest(__file__),
                   article_sha256=digest(ARTICLE), assets=assets, limitations=s['limitations'])
    (PUBLIC / 'summary.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(f'Wrote {len(report.split())} words; {len(assets)} compact assets; no market solve')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('folder', type=Path)
    write(p.parse_args().folder)
