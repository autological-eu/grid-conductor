"""Compact held-out price/mix report; no fitting or public model replacement."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sigmoid_month_pairs_2025 import ROOT, OUT, load, split, FAMILIES, EMBER, digest, write

NAME = 'sigmoid-month-pairs-2025'


def export(path, rows):
    with path.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(rows)


def report():
    sealed, data, _ = load(); summary = json.loads((OUT/'summary.json').read_text()); audit = json.loads((OUT/'audit.json').read_text())
    assert audit['status'] == 'all_six_folds_17520_retained_LP_hours_and_target_isolation_passed'
    assert audit['summary_sha256'] == digest(OUT/'summary.json') and audit['auditor_sha256'] == digest(ROOT/'tools/audit_sigmoid_month_pairs_2025.py')
    hours = []; price = {'control':[], 'learned':[], 'accepted':[]}; gen = {k:[] for k in price}; monthly_rows = []; fold_rows = []; exports = []; parameters = []
    for row in summary['pairs']:
        _, hh = split(row['train_month'], row['test_month']); hours.extend(hh)
        proposal_path = ROOT/row['proposal']['path']; assert digest(proposal_path) == row['proposal']['sha256']; proposal = json.loads(proposal_path.read_text())
        for (country, family), theta, support in zip(sealed['parameters'], proposal['theta'], proposal['support'], strict=True):
            parameters.append(dict(train_month=row['train_month'], test_month=row['test_month'], country=country, family=family,
                 midpoint_intercept_eur_mwh=theta[0], daily_sin=theta[1], daily_cos=theta[2], twice_daily_sin=theta[3], twice_daily_cos=theta[4],
                 spread_eur_mwh=float(np.exp(theta[5])), hourly_training_generation_targets=support['hourly_targets'],
                 monthly_training_generation_target=support['monthly_target'], inverse_converged=support['converged']))
        for case, role in [('control', 'test_control'), ('learned', 'test_selected')]:
            record = row['witnesses'][role]; assert digest(ROOT/record['path']) == record['sha256']
            with np.load(ROOT/record['path']) as z:
                price[case].append(z['row_duals'][:, :sealed['nz']]); gen[case].append(z['generation'])
        price['accepted'].append(data['accepted_prices'][hh]); gen['accepted'].append(data['accepted_generation'][hh])
        for case, key in [('control', 'test_control'), ('learned', 'test_selected'), ('accepted', 'accepted_insample_test')]:
            fold_rows.append(dict(train_month=row['train_month'], test_month=row['test_month'], case=case, hours=len(hh), **row[key]))
            gg = gen[case][-1]
            for ci, country in enumerate(sealed['countries']):
                for fi, family in enumerate(FAMILIES):
                    ids = [sealed['technologies'].index(t) for t in EMBER[family]]
                    model = float(gg[:, ci][:, ids].sum()/1e6); obs = data['ember'][row['test_month']-1, ci, fi]
                    monthly_rows.append(dict(train_month=row['train_month'], test_month=row['test_month'], case=case, country=country, family=family,
                         model_twh=model, observed_twh=float(obs) if np.isfinite(obs) else None, absolute_error_twh=abs(model-float(obs)) if np.isfinite(obs) else None,
                         normalized_error=abs(model-float(obs))/max(float(obs), .25) if np.isfinite(obs) else None))
    hours = np.array(hours); price = {k:np.concatenate(v) for k,v in price.items()}; gen = {k:np.concatenate(v) for k,v in gen.items()}
    assert len(hours) == 4344 and np.all(np.diff(hours) > 0)
    known = np.isfinite(data['observed_prices']).all(axis=0); target = data['observed_prices'][hours]; zones = []; hourly_rows = []; overall = {}
    for case in price:
        rr = [r for r in monthly_rows if r['case'] == case and r['observed_twh'] is not None]
        share_errors = []; share_country_months = []
        for country in sealed['countries']:
            for month in [2,4,6,8,10,12]:
                cells = [r for r in rr if r['country'] == country and r['test_month'] == month]
                if len(cells) == len(FAMILIES):
                    a = np.array([r['model_twh'] for r in cells]); b = np.array([r['observed_twh'] for r in cells])
                    if a.sum() > 0 and b.sum() > 0:
                        share_errors.extend(100*abs(a/a.sum()-b/b.sum()))
                        share_country_months.append((country, month))
        overall[case] = dict(price_mae=float(abs(price[case][:, known]-target[:, known]).mean()),
            generation_mae_twh=float(np.mean([r['absolute_error_twh'] for r in rr])), generation_normalized_mae=float(np.mean([r['normalized_error'] for r in rr])),
            generation_share_mae_percentage_points=float(np.mean(share_errors)), generation_share_cells=len(share_errors),
            generation_share_country_months=len(share_country_months), generation_share_countries=sorted({v[0] for v in share_country_months}), generation_cells=len(rr))
        for j, zone in enumerate(sealed['zones']):
            mask = np.isfinite(target[:, j]); corr = None
            if mask.sum() > 1 and target[mask, j].std() > 1e-10 and price[case][mask, j].std() > 1e-10:
                corr = float(np.corrcoef(price[case][mask, j], target[mask, j])[0, 1])
            zones.append(dict(case=case, zone=zone, hours=int(mask.sum()), mae_eur_mwh=float(abs(price[case][mask, j]-target[mask, j]).mean()) if mask.any() else None,
                              bias_eur_mwh=float((price[case][mask, j]-target[mask, j]).mean()) if mask.any() else None, correlation=corr))
        for ci, country in enumerate(sealed['countries']):
            for fi, tech in enumerate(sealed['technologies']):
                obs = data['observed_generation'][hours, ci, fi]; mask = np.isfinite(obs)
                if mask.any():
                    hourly_rows.append(dict(case=case, country=country, technology=tech, matched_hours=int(mask.sum()), mae_mw=float(abs(gen[case][mask, ci, fi]-obs[mask]).mean()),
                                            model_twh=float(gen[case][mask, ci, fi].sum()/1e6), observed_twh=float(obs[mask].sum()/1e6)))
    for suffix, rows in [('folds', fold_rows), ('zones', zones), ('generation', monthly_rows), ('hourly-generation', hourly_rows), ('parameters', parameters)]:
        path = ROOT/'research'/f'{NAME}-{suffix}.csv'; export(path, rows); exports.append(path)
    labels = {'control':'Unfitted sigmoid control', 'learned':'Odd-month learned curves', 'accepted':'Accepted baseline (in-sample)'}
    colors = {'control':'#929292', 'learned':'#287e91', 'accepted':'#9a6a99'}
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for case in price:
        rows = [r for r in fold_rows if r['case'] == case]
        axes[0,0].plot([r['test_month'] for r in rows], [r['price_mae'] for r in rows], marker='o', color=colors[case], label=labels[case])
        axes[0,1].plot([r['test_month'] for r in rows], [r['generation_normalized_mae'] for r in rows], marker='o', color=colors[case])
    axes[0,0].set(title='Held-out hourly price error · 41 complete SDAC zones', ylabel='MAE, €/MWh', xlabel='Test month'); axes[0,0].legend(fontsize=8)
    axes[0,1].set(title='Held-out monthly generation mix error', ylabel='Mean |model − source| / max(source, 0.25 TWh)', xlabel='Test month')
    for case, offset in [('control', -.25), ('learned', 0), ('accepted', .25)]:
        vals = []
        for family in FAMILIES:
            rr = [r for r in monthly_rows if r['case'] == case and r['family'] == family and r['absolute_error_twh'] is not None]
            vals.append(np.mean([r['absolute_error_twh'] for r in rr]))
        axes[1,0].bar(np.arange(len(FAMILIES))+offset, vals, width=.24, color=colors[case], label=labels[case])
    axes[1,0].set_xticks(range(len(FAMILIES)), FAMILIES, rotation=35, ha='right', fontsize=8); axes[1,0].set(title='Generation by source family · six held-out months', ylabel='Monthly country-cell MAE, TWh')
    rr = [r for r in zones if r['case'] == 'learned' and r['hours'] == 4344]; rr.sort(key=lambda r:r['mae_eur_mwh'])
    delta = [r['mae_eur_mwh']-next(s['mae_eur_mwh'] for s in zones if s['case'] == 'control' and s['zone'] == r['zone']) for r in rr]
    axes[1,1].bar(range(len(rr)), delta, color=['#287e91' if v < 0 else '#bd7542' for v in delta]); axes[1,1].set_xticks(range(len(rr)), [r['zone'] for r in rr], rotation=90, fontsize=7)
    axes[1,1].axhline(0, color='black', lw=.7); axes[1,1].set(title='Learning effect by zone · negative is better', ylabel='Price MAE change vs unfitted control, €/MWh')
    for ax in axes.ravel(): ax.grid(axis='y', alpha=.2)
    fig.suptitle('Six independent odd-month fits → next-even-month tests · 4,344 held-out hours'); fig.tight_layout(rect=(0,0,1,.96))
    path = ROOT/'research/assets'/f'{NAME}.png'; fig.savefig(path, dpi=145); plt.close(fig); exports.append(path)
    fig, axes = plt.subplots(2,2,figsize=(14,8)); times = np.arange('2025-01-01T00','2026-01-01T00',dtype='datetime64[h]')[hours]
    example = (times >= np.datetime64('2025-06-01')) & (times < np.datetime64('2025-06-08'))
    for ax, zone in zip(axes.ravel(), ['NO2','DE-LU','ES','FR'], strict=True):
        j = sealed['zones'].index(zone)
        ax.plot(times[example], target[example,j], color='black', lw=1, label='Observed ENTSO-E')
        for case in ['control','learned']:
            ax.plot(times[example], price[case][example,j], color=colors[case], lw=.8, alpha=.9, label=labels[case])
        ax.set_title(zone+' · June 1–7, fitted on May'); ax.set_ylabel('€/MWh'); ax.tick_params(axis='x', rotation=20); ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8); fig.tight_layout(); path=ROOT/'research/assets'/f'{NAME}-examples.png'; fig.savefig(path,dpi=145);plt.close(fig);exports.append(path)
    fig, axes = plt.subplots(1,2,figsize=(14,8)); names = sorted([sealed['zones'][j] for j in np.flatnonzero(known)])
    for ax, case in zip(axes, ['control','learned'], strict=True):
        grid = np.full((9,5), np.nan)
        for i, zone in enumerate(names):grid.flat[i] = next(r['mae_eur_mwh'] for r in zones if r['zone']==zone and r['case']==case)
        image=ax.imshow(grid,cmap='YlOrRd',vmin=0,vmax=max(r['mae_eur_mwh'] for r in zones if r['case'] in ['control','learned'] and r['mae_eur_mwh'] is not None));ax.set_xticks([]);ax.set_yticks([]);ax.set_title(labels[case])
        for i,zone in enumerate(names):ax.text(i%5,i//5,f'{zone}\n{grid.flat[i]:.1f}',ha='center',va='center',fontsize=9)
    fig.colorbar(image,ax=axes.ravel().tolist(),label='Held-out price MAE, €/MWh',shrink=.8);path=ROOT/'research/assets'/f'{NAME}-zone-grid.png';fig.savefig(path,dpi=145);plt.close(fig);exports.append(path)
    lines=['# Learning technology supply curves: six month-ahead tests','',
      '**Implemented and evaluated:** fit January→test February, March→April, May→June, July→August, September→October and November→December. Each fit is independent. Results below cover **4,344 held-out hours**, not an out-of-fold 8,760-hour year. The accepted research baseline remains unchanged.','',
      '## Model and data','',
      'Keep all 48 bidding zones, existing PTDF/GSK/branch and link constraints, fixed hourly demand and fixed reservoir injections. Replace inherited price-fitted bids with source technology operating costs: monthly World Bank TTF/ECB for gas, daily EIA Brent/ECB and existing source-priced oil/CHP treatment, prepared coal/lignite/nuclear/other costs. Keep source capacity and weather availability, IRENA linear commissioning, the verified solar interval correction and generic 0.86/0.90 loss replacement. Remove empirical full-year country solar factors. No capacity is fitted or replaced by observed dispatch.','',
      'For each source technology/efficiency group, quantity offered at price p is `A × sigmoid((p − source_cost − calendar_shift) / spread)`. A is source available MW. Midpoint shift uses an intercept and the first two local-time daily sine/cosine harmonics, including DST; spread is positive, between 1 and 100 €/MWh. Effective shift is bounded ±80 €/MWh. Eight equal-volume tranches sample the inverse sigmoid at bin midpoints; all eight sum exactly to available capacity. These are divisible offers and allow negative prices. Finite endpoint truncation is explicit: the logistic tails outside the first/last midpoint are approximated, not infinite market bids.','',
      'Parameters are shared **by country and Ember resource family**, because most generation observations are national, not bidding-zone-level. Original source technology/efficiency costs, hourly capacity and zonal network prices still differ. Wind combines on/offshore parameter adjustments; coal combines coal/lignite; oil and waste retain distinct source anchors under Other fossil. This first experiment does not identify independent parameters for every technology in every bidding zone.','',
      'Each odd month gets its own fit. Daily patterns repeat through that fit and the next test month; there is no separately fitted curve for each hour and no annually learned seasonal coefficient. The six pairs expose seasonal change explicitly. The model does not interpolate between fits using test observations. Flexible storage is not added: the separately tested storage candidate is unadopted and its full-year-fitted forecast would contaminate this experiment. Fixed reservoir output remains a conditional input.','',
      '## Fitting and isolation','',
      'First fit midpoint/spread from the odd month’s observed price–generation relationship. Use original ENTSO-E A75 hourly generation only when every technology constituent of the national family is available; use original Ember national monthly totals separately. Missing observations remain unknown. For inverse initialization only, zones without observed SDAC prices use the unfitted model’s own training-month prices, not invented observations. Monthly totals are never expanded into hourly targets.','',
      'Then propose up to three network-aware update rounds, with two fixed strengths (0.5 and 1). Each candidate is actually cleared for every training hour. Select the lowest training objective: `0.5 × price_MAE/50 + 0.5 × generation_normalized_MAE + parameter_ridge`. Price MAE equally weights 41 complete SDAC zones; generation averages available country/fuel monthly cells, normalized by max(source,0.25 TWh). The initializer is an inverse least-squares proposal, not proof of the best cleared-price fit. Network updates are bounded heuristic directions and exact objective comparisons, not a global optimisation guarantee.','',
      'Freeze the selected parameters and their target/source hashes before clearing or scoring the even month. Independently replay the initializer and network-update direction after replacing every other month’s price/generation target with extreme values: parameters/directions must remain identical. No even-month price or generation value selects a proposal, update strength or hyperparameter. The 41 complete price zones are a fixed source-coverage benchmark cohort. Repeated runs must use a fresh design if test outcomes motivate changes.','',
      '## Held-out results','',
      '| Model | Price MAE €/MWh | Monthly generation MAE TWh | Normalized generation MAE | Mix-share MAE percentage points |','|---|---:|---:|---:|---:|']
    for case,r in overall.items():lines.append(f"| {labels[case]} | {r['price_mae']:.3f} | {r['generation_mae_twh']:.4f} | {r['generation_normalized_mae']:.4f} | {r['generation_share_mae_percentage_points']:.2f} |")
    source_countries = sorted({r['country'] for r in monthly_rows if r['observed_twh'] is not None})
    lines += ['', f"Price headline: 41 complete SDAC zones, all 4,344 test hours, equally weighted by zone and hour. Monthly generation headline: {len(source_countries)} countries with available Ember cells, {overall['learned']['generation_cells']} matched country/family/month cells. **Mix-share coverage is narrower: {len(overall['learned']['generation_share_countries'])} countries / {overall['learned']['generation_share_country_months']} complete country-months / {overall['learned']['generation_share_cells']} share cells.** Missing countries/families are excluded rather than counted as zero; all 34 modeled national scopes remain in the CSV. Nuclear availability retains the inherited historical proxy, not a newly verified 2025 outage series."]
    worse = [z for z in sealed['zones'] if any(r['case']=='learned' and r['zone']==z and r['hours']==4344 and r['mae_eur_mwh']>next(a['mae_eur_mwh'] for a in zones if a['case']=='control' and a['zone']==z) for r in zones)]
    solar = {c:float(np.mean([r['absolute_error_twh'] for r in monthly_rows if r['case']==c and r['family']=='Solar' and r['absolute_error_twh'] is not None])) for c in ['control','learned']}
    lines += ['', f"**Adverse outcomes:** {len(worse)} of 41 zones worsen against the unfitted control: {', '.join(worse)}. Solar monthly generation MAE rises from {solar['control']:.4f} to {solar['learned']:.4f} TWh, despite the overall generation improvement. These results are retained; aggregate gains do not justify automatic adoption."]
    lines += ['',f'![Six-fold price and generation results](assets/{NAME}.png)','',
      '| Fit→test | Control price MAE | Learned price MAE | Control mix NMAE | Learned mix NMAE |','|---|---:|---:|---:|---:|']
    for row in summary['pairs']:
        a=row['test_control'];b=row['test_selected'];lines.append(f"| {row['train_month']}→{row['test_month']} | {a['price_mae']:.2f} | {b['price_mae']:.2f} | {a['generation_normalized_mae']:.4f} | {b['generation_normalized_mae']:.4f} |")
    limited = sum(r['inverse_converged'] is False for r in parameters)
    lines += ['', f'{limited} country/resource inverse initializations hit their declared evaluation limit across the six fits. These are retained bounded proposals, not claimed nonlinear optima; subsequent selection uses actual constrained training clears. Fit support, convergence flags and every learned coefficient are in the parameter CSV.']
    lines += ['', f'![Per-zone held-out MAE grid](assets/{NAME}-zone-grid.png)', '', f'![Examples from Norway, Germany, Spain and France](assets/{NAME}-examples.png)', '',
      'Generation errors above compare all available Ember family cells, including fixed hydro and source families absent from the modeled fleet. Their error cannot all be removed by fitting bids. Mix-share MAE separately compares each family’s fraction of national generation in percentage points, only for country/months with all nine source families known and positive totals; the fitting objective uses energy errors, not this additional share metric. The hourly-generation CSV separately reports each available country/technology on its matched hourly observations; incomplete series are not annualized. Accepted-baseline generation inside pooled source columns remains an illustrative proportional allocation. The new explicit technology offers represent an assumed allocation of source capacity, not recovered individual operator orders.','',
      '## Interpretation and limitations','',
      'The fair learning comparison is against the unfitted sigmoid control with identical source availability and network. The accepted baseline is shown on the same test hours for context, but was fitted using the whole year and retains annual solar factors; it is **not a cross-validated competitor**. These six independently trained policies do not form one fitted annual model, and the odd months are training data rather than held-out predictions.','',
      'All of 2025 had already been inspected. Current source choices, static network adjustments, fixed hydro schedules, annual capacity endpoints and weather inputs are inherited/hindsight assumptions. Consequently this is **conditional retrospective month-ahead validation**, not an untouched operational forecast test. Source national generation also differs from scheduled day-ahead dispatch; gross/net coverage, self-consumption, storage classification and missing fleets can limit achievable agreement. The fit cannot uniquely recover bidding curves away from the observed clearing points or establish investment counterfactual accuracy. Learned shifts may compensate for missing outages or incorrect renewable yield rather than real bidding behaviour; in particular a positive learned renewable bid is not evidence of that resource’s actual operating cost. The parameter CSV includes fit support/convergence so weakly identified families remain visible.','',
      '## Verification and runtime','',
      f"Independent audit replays **{audit['retained_witness_hours']:,} retained training/test LP hours** (selected and control), their volume sums, source hashes, objective/dual certificates, generation closure and fold isolation. Max physical residual {audit['maximum_certificate']['primal_mw']:.3g} MW; duality gap {audit['maximum_certificate']['duality_gap_eur']:.3g} EUR. Zero emergency dispatch required. Four focused tests cover monotone quantiles/volume, chronological splits, target poisoning and invalid primal/price rejection.",'',
      f"Preparation took {sealed['preparation_seconds']:.1f} s; six-pair execution {summary['execution_seconds']:.1f} s; independent audit active time {audit['seconds']:.1f} s (excluding waiting for completed pairs). Training clearing {sum(r['training_clearing_seconds'] for r in summary['pairs']):.1f} s; selected plus control even-month clearing {sum(r['test_clearing_seconds'] for r in summary['pairs']):.1f} s. The auditor ran alongside later fits on a two-CPU environment, so these are experiment wall costs, not isolated solver benchmarks or a fresh full-year scenario timing. Each process uses one solver/BLAS thread and a 5 GiB address-space cap.",'',
      '## Conclusion','']
    pdelta=overall['learned']['price_mae']-overall['control']['price_mae'];gdelta=overall['learned']['generation_normalized_mae']-overall['control']['generation_normalized_mae']
    lines += [f"The framework can fit curves on an odd month and run the following month without using its targets. In these six tests, learning changes price MAE by **{pdelta:+.3f} €/MWh** and normalized generation error by **{gdelta:+.4f}** relative to the same-input unfitted control. Both aggregate metrics improve in every test month, but {len(worse)} Nordic zones and solar generation worsen. This experiment does not promote a model or establish the €10/MWh goal. Any next curve/feature changes require a new declared experiment; these test months have now been used for evaluation.", '',
      '[Per-fold metrics]('+NAME+'-folds.csv) · [Per-zone prices]('+NAME+'-zones.csv) · [Country/fuel/month generation]('+NAME+'-generation.csv) · [Matched hourly generation metrics]('+NAME+'-hourly-generation.csv) · [Learned parameters and fitting support]('+NAME+'-parameters.csv). Full inputs, parameter proposals, history and witnesses stay ignored locally in `data/bidding-zone-network-2025/sigmoid-month-pairs-v1/`.','',
      'Related methods: [Mahler et al., parameterised structural supply curves](https://doi.org/10.1016/j.eneco.2022.105811); [Liang & Dvorkin, inverse marginal-offer recovery](https://arxiv.org/abs/2302.05498); [Pinhão et al., curve representation and forecasting](https://doi.org/10.3390/math10122012). Our national-family sigmoid, fitting objective and six-pair protocol are a separate implementation, not a reproduction of those studies.','']
    path=ROOT/'research'/f'{NAME}.md';path.write_text('\n'.join(lines));exports.append(path)
    write(OUT/'report-receipt.json',dict(producer_sha256=digest(__file__),audit_sha256=digest(OUT/'audit.json'),summary_sha256=digest(OUT/'summary.json'),overall=overall,exports={str(p.relative_to(ROOT)):digest(p) for p in exports}))
    print(json.dumps(overall,indent=2),flush=True)


if __name__ == '__main__': report()
