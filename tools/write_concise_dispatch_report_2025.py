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
    baseline = json.loads((ROOT / 'config/research-baseline.json').read_text())
    assert baseline['annual_case'] == 'refit'
    assert baseline['summary_sha256'] == digest(model / 'summary.json')
    assert baseline['audit_sha256'] == digest(model / 'verification-v1/audit.json')
    assert baseline['witness']['witness_sha256'] == digest(model / baseline['witness']['witness'])
    direction = json.loads((ROOT / 'config/research-improvement-plan.json').read_text())
    diagnostic_folder = ROOT / direction['diagnosis_folder']
    diagnosis = json.loads((diagnostic_folder / 'diagnosis.json').read_text())
    diagnosis_audit = json.loads((diagnostic_folder / 'diagnosis-audit.json').read_text())
    assert diagnosis_audit['diagnosis_sha256'] == digest(diagnostic_folder / 'diagnosis.json')
    assert diagnosis_audit['auditor_sha256'] == digest(ROOT / 'tools/audit_accepted_baseline_diagnosis_2025.py')
    assert diagnosis['producer_sha256'] == digest(ROOT / 'tools/diagnose_accepted_baseline_2025.py')
    assert diagnosis['baseline_config_sha256'] == digest(ROOT / 'config/research-baseline.json')
    assert diagnosis['equal_zone_mae'] == refit['equal_zone_mae']
    diagnostic_summary = json.loads((diagnostic_folder / 'summary.json').read_text())
    diagnostic_mix_audit = json.loads((diagnostic_folder / 'verification-v1/audit.json').read_text())
    assert diagnostic_mix_audit['summary_sha256'] == digest(diagnostic_folder / 'summary.json') == diagnosis['derivation_summary_sha256']
    assert diagnostic_summary['producer_sha256'] == digest(ROOT / 'tools/prepare_accepted_baseline_mix_2025.py')
    assert diagnostic_mix_audit['auditor_sha256'] == digest(ROOT / 'tools/audit_accepted_baseline_mix_2025.py')
    ranked = sorted([r for r in diagnosis['zones'] if r['known_price_hours']], key=lambda r:-r['mae_eur_mwh'])
    diagnostic_table = '\n'.join(f"| {r['zone']} | {r['mae_eur_mwh']:.2f} | {r['bias_eur_mwh']:+.2f} |" for r in ranked[:7])
    with np.load(diagnostic_folder / 'comparison.npz') as dz:
        mix_rows = []
        for country, fuel in [('DE','Wind'),('DE','Solar'),('DE','Coal'),('DE','Gas'),('FR','Nuclear'),('ES','Wind')]:
            ci=diagnostic_summary['countries'].index(country);fi=diagnostic_summary['ember_fuels'].index(fuel)
            pred=dz['combined_country_point_twh'][ci,fi];actual=dz['ember_reference_twh'][ci,fi]
            mix_rows.append(f"| {country} / {fuel} | {pred:.2f} | {actual:.2f} | {pred-actual:+.2f} |")
        diagnostic_mix_table = '\n'.join(mix_rows)
    daily_section = ''
    daily_receipt = None
    if direction.get('daily_fuel_experiment_folder'):
        dfolder = ROOT / direction['daily_fuel_experiment_folder']
        ds = json.loads((dfolder/'summary.json').read_text())
        da = json.loads((dfolder/'verification-v1/audit.json').read_text())
        assert da['summary_sha256'] == digest(dfolder/'summary.json')
        assert da['auditor_sha256'] == digest(ROOT/'tools/audit_daily_fuel_dispatch_2025.py')
        assert ds['producer_sha256'] == digest(ROOT/'tools/run_daily_fuel_dispatch_2025.py')
        assert len(da['certificates']) == 5 and all(c['hours']==8760 for c in da['certificates'])
        assert all(info['optimal_hours']==8760 and info['emergency_mwh']==0 for info in ds['annuals'].values())
        for name, sha in ds['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
        din = json.loads((ROOT/ds['inputs_folder']/'summary.json').read_text())
        assert din['producer_sha256']==digest(ROOT/'tools/daily_fuel_inputs_2025.py')
        names={'baseline':'Accepted baseline','oil_daily':'Daily oil','gas_daily_ES_PT':'Daily gas: ES/PT','both_daily':'Daily oil + ES/PT gas','both_daily_shape_only':'Both, monthly means preserved'}
        columns={name:{r['zone']:r for r in result['prices']['zones']} for name,result in ds['outcomes'].items()}
        daily_rows=[]
        for area in ds['zones']:
            row={'area':area,'known_hours':columns['baseline'][area]['known_hours']}
            for name in names:
                for metric in ['mae_eur_mwh','bias_eur_mwh','correlation','demeaned_mae']:
                    row[name+'_'+metric]=columns[name][area].get(metric)
            daily_rows.append(row)
        csv_file('daily-fuel-prices-by-zone.csv',daily_rows)
        table=[]
        for name,title in names.items():
            price=ds['outcomes'][name]['prices']
            table.append(f"| {title} | {price['equal_zone_mae']:.3f} | {price['mean_correlation']:.3f} | {columns[name]['ES']['mae_eur_mwh']:.3f} | {columns[name]['PT']['mae_eur_mwh']:.3f} |")
        table='\n'.join(table)
        physical=max(c['original_physical_residual_mw'] for c in da['certificates'])
        gap=max(c['duality_gap_maximum_eur'] for c in da['certificates'])
        daily_section=f'''## Daily oil and gas experiment — 17 October 2026

Fuel inputs change **before clearing**, with the accepted seasonal/calendar/Ember coefficients frozen. All cases solve **8,760 hours**, retain all 41 observed-price areas and use the same demand, source availability, hydro and network. No electricity prices or generation targets are refitted.

| Case | Mean zonal MAE, EUR/MWh | Mean price correlation | Spain MAE | Portugal MAE |
| --- | ---: | ---: | ---: | ---: |
{table}

**Coverage:** oil uses [EIA daily Brent](https://www.eia.gov/dnav/pet/hist_xls/RBRTEd.xls) and daily ECB FX across oil offers. Gas uses MIBGAS PVB in Spain and VTP in Portugal; **other zones still use monthly TTF**. These are not Europe-wide daily gas quotes. The first {din['oil_monthly_fallback_hours']} oil hours and {din['gas_monthly_fallback_hours_per_zone']} gas hours retain monthly inputs because the 2025 daily series have not started. Oil/FX use the last available same-or-earlier quote over nontrading days; gas follows 05:00 UTC winter / 04:00 summer delivery boundaries, including DST. Same-day oil observations are retrospective perfect-information inputs, not an operational forecast.

Monthly country/fuel generation-interval mismatch (the existing normalized score, lower is better) changes **{ds['outcomes']['baseline']['quantity_errors']['generation']:.6f} → {ds['outcomes']['both_daily']['quantity_errors']['generation']:.6f}** for the combined case. This is not a whole-fleet percentage error.

The direct cases change both price levels and daily shape. The final control preserves each original monthly fuel mean while using daily variation, separating those effects without electricity-price fitting. Retained assumptions include 1.7 MWh thermal/barrel, the existing gas heating-value/efficiency equivalence, and fixed carbon at EUR80/t. Brent is a crude-oil proxy, not delivered generating fuel; the plant heating-value basis remains a limitation.

All four new annual cases are optimal with zero emergency supply. Independent source-cell, cost, original-network/physics, primal/dual, price and monthly generation/trade replay passes: maximum physical residual **{physical:.2g} MW**, duality gap **EUR {gap:.6f}**. [Download every zone's results]({PREFIX}daily-fuel-prices-by-zone.csv). These controlled trials do not replace the accepted baseline.

'''
        daily_receipt=dict(summary_sha256=digest(dfolder/'summary.json'),audit=da,producer_sha256=ds['producer_sha256'],inputs_producer_sha256=din['producer_sha256'],source_coverage=da['source_replay'],
                           outcomes={name:dict(equal_zone_mae=v['prices']['equal_zone_mae'],mean_correlation=v['prices']['mean_correlation'],quantity_errors=v['quantity_errors']) for name,v in ds['outcomes'].items()},
                           annual_clearing_seconds={name:info['clearing_seconds'] for name,info in ds['annuals'].items() if not info.get('external')},preparation_seconds=ds['preparation_seconds'],finalization_command_seconds=ds['end_to_end_seconds'],producer_role=ds['producer_role'])
    nuclear_section = ''
    nuclear_receipt = None
    nuclear_study = None
    if direction.get('nuclear_availability_experiment_folder'):
        nfolder=ROOT/direction['nuclear_availability_experiment_folder']
        ns=json.loads((nfolder/'summary.json').read_text());na=json.loads((nfolder/'verification-v1/audit.json').read_text())
        assert na['summary_sha256']==digest(nfolder/'summary.json') and len(na['certificates'])==4
        assert ns['producer_sha256']==digest(ROOT/'tools/run_nuclear_availability_2025.py')
        assert na['auditor_sha256']==digest(ROOT/'tools/audit_nuclear_availability_2025.py')
        for name,sha in ns['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
        for name,sha in ns['source_hashes'].items():assert digest(ROOT/name)==sha
        assert all(c['hours']==8760 and c['original_component_residual_mw']<=1e-4 and c['source_group_bound_residual_mw']<=1e-4 and c['duality_gap_maximum_eur']<.05 for c in na['certificates'])
        nt={case:{r['zone']:r for r in v['prices']['zones']} for case,v in ns['outcomes'].items()}
        nlabels={'baseline':'Accepted baseline','annual_mean':'RTE annual mean','daily_utc':'RTE daily / UTC dates','daily_paris':'RTE daily / Paris dates'}
        rows=[]
        for zone in ns['zones']:
            row=dict(area=zone,known_hours=nt['baseline'][zone]['known_hours'])
            for case in nlabels:
                for metric in ['mae_eur_mwh','bias_eur_mwh','correlation','demeaned_mae','demeaned_correlation']:
                    row[case+'_'+metric]=nt[case][zone].get(metric)
            rows.append(row)
        csv_file('nuclear-availability-prices-by-zone.csv',rows)
        rows=[]
        for case in nlabels:
            for month in range(1,13):
                rows.append(dict(case=case,month=month,source_fr_nuclear_available_twh=ns['profiles'][case]['monthly_available_twh'][month-1],
                                 source_fr_nuclear_dispatch_illustration_twh=ns['profiles'][case]['monthly_dispatch_twh'][month-1]))
        csv_file('nuclear-availability-by-month.csv',rows)
        ntable='\n'.join(f"| {label} | {ns['outcomes'][case]['prices']['equal_zone_mae']:.3f} | {nt[case]['FR']['mae_eur_mwh']:.3f} | {ns['outcomes'][case]['prices']['mean_demeaned_correlation']:.3f} | {ns['profiles'][case]['nuclear_dispatch_twh']:.2f} | {ns['outcomes'][case]['quantity_errors']['generation']:.4f} |" for case,label in nlabels.items())
        nuclear_section=f'''## Dated nuclear availability — controlled source test

The accepted model applies a flat 2024 national nuclear energy-availability factor throughout 2025. For its French source fleet this permits **{ns['profiles']['baseline']['mean_mw']/1000:.2f} GW** at every hour. [RTE's daily availability series](https://analysesetdonnees.rte-france.com/production/nucleaire), derived from REMIT reporting, provides all **365 dates of 2025**: reported available power ranges **{ns['profiles']['daily_utc']['minimum_mw']/1000:.2f}–{ns['profiles']['daily_utc']['maximum_mw']/1000:.2f} GW**, averaging **{ns['profiles']['daily_utc']['mean_mw']/1000:.2f} GW**. These are available supply, not observed generation.

Three finite controls replace only French **source-country** nuclear availability: a constant RTE annual mean, daily values mapped to UTC dates, and daily values mapped to Paris dates. The mean control separates level from daily shape approximately. The source dates carry no timezone; both mappings are disclosed assumptions, not a certified correction. Paris mapping uses the adjacent **1 January 2026** boundary record and preserves 23/25-hour local days. Each daily value is repeated within its day: **a daily national proxy is not a verified hourly maximum or unit-level outage schedule**. The data are revised historical observations, not evidence of what bidders knew in advance. [EDF's annual Kd](https://opendata.edf.fr/datasets/disponibilite-du-parc-nucleaire-d-edf-sa-depuis-2002) describes technical availability with different exclusions; fleet/definition differences must be reconciled before treating these sources as interchangeable. No rescaling to Kd or observed generation is performed.

National available MW are allocated by retained source-fleet nameplate shares, within original nominal limits. Source membership, geographic placement and static GSKs stay distinct; plant outage geography is unresolved. All renewable inputs, fuel anchors, accepted seasonal/Ember bids, demand, fixed hydro and grid constraints stay unchanged. This test does **not** combine the preceding renewable changes or refit bids.

| Full-2025 case | European price MAE | FR price MAE | Within-day correlation, Europe | FR-source nuclear dispatch, TWh | Generation-interval mismatch |
| --- | ---: | ---: | ---: | ---: | ---: |
{ntable}

Price MAEs are EUR/MWh, equal-zone Europe includes all 41 complete observed-price areas, and all four witnesses retain **8,760 optimal hours with zero emergency supply**. National-source dispatch is a proportional allocation illustration, with conditional bounds in the receipt; national Ember/geographic reporting scope remains separate. The normalized monthly generation score is not total-fleet percentage error. [Every zone's price metrics]({PREFIX}nuclear-availability-prices-by-zone.csv) and [monthly available/dispatch quantities]({PREFIX}nuclear-availability-by-month.csv) retain the full comparison.

**Result:** daily availability raises French-source nuclear dispatch from 345.40 to about 349.2 TWh, closer to the 371.69 TWh national Ember reference but still not a scope-reconciled match. France's price correlation rises from 0.802 to about 0.817, while its MAE worsens from 23.83 to about 24.01 EUR/MWh. Europe-wide MAE only changes from 28.964 to about 28.95. The annual-mean control lowers price MAE further but worsens the nuclear generation total. Neither mapping nor mean-versus-shape controls deliver a clear joint improvement, and the <10 target remains distant. This French daily proxy does not rule out the value of better hourly/unit outage data elsewhere.

The grid below adds the three nuclear controls against the accepted baseline, separately from the wind/PV experiment's matched control. Independent replay checks source records/calendar, national MW allocation, original network physics, LP duals and annual price/mix/trade metrics. No baseline promotion or validated investment effect follows from this test.

'''
        nuclear_study=(ns,nt)
        nuclear_receipt=dict(summary_sha256=digest(nfolder/'summary.json'),audit=na,producer_sha256=ns['producer_sha256'],helper_sha256=ns['dependencies']['nuclear_availability_2025.py'],
                             source=json.loads((ROOT/ns['source_folder']/'receipt.json').read_text()),profiles=ns['profiles'],
                             outcomes={case:dict(equal_zone_mae=v['prices']['equal_zone_mae'],within_day_correlation=v['prices']['mean_demeaned_correlation'],quantity_errors=v['quantity_errors']) for case,v in ns['outcomes'].items()},
                             annuals=ns['annuals'],preparation_seconds=ns['preparation_seconds'],end_to_end_seconds=ns['end_to_end_seconds'])
    renewable_section = ''
    renewable_receipt = None
    if direction.get('renewable_source_experiment_folder'):
        rfolder=ROOT/direction['renewable_source_experiment_folder']
        rs=json.loads((rfolder/'summary.json').read_text());ra=json.loads((rfolder/'verification-v1/audit.json').read_text())
        assert ra['summary_sha256']==digest(rfolder/'summary.json')
        assert rs['producer_sha256']==digest(ROOT/'tools/run_renewable_source_bids_2025.py')
        assert ra['auditor_sha256']==digest(ROOT/'tools/audit_renewable_source_bids_2025.py')
        assert len(ra['certificates'])==7
        for name,sha in rs['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
        assert all(c['hours']==8760 and c['original_component_residual_mw']<=1e-4 and c['source_group_bound_residual_mw']<=1e-4 and c['duality_gap_maximum_eur']<.05 for c in ra['certificates'])
        names={'control':'Matched control','wind_subtypes':'IRENA wind subtypes','solar_bos':'PV system-loss sensitivity','availability_combined':'Both input changes','solar_bid':'Both inputs + PV bids','wind_bid':'Both inputs + wind bids','both_bids':'Both inputs + both bids'}
        rp={case:{r['zone']:r for r in v['prices']['zones']} for case,v in rs['outcomes'].items()}
        price_rows=[];deltas=np.full((len(rs['zones']),len(names)),np.nan)
        for j,zone in enumerate(rs['zones']):
            row=dict(area=zone,known_hours=rp['control'][zone]['known_hours'])
            for k,case in enumerate(names):
                for metric in ['mae_eur_mwh','bias_eur_mwh','correlation','demeaned_mae','demeaned_correlation']:
                    row[case+'_'+metric]=rp[case][zone].get(metric)
                if row['known_hours']:deltas[j,k]=rp[case][zone]['mae_eur_mwh']-rp['control'][zone]['mae_eur_mwh']
            price_rows.append(row)
        csv_file('renewable-source-prices-by-zone.csv',price_rows)
        cap_rows=[]
        for r in rs['capacity_inventory']:
            row={k:v for k,v in r.items() if k!='irena_endpoints_mw'}
            if r.get('irena_endpoints_mw'):
                for family,values in zip(['total_wind','onshore','offshore'],r['irena_endpoints_mw']):
                    for year,value in zip([2024,2025],values):row[f'irena_{family}_{year}_mw']=value
            cap_rows.append(row)
        csv_file('renewable-capacity-audit.csv',cap_rows)
        columns=['Control','Wind inputs','PV losses','Both inputs','+ PV bid','+ wind bid','+ both bids']
        if nuclear_study:
            ns,nt=nuclear_study;assert ns['zones']==rs['zones']
            extra=np.full((len(rs['zones']),3),np.nan)
            for j,zone in enumerate(rs['zones']):
                if nt['baseline'][zone]['known_hours']:
                    for k,case in enumerate(['annual_mean','daily_utc','daily_paris']):extra[j,k]=nt[case][zone]['mae_eur_mwh']-nt['baseline'][zone]['mae_eur_mwh']
            deltas=np.column_stack([deltas,extra]);columns+=['FR nuc mean','FR nuc UTC','FR nuc Paris']
        limit=max(.5,float(np.nanquantile(abs(deltas),.95)));fig,ax=plt.subplots(figsize=(14,15))
        cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('#eceff2')
        im=ax.imshow(np.ma.masked_invalid(deltas),cmap=cmap,vmin=-limit,vmax=limit,aspect='auto')
        ax.set_xticks(range(len(columns)),columns,rotation=30,ha='right')
        ax.set_yticks(range(len(rs['zones'])),rs['zones']);ax.set_title('2025 hourly price MAE change versus each experiment’s unchanged control\nEUR/MWh · blue improves, red worsens · gray has no observed prices')
        for j in range(len(rs['zones'])):
            for k in range(len(columns)):
                if np.isfinite(deltas[j,k]):ax.text(k,j,f'{deltas[j,k]:+.2f}',ha='center',va='center',fontsize=7,color='white' if abs(deltas[j,k])>limit*.65 else '#182a3b')
        fig.colorbar(im,ax=ax,shrink=.65,label=f'Change in MAE (colors clipped at ±{limit:.2f}; cell numbers show actual change)')
        fig.tight_layout();save(fig,'zone-mae-grid.png')
        table='\n'.join(f"| {label} | {rs['outcomes'][case]['prices']['equal_zone_mae']:.3f} | {rs['outcomes'][case]['prices']['mean_demeaned_correlation']:.3f} | {rs['outcomes'][case]['quantity_errors']['generation']:.4f} |" for case,label in names.items())
        changed=sum(r['status']=='onshore_offshore_capacity_trajectories_reconciled' for r in rs['capacity_inventory'])
        renewable_section=f'''## Wind/solar inputs and resource bids — 19 October 2026

**Wind correction:** the accepted baseline scales total national wind but retains the old fleet's onshore/offshore shares. The new case applies separate [IRENA 2026 publication](https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2026/Mar/IRENA_DAT_RE_capacity_statistics_2026.pdf) end-2024/end-2025 subtype trajectories in **{changed} source countries**, preserving original within-subtype weather/location shares. Missing or inconsistent parent/subtype records retain original wind, with status in the [capacity audit]({PREFIX}renewable-capacity-audit.csv). Parent and child capacities are never added. For example, the old Dutch split assigned about 7.3 GW offshore at the start of 2025 versus IRENA 4.75 GW. Source-country identity and geographic/GSK allocation proxies remain distinct; original static GSKs stay fixed to isolate availability effects.

**Solar sensitivity:** the original CSi panel model already includes 10% inverter losses. [PVGIS]({rs['pvgis_url']}) uses 14% as a generic overall system-loss default. Replacing the 10% factor with 14% multiplies available PV by **0.86/0.90**, a 4.44% reduction; applying another 14% would double-count inverter losses. This is a declared generic sensitivity, **not a verified country-specific fleet correction**. Original temperature, irradiance, south-facing 35° geometry, capacity trajectory and chronology remain; observed generation never replaces availability.

**Resource bids:** after both input changes, the lower half of available PV, wind or both is offered at **−10 EUR/MWh**, with the upper half at 0. These are simple synthetic bid controls, not measured subsidy entitlements or forced generation. Accepted gas/coal/nuclear calendar/Ember coefficients, demand, fuel, hydro and grid stay fixed; no refit. An unmodified matched control is necessary because separating formerly equal-price wind/solar columns can change duals and illustrative allocations. Its price MAE is {rs['outcomes']['control']['prices']['equal_zone_mae']:.6f}, versus the retained accepted baseline {rs['accepted_mae']:.6f}.

| Full-year case | Price MAE, EUR/MWh | Within-day correlation | Generation-interval mismatch |
| --- | ---: | ---: | ---: |
{table}

All seven cases clear **8,760 optimal hours with zero emergency supply**, retaining all 41 observed-price areas. Generation mismatch is the existing normalized monthly country/fuel interval score, not total-fleet percentage error; conditional allocation intervals do not span every possible equal-cost optimum. No case is promoted automatically. [All-zone hourly-price metrics]({PREFIX}renewable-source-prices-by-zone.csv) include every modeled area, with unknown observations blank.

![Every modeled zone and every source/bid control: price MAE changes]({PREFIX}zone-mae-grid.png)

**Conclusion:** both input changes reduce Europe-wide MAE only from 28.964 to 28.912 EUR/MWh, far from the <10 target. Germany improves from 21.57 to 20.83, while Spain worsens from 24.07 to 24.25. Wind subtype correction improves the quantity score but slightly worsens price MAE on its own; the generic PV loss sensitivity has the lowest price MAE. None of the negative renewable bid controls improves on the combined-input case. These are modest diagnostics, not evidence for adopting a universal negative bid or a measured PV derating.

Independent source-capacity, availability, component-physics, LP dual, price and monthly generation/trade replay verifies all seven cases. Wind/PV source profiles still represent generic turbines, idealized panel geometry and potential-based spatial layouts; subtype capacity corrections do not establish actual site output or resolve curtailment, outages and reporting scope.

'''
        renewable_receipt=dict(summary_sha256=digest(rfolder/'summary.json'),audit=ra,producer_sha256=rs['producer_sha256'],helper_sha256=rs['dependencies']['renewable_source_bids_2025.py'],
                               outcomes={case:dict(equal_zone_mae=v['prices']['equal_zone_mae'],within_day_correlation=v['prices']['mean_demeaned_correlation'],quantity_errors=v['quantity_errors']) for case,v in rs['outcomes'].items()},
                               annuals=rs['annuals'],preparation_seconds=rs['preparation_seconds'],end_to_end_seconds=rs['end_to_end_seconds'])
        # Keep the previous fuel pilot compact rather than accumulating old narratives.
        daily_section=f'''## Previous daily-fuel check

Daily EIA Brent/ECB oil quotes and MIBGAS gas indices in ES/PT changed Europe-wide MAE from 28.964 to 28.950 EUR/MWh with coefficients frozen. Gas elsewhere remained monthly TTF; this was not a Europe-wide daily-gas test. Original heating-basis assumptions and explicit first-day fallbacks remained. The source/physics/dual replay is retained; see the [all-zone fuel comparison]({PREFIX}daily-fuel-prices-by-zone.csv). The accepted baseline was unchanged.

'''
    report = f'''# European dispatch: accepted seasonal-bid baseline

## Accepted baseline: single full-year reconstruction

The seasonal/time-of-day **calendar + Ember** supply-bid model is now the accepted research baseline. Its single annual `refit` solves all **8,760 hours of 2025**, with mean zonal MAE **{refit['equal_zone_mae']:.2f} EUR/MWh**, **{baseline['mae_reduction_percent']:.1f}% lower** than the previous unfitted control ({baseline['previous_mae_eur_mwh']:.2f}). Mean price correlation is **{refit['mean_correlation']:.3f}** and within-day correlation **{refit['mean_demeaned_correlation']:.3f}**. Annual clearing took **{baseline['witness']['clearing_seconds']:.2f}s**, excluding preparation, fitting and audits; all hours were optimal with zero emergency supply.

These are **2025 in-sample reconstruction scores**: 2025 prices informed bids. Generation agreement and independently replayed physics are complementary checks, not statistical cross-validation. The model changes offers before physical clearing; it never replaces cleared prices afterward. Fixed hydro and all physical constraints remain unchanged. This acceptance does not replace the browser scenario engine or validate investment effects.

## Research target and accepted-baseline diagnosis

The target is **below 10 EUR/MWh equal-zone MAE for all 8,760 hours of 2025**, across all 41 complete observed-price areas, with per-zone results retained. Seven modeled areas still lack complete observed prices. Reaching 10 from the accepted baseline requires a further **{diagnosis['remaining_reduction_percent']:.1f}% reduction**; that improvement is a research goal, not a demonstrated outcome.

| Largest price errors | Annual MAE, EUR/MWh | Signed bias, EUR/MWh |
| --- | ---: | ---: |
{diagnostic_table}

Both daily levels and intraday movements matter. Mean daily-level error is **{diagnosis['mean_daily_level_error_mae']:.2f} EUR/MWh**; after removing each day's mean error, within-day error remains **{diagnosis['mean_within_day_error_mae']:.2f} EUR/MWh**. These are descriptive diagnostics calculated with observed prices; their MAEs do not add and they are not usable forecast corrections. Daily fuel changes alone cannot correct all hourly shape errors.

The following national quantities come from the **accepted single annual refit**, independently re-aggregated and checked against twelve-month Ember references. Coal combines hard coal and lignite. Model points illustrate saved-group allocations; conditional bounds and national/technology scope differences remain relevant.

| Country / resource | Model TWh | Ember TWh | Difference TWh |
| --- | ---: | ---: | ---: |
{diagnostic_mix_table}

**Next controlled improvements:** first reconcile country-specific wind/solar capacity and weather conversion, biomass/coal classification and reporting coverage; audit dated nuclear/thermal outages. Compare price and mix changes together. Do not scale weather availability to observed generation. Then test source-backed daily thermal costs with current bid coefficients fixed, followed by a separately labelled refit if warranted. Explore resource-specific operating bids and negative-price behaviour after those source checks; a uniform negative-bid change would not explain the excess negative prices already present in some Norwegian zones.

**Fuel precision today:** gas uses monthly World Bank TTF benchmarks; oil uses monthly Brent, both converted using monthly mean reciprocal ECB FX. Carbon is fixed at **80 EUR/t** and coal/lignite retain technology-cost assumptions. These are not daily fuel quotes. Resource bids use fuel/efficiency + carbon × emissions/efficiency + variable O&M, before the bounded seasonal correction. Gas needs gas-hub data rather than oil as a proxy.

[Ember's daily fuel-cost methodology](https://ember-energy.org/data/european-electricity-prices-and-costs/) identifies national gas hubs, API2 coal and EU/UK carbon contracts, but its embedded fuel chart explicitly restricts downloads because of licensing; no series has been adopted. [MIBGAS's 2025 archive](https://www.mibgas.es/en/file-access?path=AGNO_2025/XLS) now has **365 source-replayed delivery days** of Spanish PVB and Portuguese VTP last/average day-ahead indices. These are source-computed indices, including provider estimates in illiquid periods; they are not a Europe-wide TTF substitute. The daily trial below uses them in ES/PT; the accepted baseline remains unchanged. [EIA daily Brent](https://www.eia.gov/dnav/pet/hist_xls/RBRTEd.xls) is an oil-proxy candidate. The daily trial below documents reconciled delivery dates and nontrading-day treatment; broader gas-hub coverage, heating-value/efficiency and delivered-fuel assumptions remain open.

{nuclear_section}{renewable_section}{daily_section}## Secondary development evidence

The sections and figures below retain the **previous unfitted baseline versus out-of-fold seasonal-model comparison** as secondary development evidence. Their “baseline” labels mean the previous control; their “exploratory” results combine three fits and are **not the accepted single annual refit**. Do not mix those generation/price results with the annual-refit headline.



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

Seasonal calendar bids offer a direct way to vary supply offers daily and annually without a residual-demand predictor. Ember adds a generation-consistency signal, rather than an artificial hourly supply series. The fold selections and out-of-fold results assess that hypothesis under unchanged physical constraints. **The annual refit is the accepted research baseline; retain the unfitted control and out-of-fold evidence separately.** Prices alone cannot identify true bids or validate investment effects; fleet/weather quantities, outages, Nordic water/geography and demand scope still require source work.

Independent replay checks calendar/DST features, month exclusion, price/Ember proposals, selection, original component physics, cost/LP duals, stitched test witnesses and separate refit. Maximum physical residual is **{physical_residual:.2g} MW**, duality gap **EUR {duality_gap:.6f}**. The out-of-fold year has **8,760 optimal hours**, emergency supply **{ms['annuals']['combined']['emergency_mwh']:.6f} MWh**. Fresh test clearing totals **{test_seconds:.2f}s**; full preparation/selection/tests/refit command **{ms['end_to_end_seconds']:.2f}s**. Independent report replay additionally verifies generation geography, source observations, allocations and metrics. Research-baseline promotion is user-authorized; browser replacement, investment acceptance and deployment are separate.

- [All-zone price metrics]({PREFIX}prices-by-zone.csv), [generation coverage/errors]({PREFIX}generation-by-area.csv), [fuel volumes/hourly errors/conditional bounds]({PREFIX}generation-by-fuel.csv), [national Ember comparison]({PREFIX}national-generation.csv).
- [Compact provenance and verification receipt]({PREFIX}summary.json). Bulk hourly/source/replay evidence stays locally cached outside Git.
- [Seasonal bid formulation](tools/seasonal_calendar_bids_2025.py), [independent model replay](tools/audit_seasonal_calendar_bids_2025.py), [report derivation](tools/{producer_file}), [independent report replay](tools/{auditor_file}), [renderer](tools/write_concise_dispatch_report_2025.py).
'''
    if renewable_receipt:
        legacy_start=report.index("![Every modeled zone's baseline and out-of-fold price MAE]")
        legacy_end=report.index('Generation comparison covers',legacy_start)
        report=report[:legacy_start]+"Historical out-of-fold zone metrics remain in the downloads; the all-zone grid above shows the current source/bid experiment.\n\n"+report[legacy_end:]
    ARTICLE.write_text(report)
    assets = {path.name: digest(path) for path in sorted(PUBLIC.iterdir()) if path.name != 'summary.json'}
    receipt = dict(nuclear_availability_evaluation=nuclear_receipt, renewable_source_evaluation=renewable_receipt, daily_fuel_evaluation=daily_receipt, research_direction=dict(plan_sha256=digest(ROOT/'config/research-improvement-plan.json'),
                       diagnosis_sha256=digest(diagnostic_folder/'diagnosis.json'),audit=diagnosis_audit,
                       producer_sha256=diagnosis['producer_sha256'],mix_producer_sha256=diagnostic_summary['producer_sha256'],
                       mix_auditor_sha256=diagnostic_mix_audit['auditor_sha256'],mix_audit=diagnostic_mix_audit,
                       target=direction['target'],equal_zone_mae=diagnosis['equal_zone_mae'],
                       mean_daily_level_error_mae=diagnosis['mean_daily_level_error_mae'],
                       mean_within_day_error_mae=diagnosis['mean_within_day_error_mae']), accepted_baseline=baseline, period=s['period'], models=LABELS, generation_reporting_areas=38, observed_price_zones=41,
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
