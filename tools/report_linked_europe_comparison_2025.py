"""Compact observed-price and generation report for the saved linked annual run."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
from generation_mix_2025 import ROOT,digest,EMBER

OUT=ROOT/'data/bidding-zone-network-2025/europe-linked-clearing-robust-v1/observed-comparison-v1'
REPORT=ROOT/'research/europe-linked-clearing-2025-observed'


def export(path,rows):
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def report():
    s=json.loads((OUT/'summary.json').read_text());audit=json.loads((OUT/'audit.json').read_text())
    assert audit['summary_sha256']==digest(OUT/'summary.json') and audit['auditor_sha256']==digest(ROOT/'tools/audit_linked_europe_comparison_2025.py')
    assert s['producer_sha256']==digest(ROOT/'tools/evaluate_linked_europe_2025.py')
    for f,h in s['sources'].items():assert digest(ROOT/f)==h
    assert s['hourly_sha256']==digest(OUT/'hourly-comparison.npz')
    with np.load(OUT/'hourly-comparison.npz') as z:arrays={k:z[k] for k in z.files}
    files=[];prices=[]
    for zone in s['zones']:
        old=next(r for r in s['prices'] if r['case']=='baseline' and r['zone']==zone);new=next(r for r in s['prices'] if r['case']=='linked' and r['zone']==zone)
        row=dict(zone=zone,observed_hours=old['known_hours'])
        for k in ['mae_eur_mwh','bias_eur_mwh','rmse_eur_mwh','correlation','demeaned_mae','ramp_mae','coupled_hour_mae']:
            row['baseline_'+k]=old.get(k);row['linked_'+k]=new.get(k)
        row['mae_change_eur_mwh']=new['mae_eur_mwh']-old['mae_eur_mwh'] if old['known_hours'] else None;prices.append(row)
    path=Path(str(REPORT)+'-prices.csv');export(path,prices);files.append(path)
    generation=[]
    for c in s['countries']:
        for fuel in EMBER:
            rs={case:[r for r in s['ember_monthly'] if r['case']==case and r['country']==c and r['fuel']==fuel] for case in ['baseline','linked']};known=[r for r in rs['baseline'] if r['observed_twh'] is not None]
            row=dict(country=c,fuel=fuel,observed_months=len(known),observed_twh=sum(r['observed_twh'] for r in known) if len(known)==12 else None)
            for case,r in rs.items():
                row[case+'_annual_twh']=sum(v['model_twh'] for v in r)
                row[case+'_matched_month_mae_twh']=float(np.mean([v['absolute_error_twh'] for v in r if v['absolute_error_twh'] is not None])) if known else None
            generation.append(row)
    path=Path(str(REPORT)+'-generation.csv');export(path,generation);files.append(path)
    fields=['case','country','technology','known_hours','expected_hours','status','model_twh','observed_twh','lower_twh','upper_twh','mae_mw','correlation']
    path=Path(str(REPORT)+'-hourly-generation.csv');export(path,[{f:r.get(f) for f in fields} for r in s['hourly_generation']]);files.append(path)
    complete=[r for r in prices if r['observed_hours']==8760];complete.sort(key=lambda r:r['mae_change_eur_mwh'])
    fig,axes=plt.subplots(1,2,figsize=(13,10));ax=axes[0];delta=[r['mae_change_eur_mwh'] for r in complete]
    ax.barh(range(len(complete)),delta,color=['#24769b' if v<0 else '#bd6438' for v in delta]);ax.set_yticks(range(len(complete)),[r['zone'] for r in complete],fontsize=8);ax.axvline(0,color='black',lw=.7);ax.set_xlabel('Linked minus baseline price MAE, €/MWh');ax.set_title('All 41 complete SDAC zones\nNegative improves; changes are small');ax.grid(axis='x',alpha=.2)
    ax=axes[1];fuels=list(EMBER);xs=np.arange(len(fuels));old=[s['ember_scores']['baseline'][f] for f in fuels];new=[s['ember_scores']['linked'][f] for f in fuels]
    ax.barh(xs-.18,old,height=.35,label='Accepted baseline',color='#a7a7a7');ax.barh(xs+.18,new,height=.35,label='Linked prototype',color='#24769b');ax.set_yticks(xs,fuels);ax.set_xlabel('Mean country/month generation MAE, TWh');ax.set_title('Against original Ember monthly totals\nSame reported cells in both models');ax.legend();ax.grid(axis='x',alpha=.2)
    fig.suptitle('Linked bids: almost unchanged observed-price and generation fit');fig.tight_layout(rect=(0,0,1,.96));path=ROOT/'research/assets/europe-linked-clearing-2025-observed.png';fig.savefig(path,dpi=140);plt.close(fig);files.append(path)
    fig,axes=plt.subplots(4,2,figsize=(15,13));start=12*24;end=21*24;times=np.arange('2025-01-01T00','2026-01-01T00',dtype='datetime64[h]')[start:end]
    palette=plt.get_cmap('tab10').colors
    for ri,(c,z) in enumerate([('NO','NO2'),('DE','DE-LU'),('ES','ES'),('FR','FR')]):
        ax=axes[ri,0];zi=s['zones'].index(z)
        ax.plot(times,arrays['observed_prices'][start:end,zi],label='Observed SDAC',color='#222222',lw=1)
        ax.plot(times,arrays['baseline_prices'][start:end,zi],label='Accepted baseline',color='#b67d31',lw=1,ls='--')
        ax.plot(times,arrays['linked_prices'][start:end,zi],label='Linked prototype',color='#24769b',lw=.9)
        ax.set_title(z+' prices · 13–21 January');ax.set_ylabel('€/MWh');ax.grid(alpha=.2)
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2));ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        if ri==0:ax.legend(fontsize=8)
        ax=axes[ri,1];bottom=np.zeros(3);covered=[]
        for fi,fuel in enumerate(fuels):
            r=next(r for r in generation if r['country']==c and r['fuel']==fuel)
            if r['observed_months']!=12:continue
            covered.append(fuel);v=np.array([r['baseline_annual_twh'],r['linked_annual_twh'],r['observed_twh']]);ax.bar(range(3),v,bottom=bottom,label=fuel,color=palette[fi]);bottom+=v
        ax.set_ylim(0,max(bottom)*1.08);ax.set_xticks(range(3),['Baseline','Linked','Ember']);ax.set_ylabel('TWh in fully reported fuel groups');ax.set_title(f'{c} national 2025 mix · {len(covered)}/9 fuel groups');ax.grid(axis='y',alpha=.2)
    handles=[Patch(facecolor=palette[i],label=f) for i,f in enumerate(fuels)];fig.legend(handles,[f for f in fuels],loc='lower center',ncol=5,fontsize=9);fig.tight_layout(rect=(0,.05,1,.98));path=ROOT/'research/assets/europe-linked-clearing-2025-country-comparison.png';fig.savefig(path,dpi=140);plt.close(fig);files.append(path)
    b=s['price_scores']['baseline'];n=s['price_scores']['linked'];improvement=100*(b['mae']-n['mae'])/b['mae'];better=sum(v<0 for v in delta);worse=sum(v>0 for v in delta)
    lines=['# Linked bids: observed 2025 prices and generation','',
        f"**Result:** the saved 365-day linked-order prototype changes European price MAE **{b['mae']:.3f} → {n['mae']:.3f} €/MWh ({improvement:.3f}% lower)**. Generation is almost unchanged: gas fit worsens slightly, coal/hydro improve slightly, wind/solar are essentially unchanged. **The measured accuracy benefit does not justify replacing the accepted ~52-second continuous baseline with this ~37-minute prototype.** This evaluates the specified synthetic packages, not the value of all possible block/linked bidding strategies.",'',
        '## Saved results and comparison scope','',
        'All daily dispatch, coupled primal/dual prices, acceptance ratios and storage flows remain in the ignored local cloud cache `data/bidding-zone-network-2025/europe-linked-clearing-robust-v1/`, with six seed witnesses referenced in `europe-linked-clearing-priced-v1/`. The parent audit independently replayed all 365 days/8,760 physical hours and linked-price/storage certificates. No market solve was repeated for this report. A derived `observed-comparison-v1/hourly-comparison.npz` contains both annual price/generation arrays and the observations; source hashes and metric audit remain beside it. These full hourly witnesses are local cache files, not Git-backed remote backups. Only this report, compact summary CSVs, figures and reproducible code are committed.','',
        'Baseline means the user-accepted `solar-anchor-bids-v1/resource_full`, not the older model in the public country explorer. Linked means the same inputs/grid/fixed hydro plus ~44.45 GW of synthetic gas packages and three hypothetical 100 MW/400 MWh batteries. Six hours/day are newly coupled and 18 exact unchanged hours reused. Comparison covers all 8,760 hours; it does not treat the six-hour subset as a full-year sample. Cached own-model storage forecasts are unchanged.','',
        'Prices use **corrected hourly ENTSO-E main SDAC day-ahead auction observations**, already interval-averaged into hourly targets. Equal-zone annual MAE uses the same 41 complete zones out of 48 modeled zones. Missing source observations remain unknown. No target refit, new fuel-price calibration, baseline adoption or public explorer replacement occurs. Generation uses original monthly Ember country/fuel totals and hourly ENTSO-E A75 generation where all required national/constituent areas report the technology/hour. IRENA supplies capacity inputs, not hourly generation observations.','',
        '## Price performance','',
        '| Metric | Accepted baseline | Linked prototype |','|---|---:|---:|',
        f"| Full-year equal-zone MAE, €/MWh | {b['mae']:.4f} | {n['mae']:.4f} |",
        f"| Mean zonal correlation | {b['correlation']:.4f} | {n['correlation']:.4f} |",
        f"| Daily-demeaned MAE, €/MWh | {b['demeaned_mae']:.4f} | {n['demeaned_mae']:.4f} |",
        f"| Pooled MAE when observed price >300 €/MWh | {b['above_300_mae']:.2f} | {n['above_300_mae']:.2f} |",'',
        f'{better} complete zones improve and {worse} worsen. Scarcity-spike error remains large; adding these packages does not recover the missing spikes. Price changes can reflect both allocation and the choice of supporting LP duals. Fixed-integer prices satisfy the retained family/KKT checks, but this is a heuristic supported-price incumbent rather than full EUPHEMIA certification or proof that observed commercial bids were recovered.','',
        '| Zone | Baseline MAE | Linked MAE | Baseline correlation | Linked correlation |','|---|---:|---:|---:|---:|']
    for zone in ['DE-LU','ES','FR','NO1','NO2','NO3','NO4','NO5']:
        r=next(r for r in prices if r['zone']==zone);lines.append(f"| {zone} | {r['baseline_mae_eur_mwh']:.3f} | {r['linked_mae_eur_mwh']:.3f} | {r['baseline_correlation']:.3f} | {r['linked_correlation']:.3f} |")
    lines+=['','![All-zone price changes and generation accuracy](assets/europe-linked-clearing-2025-observed.png)','',
        '## Generation mix','',
        'The table averages absolute monthly generation error across the **same known country/fuel/month cells**, including observed zero output. Each fuel has different source coverage. The CSV includes observed months and annual totals only when all 12 months report. These all-country metrics have broader coverage than the earlier solar score over 21 fitted countries and the earlier thermal score limited to modeled fleets; they should not be compared as identical scores.','',
        '| Ember fuel group | Complete countries | Baseline monthly MAE, TWh | Linked monthly MAE, TWh |','|---|---:|---:|---:|']
    for fuel in fuels:
        count=sum(r['fuel']==fuel and r['observed_months']==12 for r in generation);lines.append(f"| {fuel} | {count} | {s['ember_scores']['baseline'][fuel]:.4f} | {s['ember_scores']['linked'][fuel]:.4f} |")
    lines+=['','Across the complete national source scopes, baseline wind generation is about 643.84 TWh versus 568.37 TWh observed; gas is 372.33 versus 528.83 TWh, and coal 207.67 versus 279.21 TWh. The prototype barely changes those fleet-wide gaps. These are sums over each fuel’s covered country set, not a harmonized EU total. Price and quantity source-boundary differences remain.','',
        'Technology allocations within pooled equal-price source offers are proportional to current member availability; 108 compiled offers contain multiple country/technology labels. Current corrected PV components are reconstructed separately; all capacities partition the sealed offer bounds. Thermal pure-country/fuel groups are identified, while renewable mix points can be nonunique. Hourly CSVs retain conditional allocation bounds, not confidence intervals; different bounds cannot generally be attained jointly. Fixed reservoir generation is reconstructed from sealed native demand, displacement offsets and zonal residual-load weights.','',
        f"Hypothetical batteries consume **{s['storage_charge_twh']:.6f} TWh** and return **{s['storage_discharge_twh']:.6f} TWh**. Their discharge is excluded from primary generation mix and reported separately. ENTSO-E pumped-storage production/consumption is not silently folded into reservoir generation. Gross/net output, Ember Other fossil versus oil/waste, geography and unreported types remain limitations; missing data are never zero-filled.",'',
        '## Country examples','',
        'The left panels show hourly observed and model prices during 13–21 January; nearly overlapping model curves are an actual result. Norway uses NO2 as the price example and national NO for generation. The right panels compare annual primary generation for fuel groups with all 12 Ember months; omitted groups remain unknown, so bars are covered mix rather than certified total generation.','',
        '![NO, DE, ES and FR prices and generation mix](assets/europe-linked-clearing-2025-country-comparison.png)','',
        '## Verification and conclusion','',
        f"The source-bound producer checks all daily witness hashes, exact reuse of the 6,570 independent hours, current PV/source-capacity partition (maximum difference {s['maximum_capacity_partition_mw']:.3g} MW), primary-generation closure and source coverage. An independent metric replay checks {audit['price_zone_case_checks']} available zone/case price records, {audit['monthly_generation_checks']} country/fuel/month results against original Ember CSV cells and {audit['hourly_generation_checks']} available hourly technology/country/case comparisons. Original physical/price-family/storage audit remains linked; this reporting audit does not claim a new native solve or unique generation allocation.",'',
        'Keep the accepted continuous baseline. The next useful changes should target the much larger source/mix and scarcity-price discrepancies, then test block strategies with source-backed plant commitments or observed operator behavior. The current result gives no evidence that the extra discrete complexity materially improves the observed fit. Both models remain calibrated 2025 reconstructions, not independent forecasts or validated investment estimators.','',
        '[All 48 price-zone comparisons](europe-linked-clearing-2025-observed-prices.csv) · [All country/Ember fuel comparisons](europe-linked-clearing-2025-observed-generation.csv) · [Hourly ENTSO-E technology metrics and allocation bounds](europe-linked-clearing-2025-observed-hourly-generation.csv) · [Measured runtime and scope](europe-linked-clearing-2025-runtime.md).','']
    path=Path(str(REPORT)+'.md');path.write_text('\n'.join(lines));files.append(path)
    write=dict(producer_sha256=digest(__file__),summary_sha256=digest(OUT/'summary.json'),audit_sha256=digest(OUT/'audit.json'),exports={str(f.relative_to(ROOT)):digest(f) for f in files})
    (OUT/'report-receipt.json').write_text(json.dumps(write,indent=2)+'\n');print('Compared MAE',b['mae'],'to',n['mae'],'exports',len(files),flush=True)


if __name__=='__main__':
    from pathlib import Path
    report()
