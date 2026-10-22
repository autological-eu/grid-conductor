"""Compact regression and post-clearing generation/price report; no promotion."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from generation_mix_2025 import ROOT,digest
from report_solar_fleet_2025 import table_export

OUT=ROOT/'data/bidding-zone-network-2025/solar-country-fit-v1'
REPORT=ROOT/'research/solar-alignment-2025.md'


def report():
    a=json.loads((OUT/'audit.json').read_text());s=json.loads((OUT/'summary.json').read_text());p=json.loads((OUT/'inputs.json').read_text())
    assert a['status']=='all_17520_regression_source_native_and_kkt_replays_passed'
    assert a['summary_sha256']==digest(OUT/'summary.json') and a['inputs_sha256']==digest(OUT/'inputs.json')
    assert a['auditor_sha256']==digest(ROOT/'tools/audit_solar_country_fit_2025.py')
    for f,h in a['audit_dependencies'].items():assert digest(ROOT/'tools'/f)==h
    assert digest(ROOT/'data/pypsa-eur/ember-current-release/monthly.csv')==a['original_ember_sha256']
    fit={r['country']:r for r in p['factors']};base={r['country']:r for r in a['quantities']['control']};candidate={r['country']:r for r in a['quantities']['country_factors']}
    bm={(r['country'],r['month']):r for r in a['monthly']['control']};cm={(r['country'],r['month']):r for r in a['monthly']['country_factors']}
    rows=[];monthly=[]
    for c,r in fit.items():
        target=r['target_monthly_twh'];complete=all(v is not None for v in target)
        old_error=float(np.mean([abs(bm[c,m]['dispatch_twh']-target[m-1]) for m in range(1,13)])) if complete else None
        new_error=float(np.mean([abs(cm[c,m]['dispatch_twh']-target[m-1]) for m in range(1,13)])) if complete else None
        rows.append(dict(country=c,factor=r['factor'],raw_factor=r['raw_factor'],status=r['status'],
            input_weather_twh=float(sum(r['weather_monthly_twh'])),target_twh=sum(target) if complete else None,
            control_dispatch_twh=base[c]['dispatch_twh'],fitted_dispatch_twh=candidate[c]['dispatch_twh'],
            fitted_lower_twh=candidate[c]['dispatch_lower_twh'],fitted_upper_twh=candidate[c]['dispatch_upper_twh'],
            control_monthly_mae_twh=old_error,fitted_monthly_mae_twh=new_error,
            weather_monthly_sse=r['input_monthly_sse'],fitted_weather_monthly_sse=r['scaled_weather_monthly_sse']))
        for m in range(1,13):
            monthly.append(dict(country=c,month=m,factor=r['factor'],target_twh=target[m-1],
                control_twh=bm[c,m]['dispatch_twh'],fitted_twh=cm[c,m]['dispatch_twh'],
                fitted_lower_twh=cm[c,m]['lower_twh'],fitted_upper_twh=cm[c,m]['upper_twh']))
    price=[]
    targets=np.load(ROOT/'data/price-trace/sdac-hourly-2025-v1/prices.npz')['prices']
    for case,record in s['cases'].items():
        witness=ROOT/record['annual']['witness'];assert digest(witness)==record['annual']['witness_sha256']
        with np.load(witness) as z:prices=z['row_duals'][:,:targets.shape[1]]
        for j,r in enumerate(record['metrics']['zones']):
            mask=np.isfinite(targets[:,j]);assert int(mask.sum())==r['known_hours']
            if mask.any():
                assert abs(abs(prices[mask,j]-targets[mask,j]).mean()-r['mae_eur_mwh'])<1e-9
                assert abs(np.corrcoef(prices[mask,j],targets[mask,j])[0,1]-r['correlation'])<1e-9
    for old,new in zip(s['cases']['control']['metrics']['zones'],s['cases']['country_factors']['metrics']['zones'],strict=True):
        assert old['zone']==new['zone']
        known=old['known_hours']==8760
        price.append(dict(zone=old['zone'],hours=old['known_hours'],control_mae=old.get('mae_eur_mwh'),fitted_mae=new.get('mae_eur_mwh'),
            delta_mae=new['mae_eur_mwh']-old['mae_eur_mwh'] if known else None,
            control_correlation=old.get('correlation'),fitted_correlation=new.get('correlation')))
    folder=ROOT/'research';exports=[]
    for file,data in [('solar-country-fit-2025.csv',rows),('solar-country-fit-2025-monthly.csv',monthly),('solar-country-fit-2025-prices.csv',price)]:
        path=folder/file;table_export(path,data);exports.append(path)
    chosen=['DE','FR','GB','AT','CH','PL'];fig,axes=plt.subplots(1,2,figsize=(13,8),gridspec_kw={'width_ratios':[1.05,1]})
    ax=axes[0];pos=np.arange(len(chosen))
    ax.bar(pos-.25,[base[c]['dispatch_twh'] for c in chosen],width=.23,color='#888888',label='Control dispatch')
    vals=np.array([candidate[c]['dispatch_twh'] for c in chosen]);low=np.array([candidate[c]['dispatch_lower_twh'] for c in chosen]);high=np.array([candidate[c]['dispatch_upper_twh'] for c in chosen])
    ax.bar(pos,vals,width=.23,color='#377eb8',label='Fitted-factor dispatch',yerr=np.array([vals-low,high-vals]),capsize=2,error_kw=dict(lw=.8))
    ax.bar(pos+.25,[sum(fit[c]['target_monthly_twh']) for c in chosen],width=.23,color='#4daf4a',label='Ember monthly sum')
    ax.set_xticks(pos,chosen);ax.set_ylabel('Full-year allocated PV generation, TWh');ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
    ax.set_title('Generation after coupled clearing\nThin bars: conditional allocation bounds')
    ax=axes[1];known=sorted([r for r in price if r['hours']==8760],key=lambda r:r['delta_mae']);pos=np.arange(len(known))
    ax.barh(pos,[r['delta_mae'] for r in known],color=['#377eb8' if r['delta_mae']<0 else '#d95f02' for r in known])
    ax.set_yticks(pos,[r['zone'] for r in known],fontsize=7);ax.axvline(0,color='black',lw=.8);ax.set_xlabel('Change in full-year price MAE, €/MWh');ax.set_title('Every complete SDAC price zone\nBlue improves; orange worsens');ax.grid(axis='x',alpha=.2)
    fig.suptitle('Country solar factors: generation fit and price accuracy are separate checks');fig.tight_layout(rect=(0,0,1,.96))
    image=folder/'assets/solar-country-fit-2025.png';fig.savefig(image,dpi=140,metadata={'Software':'Grid Conductor'});plt.close(fig);exports.append(image)
    calibrated=[r for r in rows if r['status']=='fitted'];before=np.mean([r['control_monthly_mae_twh'] for r in calibrated]);after=np.mean([r['fitted_monthly_mae_twh'] for r in calibrated])
    gen_better=sum(r['fitted_monthly_mae_twh']<r['control_monthly_mae_twh'] for r in calibrated);better=sum(r['delta_mae']<0 for r in known);worse=sum(r['delta_mae']>0 for r in known)
    lines=['## Country solar-factor regression — 22 October 2026','',
        f"**Implemented and independently tested:** one zero-intercept factor for each of {len(calibrated)} eligible countries, using monthly generation only. All 8,760 hours clear with zero emergency. European price MAE **{s['cases']['control']['europe_mae']:.3f} → {s['cases']['country_factors']['europe_mae']:.3f} €/MWh**; {better} zones improve and {worse} worsen. This candidate is not promoted.",'',
        '### Method and limits','',
        r'For each country, form twelve monthly energy values $x_m$ from the preserved, interval-aligned weather/IRENA PV profiles after the generic loss correction. Fit original Ember Solar totals $y_m$ with $\alpha=\sum_m x_m y_m/\sum_m x_m^2$, without an intercept. Apply that same factor to every source PV hour and region in the country before offer pooling. No hourly generation is copied into the inputs, and no price enters the regression.','',
        'This fits **pre-clearing available energy**, not an assumed linear response of market dispatch. Rerunning the network determines curtailment and generation afterward. One pass only: no seasonal coefficients, dispatch-feedback refit or price-selected iteration. Nameplate, original profile files, night zeros, geography, IRENA commissioning and all non-PV inputs/bids remain unchanged.','',
        'Require twelve finite nonnegative Ember months and compatible IRENA Solar/PV parent endpoints within 2 MW rounding tolerance. The Netherlands is excluded for the documented source conflict. Spain and Italy retain their inputs because the strict parent check detects solar thermal (including Italy\'s small 5 MW difference). A declared reduction-only guard accepts raw factors from 0.5 to 1; rejected values remain reported and their applied factor stays 1, never clipped. The guard is a research assumption, not a verified physical bound.','',
        'All 34 countries and exclusion/raw-coefficient records are in the CSV. Norwegian raw factor is about0.0129 and is rejected, rather than removing98.7% of weather-derived PV to reproduce9GWh. Upward fits and missing/incompatible sources are also retained unchanged. Country-specific gross/grid-feed-in, demand, AC/DC and geographical scope remain limitations: this empirical factor can absorb measurement, losses, curtailment or fleet-model errors. It does not identify physical efficiency or market-eligible capacity.','',
        '### Generation after clearing','',
        f"Across the {len(calibrated)} fitted countries, equal-country mean monthly generation MAE against the fitting source changes **{before:.4f} → {after:.4f} TWh/month**; {gen_better} countries improve on that metric. These are post-clearing allocated generation comparisons, not just the regression's algebraic weather fit. They are in-sample and do not establish unseen-year accuracy or uniquely recovered unit dispatch.",'',
        '| Country | Factor | Control TWh | After clearing TWh | Ember TWh |',
        '|---|---:|---:|---:|---:|']
    for c in chosen:
        lines.append(f"| {c} | {fit[c]['factor']:.4f} | {base[c]['dispatch_twh']:.3f} | {candidate[c]['dispatch_twh']:.3f} | {sum(fit[c]['target_monthly_twh']):.3f} |")
    lines += ['', '![Generation and every-zone price comparison](assets/solar-country-fit-2025.png)','',
        'Conditional generation-allocation bounds remain explicit. Correcting input PV in one country can change curtailment and generation in other countries whose factor is unchanged. A national energy match also cannot correct an incorrect within-day shape through a single scalar.','',
        '### Price result and verification','',
        'Generation calibration does not guarantee better prices. Germany and France improve, but the all-zone score worsens; every covered zone is shown in the figure/CSV. Existing bids were calibrated against earlier inputs/auction targets, and source-boundary/network uncertainties remain. This experiment does not identify which of those causes the price trade-off. Price results remain a retrospective cross-target check: all2025 was already inspected, so this is not independent forecasting validation.','',
        f"Independent audit reads the original Ember provider CSV, checks IRENA scope, solves the regression with a separate least-squares implementation, reconstructs the PV-only delta and replays **17,520 hourly native/KKT certificates**. Maximum native residual **{max(r['native_residual_mw'] for r in a['cases'].values()):.3g} MW**, duality gap **{max(r['duality_gap_maximum_eur'] for r in a['cases'].values()):.3g} EUR**; zero emergency in both years. New annual driver **{s['cases']['country_factors']['annual']['clearing_seconds']:.1f}s**, independent audit **{a['seconds']:.1f}s**, excluding source preparation. Three tests cover scalar recovery/no intercept, missing data and rejected-factor behavior.",'',
        '[All country factors, eligibility, raw slopes and post-clearing scores](solar-country-fit-2025.csv) · [Monthly target/control/cleared quantities and bounds](solar-country-fit-2025-monthly.csv) · [All48 price zones, including missing targets](solar-country-fit-2025-prices.csv).','',
        'Design: config/solar-country-fit-2025.json. New producer/auditor/renderer are named solar_country_fit_2025; exact local sources, delta, witnesses, source-fit/audit summaries and renderer receipt remain in ignored data/bidding-zone-network-2025/solar-country-fit-v1/. The source-loss control is reused byte-for-byte. Public and accepted baselines remain unchanged; automatic reviews stay disabled.','']
    marker='## Country solar-factor regression — 22 October 2026';old=REPORT.read_text().split(marker)[0].rstrip();REPORT.write_text(old+'\n\n'+'\n'.join(lines));exports.append(REPORT)
    result=dict(producer_sha256=digest(__file__),helper_sha256=digest(ROOT/'tools/report_solar_fleet_2025.py'),summary_sha256=digest(OUT/'summary.json'),audit_sha256=digest(OUT/'audit.json'),
        fitted_countries=len(calibrated),post_clear_monthly_mae_control=float(before),post_clear_monthly_mae_fitted=float(after),generation_improved_countries=gen_better,
        exports={str(f.relative_to(ROOT)):digest(f) for f in exports})
    (OUT/'report-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Fitted countries',len(calibrated),'post-clearing monthly MAE',before,'→',after,'improved',gen_better,flush=True)


if __name__=='__main__':report()
