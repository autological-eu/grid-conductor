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
    auditor_file = audit.get('auditor_file', 'audit_concise_dispatch_report_2025.py')
    producer_file = s.get('producer_file', 'prepare_concise_dispatch_report_2025.py')
    assert auditor_file in ['audit_concise_dispatch_report_2025.py', 'audit_intraday_dispatch_report_2025.py', 'audit_seasonal_dispatch_report_2025.py']
    assert producer_file in ['prepare_concise_dispatch_report_2025.py', 'prepare_intraday_dispatch_report_2025.py', 'prepare_seasonal_dispatch_report_2025.py']
    assert audit['auditor_sha256'] == digest(ROOT / 'tools' / auditor_file)
    assert s['producer_sha256'] == digest(ROOT / 'tools' / producer_file)
    assert s['witness_sha256'] == digest(folder / 'comparison.npz')
    for name, sha in s['source_hashes'].items():
        assert digest(ROOT / name) == sha
    for name, sha in s['dependencies'].items():
        assert digest(ROOT / 'tools' / name) == sha
    with np.load(folder / 'comparison.npz') as f:
        a = {k: f[k] for k in f.files}
    model = ROOT / s.get('model_folder', 'data/bidding-zone-network-2025/hourly-offer-curves-v1')
    ms = json.loads((model / 'summary.json').read_text())
    ma = json.loads((model / 'verification-v1/audit.json').read_text())
    assert digest(model / 'summary.json') == s['original_model_summary_sha256'] == ma['summary_sha256']
    params = [f['winner'] for f in ms['folds']]
    assert ms['status'] == 'seasonal_calendar_oof_and_separate_insample_refit_not_promoted'
    with np.load(model / 'development-targets.npz') as f:
        half_prices = f['prices']
    with np.load(model / 'evaluation-targets.npz') as f:
        observed_price = np.concatenate([half_prices, f['prices']])
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
    fig.suptitle('2025 · out-of-fold evaluation · points below the diagonal improve', fontsize=12)
    save(fig, 'overview.png')

    # One tile per modeled area, ordered by area name, with common delta scale.
    from matplotlib.colors import TwoSlopeNorm
    changes = [p['combined'][z]['mae_eur_mwh'] - p['control'][z]['mae_eur_mwh']
               for z in s['zones'] if p['control'][z]['known_hours']]
    limit = max(1., max(abs(v) for v in changes))
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0., vmax=limit)
    cmap = plt.get_cmap('RdBu_r')
    fig, ax = plt.subplots(figsize=(12, 8), layout='constrained')
    for i, area in enumerate(sorted(s['zones'])):
        row, col = divmod(i, 6)
        known = p['control'][area]['known_hours'] > 0
        if known:
            old = p['control'][area]['mae_eur_mwh']; new = p['combined'][area]['mae_eur_mwh']; delta = new - old
            color = cmap(norm(delta)); text = f'{area}\n{old:.1f} → {new:.1f}\nΔ {delta:+.1f}'
            ink = 'white' if abs(delta) > .6 * limit else BLACK
        else:
            color = '#e6e9ed'; text = f'{area}\nNo observed price'; ink = '#53606d'
        ax.add_patch(plt.Rectangle((col, row), 1, 1, facecolor=color, edgecolor='white', linewidth=3))
        ax.text(col+.5, row+.5, text, ha='center', va='center', color=ink, fontsize=10)
    ax.set(xlim=(0, 6), ylim=(8, 0), xticks=[], yticks=[],
           title='Price MAE by zone · baseline → exploratory (EUR/MWh)\n2025 · out-of-fold evaluation · blue improves, red worsens')
    for spine in ax.spines.values():spine.set_visible(False)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, shrink=.7,
                 label='Change in MAE: exploratory − baseline (EUR/MWh)')
    save(fig, 'zone-mae-grid.png')

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
    fig.suptitle('2025 · out-of-fold evaluation · model fuel splits are illustrative', fontsize=12)
    save(fig, 'national-mix.png')

    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout='constrained')
    utc = pd.date_range('2025-01-01', periods=8760, freq='h', tz='UTC')
    timezones = ['Europe/Oslo', 'Europe/Berlin', 'Europe/Madrid', 'Europe/Paris']
    for ax, area, tz in zip(axes.flat, ['NO2', 'DE-LU', 'ES', 'FR'], timezones):
        j = s['zones'].index(area)
        hours = utc.tz_convert(ZoneInfo(tz)).hour
        for months, band, color in [([1, 2, 12], 'Winter', '#287ab5'), ([6, 7, 8], 'Summer', ORANGE)]:
            season_mask = np.isin(utc.month, months)
            for values, label, style in [(observed_price[:, j], 'observed', '-'),
                                          (a['combined_prices'][:, j], 'modeled', '--')]:
                ax.plot(range(24), [np.nanmean(values[(hours == h) & season_mask]) for h in range(24)],
                        label=band + ' ' + label, color=color, linestyle=style, linewidth=2)
        ax.set(title=area + ' · ' + tz, xlabel='Local hour (DST applied)', ylabel='Mean price (EUR/MWh)',
               xticks=[0, 6, 12, 18, 23])
        ax.grid(alpha=.15)
    axes[0, 0].legend(frameon=False, fontsize=9)
    fig.suptitle('2025 · winter/summer daily prices · model is out of fold', fontsize=12)
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
    def cv(country, fuel, name='combined'):
        return a[name + '_country_point_twh'][s['countries'].index(country), s['ember_fuels'].index(fuel)]
    def pr(area, key, name='combined'):
        return p[name][area][key]
    new = aggregate['combined']
    certs = ma['certificates']
    physical_residual = max(r['original_physical_residual_mw'] for r in certs)
    duality_gap = max(r['duality_gap_maximum_eur'] for r in certs)
    from generation_mix_2025 import MONTH
    methods=['Unchanged', 'Calendar', 'Calendar + Ember']
    fold_rows=[]
    eligible=[j for j,z in enumerate(s['zones']) if p['control'][z]['known_hours']]
    for f in ms['folds']:
        ids=np.isin(MONTH,f['split']['test'])
        baseline_mae=float(np.mean(np.mean(abs(a['control_prices'][ids][:,eligible]-observed_price[ids][:,eligible]),axis=0)))
        months=lambda role: ', '.join(str(m) for m in f['split'][role])
        fold_rows.append(f"| {f['index']+1} | {months('fit')} | {months('selection')} | {months('test')} | {methods[f['winner']]} | {baseline_mae:.2f} → {f['test_metrics']['equal_zone_mae']:.2f} |")
    fold_table='\n'.join(fold_rows)
    selection_tradeoff='; '.join(f"fold {f['index']+1}: {f['records'][1]['raw']['price']:.2f} → {f['records'][2]['raw']['price']:.2f}" for f in ms['folds'])
    def rv(country,fuel):
        return a['ember_reference_twh'][s['countries'].index(country),s['ember_fuels'].index(fuel)]
    test_seconds=sum(f['test']['clearing_seconds'] for f in ms['folds'] if not f['test'].get('external'))
    refit=ms['outcomes']['refit']['prices']
    report = f'''# European dispatch: seasonal supply bids and price validation

## Summary

The exploratory model now uses **seasonal and time-of-day supply-bid patterns, without residual demand as a fitted bid predictor**. Demand and weather-dependent available supply still enter the physical clearing problem. Monthly Ember generation informs an optional resource-specific seasonal bid correction; ENTSO-E prices validate the resulting coupled clearing prices.

Across **41 observed-price zones**, full-2025 out-of-fold price MAE changes **{aggregate['control']['equal_zone_mae']:.2f} → {new['equal_zone_mae']:.2f} EUR/MWh**, mean correlation **{aggregate['control']['mean_correlation']:.3f} → {new['mean_correlation']:.3f}**, and within-day correlation **{aggregate['control']['mean_demeaned_correlation']:.3f} → {new['mean_demeaned_correlation']:.3f}**. MAE improves in **{improved_p}/41 zones**; Belgium, France and NO5 worsen. These are retrospective reconstruction/interpolation results, not verified actual bids or an accepted investment model.

## 1. Baseline model and data

**Clearing.** An hourly sparse linear program minimizes accepted resource-bid cost under fixed demand, original available generation and network constraints. Zonal balance duals provide prices. Hours are independent: daily processing does not add ramping, unit commitment, batteries or intertemporal reservoir optimization.

**Geography.** The retained network has **48 clearing areas and 145 physical buses**, with separate NO1–NO5, SE1–SE4, DK1/DK2 and seven Italian zones. DE-LU is combined; peripheral modeled areas are not all certified commercial bidding zones. Capacity-based generation shift keys locate zonal supply on physical buses. AC flow sensitivities, electrical-island balances, intrazonal branch limits and HVDC bounds/losses remain. A uniform **0.7 security factor** applies to branch ratings. These are model-derived N-0 constraints, not JAO commercial domains, explicit N-1 security or full EUPHEMIA allocation.

**Supply, demand and hydro.** Original resource bids use plant fuel/efficiency/carbon/operating-cost profiles; wind/solar retain zero offers. No earlier price-fitted thermal step markups are inherited in this experiment. Prepared 2025 demand is fixed, with source/member allocation proxies where historical aggregation crossed zones; it is not certified metered zonal load everywhere. Reservoir output is precomputed and fixed hourly. Norway uses NVE weather-driven HBV inflow and boundary stocks; other countries retain source schedules. Inventories, turbine limits and efficiency remain unchanged, without daily water resets. Run-of-river is an available offer. Fixed reservoir output cannot adapt to an investment or acquired bidding flexibility. Emergency offers at 10,000 EUR/MWh diagnose shortage and are excluded from real generation totals.

| Component | Source and treatment |
| --- | --- |
| Grid, plants, demand and inherited profiles | Pinned [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) v2026.08.0 backbone and retained source/replay coefficients. Location/load splits include proxies; nuclear availability ending in 2024 is a proxy, not audited 2025 outages. |
| Wind/solar availability | [IRENA](https://www.irena.org/Data) end-2024/end-2025 capacity interpolation plus retained ERA5-derived hourly profiles. Linear commissioning is assumed; observed generation never replaces availability. |
| Fuel and baseline bids | [World Bank](https://www.worldbank.org/en/research/commodity-markets) monthly TTF/Brent, [ECB](https://data.ecb.europa.eu/) FX, inherited carbon/efficiency/VOM assumptions. Delivered fuel, heating-value and EUA details remain imperfect. |
| Norwegian reservoir water | [NVE](https://www.nve.no/energi/analyser-og-statistikk/hydrologiske-data-til-kraftsituasjonsrapporten/) HBV inflow, stocks and capacity, with chronological stored/electrical-unit conversion. Retrospective revisions, national pooling and gross-stock/net-inflow compatibility remain limitations. |
| Price targets / hourly generation checks | [ENTSO-E Transparency](https://transparency.entsoe.eu/) A44 prices and A75 generation by type, source-hashed and UTC-aligned. Test-month prices do not construct bids. |
| Monthly generation signal and national check | [Ember](https://ember-energy.org/data/) national monthly fuel generation. Only fitting months inform bid corrections; each test month's generation remains excluded from its calibration and selection. |

## 2. Exploratory seasonal bids

The bids themselves change **before clearing**; predicted prices are never overwritten afterward. Physical demand, fleet capacity, hourly availability, hydro, GSKs and network rows stay identical to the baseline.

**Calendar pattern.** Each zone has a smooth annual level plus daily morning/evening harmonics. Annual sine/cosine terms also change the daily pattern through the seasons, rather than reusing one winter profile in summer. The 15 calendar coefficients comprise an intercept, two annual terms, four daily terms and eight seasonal–daily interactions. Local clock hours include DST. Ridge fitting uses only fitting-month observed-minus-baseline price errors, clipped at ±100 EUR/MWh; unsupported price zones get zero coefficients. No residual-demand, demand or observed-generation series enters this hourly feature vector.

**Ember signal.** Monthly data cannot identify hourly generation or orders. For gas, coal and nuclear, a national generation target above the baseline's conditional generation range proposes a lower bid; a target below the range proposes a higher bid. Within-range targets propose zero. The normalized correction is bounded and smoothed with an annual intercept/sine/cosine, using fitting months only. Original nameplate membership weights this national signal into mixed offers; it does not allocate observed generation to bidding zones or create capacity.

| Resource | Change relative to baseline |
| --- | --- |
| Gas and coal/lignite | Calendar correction, optionally plus Ember seasonal signal; total adjustment capped at ±30 EUR/MWh |
| Nuclear | Quarter-strength correction, capped at ±7.5 EUR/MWh; no peaking blocks |
| Wind, solar and other offers | Unchanged |
| Final bids / physical quantities | Offers floored at zero; available MW and all physical constraints unchanged |

This is a transparent effective-bid hypothesis. Price fitting may compensate for incorrect capacity, demand, constraints or outages; it does not uniquely recover actual supply orders. Generation and implied-trade checks therefore accompany price validation. Fixed-hydro areas can remain poorly priced even with better thermal bids.

## 3. Validation across seasons

The earlier Jan–April/May–June/July–December split tested extrapolation from early-year conditions. It did not represent every season in fitting. The new design rotates **whole months**, with one month from each quarter in each role:

| Fold | Fit months | Select months | Test months | Selected variant | Test price MAE: baseline → exploratory |
| --- | --- | --- | --- | --- | ---: |
{fold_table}

Each fold fits its own coefficients, then selects among exactly **unchanged, calendar-only, calendar-plus-Ember** bids. The selection score gives equal weight to control-normalized hourly price MAE, daily-demeaned MAE, monthly generation-interval error and implied-trade interval error, plus a small bid-size penalty. The simplest variant wins numerical ties. First/last 48 hours of fitting and selection months are excluded from price fitting/scoring; monthly Ember checks retain whole months. No test-month price or generation target participates in its fold's fitting or selection.

**Price/mix trade-off:** adding Ember worsened selection-period price MAE relative to calendar-only bids ({selection_tradeoff} EUR/MWh), while improving the joint generation/trade score. That combined score selected it; this is not evidence that Ember alone improves prices. Calendar-only bids were not separately evaluated on the outer test months, so their out-of-fold price accuracy remains unmeasured.

The primary comparison stitches the three disjoint test sets into **all 8,760 hours of 2025**. It is an **out-of-fold composite of three fitted models**, not one deployed annual policy. Ramps exclude boundaries between fold fits. This tests **within-year seasonal interpolation**, using other months that may be later in calendar time. Purging reduces boundary dependence; it does not make months or coupled zones statistically independent. Previously inspected 2025 and reused model architecture prevent an untouched-validation claim. A subsequent year is needed to test genuine forecasting; capacity/weather inputs also assume perfect exogenous information. These scores are not directly comparable to earlier July–December-only headlines.

A separate final reconstruction uses **{methods[ms['refit_variant']]}**, chosen by the mode of inner-selection winners, then refits on all 2025 fitting information. Its MAE is **{refit['equal_zone_mae']:.2f} EUR/MWh**, correlation **{refit['mean_correlation']:.3f}**: **in-sample**, not additional validation. Its witness is retained separately; all primary figures below use out-of-fold results.

## 4. Generation and price results

![All-area generation and price errors, baseline versus out-of-fold seasonal bids]({PREFIX}overview.png)

| Full-2025 metric | Baseline | Exploratory, out of fold |
| --- | ---: | ---: |
| Equal-zone hourly price MAE, EUR/MWh | {aggregate['control']['equal_zone_mae']:.2f} | {new['equal_zone_mae']:.2f} |
| Mean zonal price correlation | {aggregate['control']['mean_correlation']:.3f} | {new['mean_correlation']:.3f} |
| Mean within-day price correlation | {aggregate['control']['mean_demeaned_correlation']:.3f} | {new['mean_demeaned_correlation']:.3f} |
| Daily-demeaned price MAE, EUR/MWh | {aggregate['control']['mean_demeaned_mae']:.2f} | {new['mean_demeaned_mae']:.2f} |
| Median covered-fuel generation volume error, % | {gm['control']:.1f} | {gm['combined']:.1f} |

![Every modeled zone's baseline and out-of-fold price MAE]({PREFIX}zone-mae-grid.png)

Each tile shows baseline → exploratory MAE and signed change; blue improves, red worsens. Gray areas have no observed price: BA, GB, IE-SEM, ME, IT-CALA, FR-COR and XK. [Open the full-size grid]({PREFIX}zone-mae-grid.png). All 48 areas remain visible, including every adverse outcome.

Generation comparison covers **38 reporting areas**, with different fuel/hour coverage. Its error sums absolute fuel-volume differences and divides by observed generation on matched known hours; it can exceed 100% and is not a share percentage-point error or complete-fleet score. **{improved_g}/38** areas improve. Saved equal-bid group dispatch is allocated proportionally to original available MW for illustration. Downloads retain conditional lower/upper allocations; they are not jointly attainable or all possible LP optima. Missing observations stay unknown; pumped-storage output remains separate from primary generation.

Within-day metrics subtract each complete UTC day's mean; the example profiles below instead group by local clock hour with DST.

## 5. Norway, Germany, Spain and France

![National annual generation shares and covered-fuel TWh against Ember]({PREFIX}national-mix.png)

This national Ember cross-check uses all twelve months, separately from hourly ENTSO-E reporting areas. Only fuels with complete monthly references enter all three bars; missing types are excluded, never filled with zero. National Norwegian totals include NO5, which has no comparable hourly zonal generation. Germany's generation excludes Luxembourg while its price is DE-LU. France uses national model membership including modeled Corsica. Geographic, gross/net and taxonomy differences remain material.

| Area | Generation volume error, %: baseline → exploratory | Price MAE, EUR/MWh: baseline → exploratory | Price correlation: baseline → exploratory |
| --- | ---: | ---: | ---: |
{focus_table}

DE-LU generation means Germany national; FR is national. Norway rows use available zonal series. A dash denotes unavailable generation verification.

**Norway:** modeled national hydro is **{cv('NO','Hydro'):.2f} TWh** versus Ember **{rv('NO','Hydro'):.2f} TWh**. NO5 price correlation is **{pr('NO5','correlation'):.3f}**, MAE **{pr('NO5','mae_eur_mwh'):.2f} EUR/MWh**. National volume agreement cannot certify regional water allocation, and new thermal bids cannot reschedule fixed reservoir injections.

**Germany:** gas is **{cv('DE','Gas'):.2f} TWh** versus Ember **{rv('DE','Gas'):.2f}**, coal **{cv('DE','Coal'):.2f}** versus **{rv('DE','Coal'):.2f}**, wind **{cv('DE','Wind'):.2f}** versus **{rv('DE','Wind'):.2f}**. Price correlation **{pr('DE-LU','correlation'):.3f}** must be read alongside those quantity mismatches and demand-scope assumptions.

**Spain:** price MAE is **{pr('ES','mae_eur_mwh'):.2f} EUR/MWh**, bias **{pr('ES','bias_eur_mwh'):+.2f}**, within-day correlation **{pr('ES','demeaned_correlation'):.3f}**. National gas is **{cv('ES','Gas'):.2f} TWh** versus **{rv('ES','Gas'):.2f}** observed; wind **{cv('ES','Wind'):.2f}** versus **{rv('ES','Wind'):.2f}**.

**France:** nuclear is **{cv('FR','Nuclear'):.2f} TWh** versus **{rv('FR','Nuclear'):.2f}**, hydro **{cv('FR','Hydro'):.2f}** versus **{rv('FR','Hydro'):.2f}**. Price MAE is **{pr('FR','mae_eur_mwh'):.2f} EUR/MWh**. Nuclear availability/outages and fixed hydro remain source assumptions, irrespective of fitted price accuracy.

![Winter and summer observed versus out-of-fold mean local-hour prices in NO2, DE-LU, ES and FR]({PREFIX}daily-prices.png)

Profiles separate **winter (Jan/Feb/Dec) and summer (Jun/Jul/Aug)** mean local-hour prices, with DST; solid lines are observed, dashed modeled. They are not an individual day's forecast. Spain's annual mean daily range is **{pr('ES','model_daily_range_mean'):.2f}** versus observed **{pr('ES','observed_daily_range_mean'):.2f} EUR/MWh**; ramp MAE **{pr('ES','ramp_mae'):.2f}**, with **{pr('ES','model_material_negative_hours')} modeled versus {pr('ES','observed_material_negative_hours')} observed negative-price hours**. Seasonal mean profiles can conceal particular-day/tail errors; downloads include them.

## Conclusion and reproducibility

Seasonal calendar bids offer a direct way to vary supply offers daily and annually without a residual-demand predictor. Ember adds a generation-consistency signal, rather than an artificial hourly supply series. The fold selections and out-of-fold results assess that hypothesis under unchanged physical constraints. **Keep the unfitted baseline and the in-sample reconstruction separate from the validation evidence.** Prices alone cannot identify true bids or validate investment effects; fleet/weather quantities, outages, Nordic water/geography and demand scope still require source work.

Independent replay checks calendar/DST features, month exclusion, price/Ember proposals, selection, original component physics, cost/LP duals, stitched test witnesses and separate refit. Maximum physical residual is **{physical_residual:.2g} MW**, duality gap **EUR {duality_gap:.6f}**. The out-of-fold year has **8,760 optimal hours**, emergency supply **{ms['annuals']['combined']['emergency_mwh']:.6f} MWh**. Fresh test clearing totals **{test_seconds:.2f}s**; full preparation/selection/tests/refit command **{ms['end_to_end_seconds']:.2f}s**. Independent report replay additionally verifies generation geography, source observations, allocations and metrics. No empirical acceptance, browser replacement or deployment is implied.

- [All-zone price metrics]({PREFIX}prices-by-zone.csv), [generation coverage/errors]({PREFIX}generation-by-area.csv), [fuel volumes/hourly errors/conditional bounds]({PREFIX}generation-by-fuel.csv), [national Ember comparison]({PREFIX}national-generation.csv).
- [Compact provenance and verification receipt]({PREFIX}summary.json). Bulk hourly/source/replay evidence stays locally cached outside Git.
- [Seasonal bid formulation](tools/seasonal_calendar_bids_2025.py), [independent model replay](tools/audit_seasonal_calendar_bids_2025.py), [report derivation](tools/{producer_file}), [independent report replay](tools/{auditor_file}), [renderer](tools/write_concise_dispatch_report_2025.py).
'''
    ARTICLE.write_text(report)
    assets = {path.name: digest(path) for path in sorted(PUBLIC.iterdir()) if path.name != 'summary.json'}
    receipt = dict(period=s['period'], models=LABELS, generation_reporting_areas=38, observed_price_zones=41,
                   derived_summary_sha256=digest(folder / 'summary.json'), derived_witness_sha256=s['witness_sha256'],
                   report_audit=audit, report_audit_sha256=digest(audit_path),
                   original_model_summary_sha256=s['original_model_summary_sha256'],
                   original_model_audit_sha256=s['original_model_audit_sha256'],
                   model_verification=dict(status=ma['status'], fold_winners=params,
                       variants=ms['design']['variants'], refit_variant=ms['refit_variant'],
                       insample_refit_mae_eur_mwh=refit['equal_zone_mae'],
                       complete_lp_certificates=ma['complete_lp_certificates'],
                       maximum_physical_residual_mw=physical_residual, maximum_duality_gap_eur=duality_gap,
                       producer_file='run_seasonal_calendar_bids_2025.py', producer_sha256=ms['producer_sha256'],
                       helper_file='seasonal_calendar_bids_2025.py', helper_sha256=ms['dependencies']['seasonal_calendar_bids_2025.py'],
                       auditor_file='audit_seasonal_calendar_bids_2025.py', auditor_sha256=ma['auditor_sha256'],
                       annual_clearing_seconds=sum(f['test']['clearing_seconds'] for f in ms['folds'] if not f['test'].get('external')),
                       preparation_seconds=ms['preparation_seconds'], complete_command_seconds=ms['end_to_end_seconds'],
                       optimal_hours=ms['annuals']['combined']['optimal_hours'], emergency_mwh=ms['annuals']['combined']['emergency_mwh']),
                   derived_producer_sha256=s['producer_sha256'], derived_producer_file=producer_file, renderer_sha256=digest(__file__),
                   article_sha256=digest(ARTICLE), assets=assets, limitations=s['limitations'])
    (PUBLIC / 'summary.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(f'Wrote {len(report.split())} words; {len(assets)} compact assets; no market solve')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('folder', type=Path)
    write(p.parse_args().folder)
