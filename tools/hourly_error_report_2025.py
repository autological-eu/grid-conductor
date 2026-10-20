"""Retained four-figure report: error timing, mechanisms and weekly-bid test."""
import csv,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from generation_mix_2025 import ROOT,digest
from hourly_error_events_2025 import load,describe,ANCHORS


def render(folder,public,prefix):
    s=json.loads((folder/'summary.json').read_text());audit=json.loads((folder/'verification-v1/audit.json').read_text())
    assert audit['summary_sha256']==digest(folder/'summary.json')
    assert audit['auditor_sha256']==digest(ROOT/'tools/audit_weekly_supply_bids_2025.py')
    for p,h in s['source_hashes'].items():assert digest(ROOT/p)==h
    for p,h in s['dependencies'].items():assert digest(ROOT/'tools'/p)==h
    zones,o,models,_=load();labels={ANCHORS[0]:'Accepted baseline',ANCHORS[1]:'Joint checkpoint'}
    for key in ANCHORS:
        info=s['annuals'][key];p=folder/info['witness'];assert digest(p)==info['witness_sha256']
        with np.load(p) as z:models[key+'-weekly']=z['row_duals'][:,:len(zones)]
        labels[key+'-weekly']='Baseline + weekly bids' if key==ANCHORS[0] else 'Joint + weekly bids'
    order=[ANCHORS[0],ANCHORS[0]+'-weekly',ANCHORS[1],ANCHORS[1]+'-weekly']
    details={k:describe(models[k],o,zones) for k in order}
    def csvwrite(name,rows):
        with (public/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(key for r in rows for key in r)),lineterminator='\n');w.writeheader();w.writerows(rows)
    csvwrite('hourly-error-zones.csv',[dict(model=k,label=labels[k],**{n:v for n,v in r.items() if not isinstance(v,(list,dict))},correlation=float(np.corrcoef(models[k][:,zones.index(r['zone'])],o[:,zones.index(r['zone'])])[0,1]) if r['known_hours'] else None) for k in order for r in details[k]['zones']])
    periods=[];clock=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC')
    for k in order:
        periods.extend(dict(model=k,period_type='observed-price-regime',period=r['regime'],**{n:v for n,v in r.items() if n!='regime'}) for r in details[k]['regimes'])
        for month in range(1,13):
            e=models[k][clock.month==month]-o[clock.month==month];good=np.isfinite(e)
            periods.append(dict(model=k,period_type='UTC-month',period=month,zone_hours=int(good.sum()),mae=float(abs(e[good]).mean()),bias=float(e[good].mean())))
        periods.extend(dict(model=k,period_type='worst-UTC-day',period=r['utc_date'],mae=r['equal_zone_mae'],bias=r['mean_bias']) for r in details[k]['worst_utc_days'])
    csvwrite('hourly-error-periods.csv',periods)
    def save(fig,name):fig.savefig(public/name,dpi=150,bbox_inches='tight');plt.close(fig)
    colors=['#8796a7','#e39b4f','#087f79','#8a4c94']
    fig,axes=plt.subplots(1,2,figsize=(12,4.5));x=np.arange(6);width=.18
    for i,k in enumerate(order):
        r=details[k]['regimes'];axes[0].bar(x+(i-1.5)*width,[v['absolute_error_share']*100 for v in r],width,color=colors[i],label=labels[k]);axes[1].bar(x+(i-1.5)*width,[v['bias'] for v in r],width,color=colors[i])
    for ax in axes:ax.set_xticks(x,[r['regime'] for r in details[order[0]]['regimes']],rotation=25);ax.grid(axis='y',alpha=.2);ax.set_xlabel('Observed-price band (EUR/MWh)')
    axes[0].set_title('Where the absolute price error accumulates');axes[0].set_ylabel('Share of total absolute error (%)');axes[0].legend(fontsize=7)
    axes[1].set_title('High prices are systematically understated');axes[1].set_ylabel('Mean model − observed price (EUR/MWh)');axes[1].axhline(0,color='black',lw=.7);fig.tight_layout();save(fig,'overview.png')
    grid=np.array([[next(r for r in details[k]['zones'] if r['zone']==z).get('mae',np.nan) for k in order] for z in zones])
    fig,ax=plt.subplots(figsize=(9,14));cmap=plt.get_cmap('YlOrRd').copy();cmap.set_bad('#e5e8ec');im=ax.imshow(grid,aspect='auto',vmin=0,vmax=50,cmap=cmap)
    ax.set_xticks(range(4),[labels[k] for k in order],rotation=20,ha='right');ax.set_yticks(range(len(zones)),zones);ax.set_title('All-zone full-2025 price MAE; 8,760 hours\nGray: no complete observed-price target; no area dropped')
    for j in range(len(zones)):
        for i in range(4):
            if np.isfinite(grid[j,i]):ax.text(i,j,f'{grid[j,i]:.1f}',ha='center',va='center',fontsize=7,color='white' if grid[j,i]>32 else '#172635')
    fig.colorbar(im,ax=ax,shrink=.6,label='EUR/MWh; colors capped at 50, numbers uncapped');fig.tight_layout();save(fig,'zone-mae-grid.png')
    fig,axes=plt.subplots(1,2,figsize=(12,5));focus=['NO1','NO2','NO3','NO4','NO5','SE1','SE2','DE-LU','ES','FR'];pos=np.arange(len(focus));width=.18
    for i,k in enumerate(order):
        by={r['zone']:r for r in details[k]['zones']}
        axes[0].bar(pos+(i-1.5)*width,[by[z]['weekend_bias']-by[z]['weekday_bias'] for z in focus],width,color=colors[i],label=labels[k])
    axes[0].set_xticks(pos,focus,rotation=45);axes[0].set_ylabel('Weekend bias − weekday bias (EUR/MWh)');axes[0].set_title('Weekly price pattern missed by the model');axes[0].legend(fontsize=7);axes[0].grid(axis='y',alpha=.2)
    chosen=ANCHORS[1]+'-weekly';matrix=np.array([[r['bias'] for r in next(v for v in details[chosen]['zones'] if v['zone']==z)['monthly']] for z in focus]);im=axes[1].imshow(matrix,aspect='auto',cmap='RdBu_r',vmin=-60,vmax=60)
    axes[1].set_xticks(range(12),range(1,13));axes[1].set_yticks(range(len(focus)),focus);axes[1].set_xlabel('UTC month');axes[1].set_title('Remaining monthly bias: joint + weekly bids');fig.colorbar(im,ax=axes[1],label='Model − observed (EUR/MWh)');fig.tight_layout();save(fig,'national-mix.png')
    # A predeclared diagnosis window, not selected on the candidate's outcome.
    mask=(clock>=pd.Timestamp('2025-11-24',tz='UTC'))&(clock<pd.Timestamp('2025-11-27',tz='UTC'))
    fig,axes=plt.subplots(4,1,figsize=(12,9),sharex=True)
    for ax,z in zip(axes,['NO5','DE-LU','ES','FR']):
        j=zones.index(z);ax.plot(clock[mask],o[mask,j],color='#172635',lw=1.5,label='Observed ENTSO-E A44')
        for k,color in zip(order,colors):ax.plot(clock[mask],models[k][mask,j],lw=.9,color=color,label=labels[k])
        ax.set_ylabel(z+'\nEUR/MWh');ax.grid(alpha=.2)
    axes[0].set_title('24–26 November: shared high-price episode\nWindow chosen from both anchors before the weekly-bid clear');axes[0].legend(ncol=3,fontsize=7);fig.autofmt_xdate();fig.tight_layout();save(fig,'daily-prices.png')
    results=s['results'];table='\n'.join(f"| {labels[r['anchor']]} | {r['parent_metrics']['price']:.3f} → {r['metrics']['price']:.3f} | {r['parent_metrics']['daily_demeaned_price']:.3f} → {r['metrics']['daily_demeaned_price']:.3f} | {r['parent_metrics']['generation']:.4f} → {r['metrics']['generation']:.4f} | {r['parent_metrics']['trade']:.4f} → {r['metrics']['trade']:.4f} | {'pass' if r['eligible'] else 'fail'} |" for r in results)
    event=details[ANCHORS[1]];high=sum(v['absolute_error_share'] for v in event['regimes'][-2:]);negative=event['regimes'][0]['absolute_error_share']
    by={k:{r['zone']:r for r in details[k]['zones']} for k in order}
    zone_table='\n'.join('| '+z+' | '+' | '.join(f"{by[k][z]['mae']:.2f}" for k in order)+' |' for z in focus)
    coeff=json.loads((folder/'coefficients.json').read_text());mechanisms=json.loads((folder/'mechanisms.json').read_text())
    gas=sum(v['coefficient']!=0 for v in coeff[ANCHORS[1]]['support'] if v['resource']=='gas');coal=sum(v['coefficient']!=0 for v in coeff[ANCHORS[1]]['support'] if v['resource']=='coal');nuc=sum(v['coefficient']!=0 for v in coeff[ANCHORS[1]]['support'] if v['resource']=='nuclear')
    # Report exact totals rather than claiming a numerical certificate measures realism.
    maxphys=max(v['native_residual_mw'] for v in audit['certificates']);maxgap=max(v['duality_gap_maximum_eur'] for v in audit['certificates'])
    improvements=[100*(1-r['metrics']['price']/r['parent_metrics']['price']) for r in results]
    corr=[float(np.mean([np.corrcoef(models[k][:,j],o[:,j])[0,1] for j in range(len(zones)) if np.isfinite(o[:,j]).all()])) for k in order]
    report=f'''# European hourly clearing: diagnosing the price errors

Updated 20 October 2026. **The main problem is the shape and timing of prices, not one uniform Europe-wide offset.** The model understates high-price episodes, often overstates low-price hours, and misses a weekly pattern. Nordic errors also change sign by region and season. We traced these patterns through the saved full-year solutions and tested one bounded change to supply bids: a weekday/weekend term.

This remains a **2025 in-sample market reconstruction**, not independent forecasting, recovered actual order books or investment validation. The accepted research baseline remains the seasonal-calendar annual refit; the earlier joint supply/network fit is a separate checkpoint. Neither this test nor the joint checkpoint replaces the browser's two-zone scenario engine.

## 1. What the baseline clears

The model clears fixed observed/model-input zonal demand against synthetic resource supply offers for **48 modeled areas**, projected through a **145-bus physical backbone**. Each of the **8,760 hours** has a network-constrained linear dispatch solve. Daily grouping currently contains independent hourly solves; there is no new inter-hour commitment or adaptive reservoir optimisation.

Wind/solar offered MW come from retained weather profiles and capacity trajectories. Thermal offers use fuel, efficiency, carbon and operating-cost anchors, split into monotone supply blocks. Nuclear has its own offer. Smooth local-clock and seasonal adjustments, plus national generation consistency signals, are calibrated into the accepted supply bids. Hydro remains the retained fixed hourly injection schedule, not a freely priced reservoir bid. Passive AC constraints use the model PTDF/static generation-shift keys; controllable links retain bounds/losses. These are model-derived constraints, not certified JAO commercial domains.

The **joint checkpoint** additionally uses the frozen prior inverse gas/coal/nuclear bid fit and 15% higher effective Nordic-incident AC limits. It retains original wind availability, topology, impedances, GSKs, HVDC, demand and hydro. The headroom multiplier is a calibration assumption, not a verified grid correction. Its lower aggregate error conceals regressions in NO2/NO4 and Sweden. Full prior search outcomes, including rejected states, remain in the supporting CSVs below.

## 2. When and what kinds of errors occur

We compare model minus observed ENTSO-E day-ahead price, $e=p_{{model}}-p_{{observed}}$, preserving all **41 complete observed-price zones** and all hours. Positive bias means overpricing. The seven remaining modeled areas have no complete target and stay visibly missing. Local weekday/hour classifications include DST; shared event dates and monthly totals use UTC.

For both anchors, the three worst days are **25 November, 20 January and 15 January**. In the joint checkpoint, hours above **EUR 150/MWh account for {high*100:.1f}%** of total absolute error; observed negative-price hours account for **{negative*100:.1f}%**. The largest portion still accumulates in ordinary price bands because they contain far more hours. Fixing only rare extremes or negatives cannot close the overall gap.

![Absolute error contributions and signed bias by observed price regime]({prefix}overview.png)

These bands are diagnostic groupings using the observed target, never predictors passed to the solver. The model's supply stack frequently produces a narrow price range while real prices have deeper troughs and higher peaks. A calendar-only bid cannot reproduce a specific scarcity event merely because it occurred in winter. Zero renewable offers/positive thermal floors also miss negative-price mechanisms in western zones. Prior universal renewable discounts did not establish a satisfactory fleet-wide correction, so they are not silently reintroduced here.

The weekly mismatch is widespread: modeled-minus-observed bias is more positive on weekends than weekdays, even though source demand already varies hourly. A missing weekly bid effect is therefore a testable hypothesis; it is **not proof** that real suppliers use exactly this rule or that demand inputs are complete. Local interior-offer diagnostics distinguish gas/coal/nuclear support from hours without a matching local marginal offer. Network dual terms are an exact witness decomposition, not causal error shares or uniquely identified real price setters.

There are two materially different mechanisms in the saved solutions. In Germany, local gas/coal offers match the joint checkpoint price in 3,875 hours; in France, nuclear matches in 4,905 hours. These provide local bid evidence. In **NO5, 8,589/8,760 hours have no matching local interior offer**: its fixed hydro injection has no water-price decision, and its cleared price depends on the coupled network/links rather than an adjustable local water bid. That explains why this local thermal-bid correction has little leverage there; it does not establish which real constraint or hydro assumption is wrong. On 1 October at 17:00 UTC, DE-LU observed EUR 512.59/MWh versus the joint model's EUR 128.92. On 25 November at 15:00 UTC, NO5 observed EUR 266.26 versus EUR 2.86. These need different investigations, rather than one common price offset.

## 3. The targeted model change

Each zone/resource receives at most **one new coefficient** multiplying its centered local Saturday/Sunday indicator, $w=I_{{weekend}}-E[I_{{weekend}}]$. Existing 15 seasonal/time-of-day columns are included as nuisance controls in fitting; only the new weekly coefficient is applied. Thus we test the omitted weekly pattern without refitting all existing parameters or introducing residual-demand predictors.

Fit support requires the resource to be locally interior, over 0.001 MW from both bounds, and its offer to match the cleared local price within EUR 0.00001/MWh. At least 168 supported hours and 24 of each day type are required; unsupported resources receive zero correction. All 2025 observed prices inform this explicitly labelled reconstruction. A ridge of 168 and response clipping at +/-EUR 100/MWh reduce isolated-event influence. Weekly coefficient bounds are +/-EUR 30/MWh for gas/coal and +/-EUR 7.5/MWh for nuclear. In the joint case, {gas} gas, {coal} coal and {nuc} nuclear zone coefficients have nonzero support.

The same additive adjustment applies to every block of that zone/resource; final bids remain nonnegative and block ordering is preserved. The weekly term has zero annual mean before the final floor. It changes offers **before clearing**, never overwrites a cleared price. At inference it uses calendar and saved coefficients only. Wind/solar availability, fixed hydro, capacities, demand, network constraints and all other bids remain identical to the corresponding anchor.

The declared design tests exactly **two full-year corrections**, one per anchor, with no strength sweep or after-the-fact refit. Each must improve its own anchor's annual price MAE without worsening within-day, generation or trade scores by more than 2%; all 8,760 hours must be optimal with no emergency supply. These are research safeguards, not a product-acceptance or forecasting certificate.

## 4. Full-year results

Price and within-day columns are EUR/MWh. Generation and implied-trade scores are normalized monthly distances outside conditional allocation intervals, **not percentage TWh errors**; lower is better. Generation uses Wind/Solar/Nuclear/Gas/Coal national Ember observations; implied trade is generation minus demand, not verified physical border flow. Missing targets stay unknown.

| Anchor → same model with weekly bids | Price MAE | Within-day MAE | Generation score | Trade score | Declared filter |
| --- | ---: | ---: | ---: | ---: | --- |
{table}

The correction reduces aggregate MAE by **{improvements[0]:.2f}%** on the accepted baseline and **{improvements[1]:.2f}%** on the joint checkpoint. Mean zonal correlation changes **{corr[0]:.3f}→{corr[1]:.3f}** and **{corr[2]:.3f}→{corr[3]:.3f}**, respectively. Both pass the declared filters. This is a modest improvement: the joint version slightly worsens within-day MAE and implied-trade score, though within the predeclared 2% bound. A successful fit is not a claim that every zone or metric improves.

![All modeled zones: full-year price MAE before and after the weekly supply-bid correction]({prefix}zone-mae-grid.png)

| Zone | Accepted baseline | Baseline + weekly | Joint checkpoint | Joint + weekly |
| --- | ---: | ---: | ---: | ---: |
{zone_table}

![Weekly error contrast and remaining seasonal regional bias]({prefix}national-mix.png)

The weekly comparison is descriptive: demand, weather and network conditions differ between day types. The fitted term controls the existing smooth seasonal/local-clock features but cannot establish a causal bidding effect. Nordic north/south and monthly biases remain visible rather than being averaged away.

![Hourly observed and modeled prices during a shared November error episode]({prefix}daily-prices.png)

The November window was chosen from both anchors' error inventory before evaluating the weekly correction. It illustrates a remaining difficult episode; headline metrics use the entire year. A successful calendar correction would still leave resource availability, scarcity premiums, operating constraints and Nordic injection/constraint geography to investigate independently. Fixed hydro has no flexible water bid to calibrate in this formulation.

## 5. Data, verification and conclusion

**Observed prices:** retained ENTSO-E A44 series, UTC-aligned to hourly 2025. Demand is the retained ENTSO-E/PyPSA-Eur-derived source input; geographic allocation/proxy limitations persist. **Supply:** PyPSA-Eur plant/network lineage, original processed weather profiles, IRENA end-2024/end-2025 wind/solar trajectories under assumed linear commissioning, retained NVE-backed fixed Norwegian hydro schedule and inherited other-country schedules. **Generation targets:** monthly national Ember; available weather supply is never replaced by reported generation or dispatch. **Fuel anchors:** inherited monthly World Bank TTF/Brent and ECB conversion, flat carbon and coal/lignite assumptions; this experiment does not adopt daily-fuel sensitivities. National capacity/quantity coverage is distinct from commercial bid-zone completeness. The model is EUPHEMIA-inspired, not a reproduction of actual block orders/allocation rules.

Independent replay reconstructs coefficients with an augmented least-squares calculation, altered offer vectors, all original source bounds and native component equations, primal/dual optimality, objectives and monthly quantities. Both tests contain 8,760 optimal hours and zero emergency supply. Maximum native residual **{maxphys:.2g} MW**, duality gap **EUR {maxgap:.6f}**. New annual clearing loops total **{sum(v['clearing_seconds'] for v in s['annuals'].values()):.2f}s**; source/model preparation **{s['preparation_seconds']:.2f}s**, complete driver **{s['end_to_end_seconds']:.2f}s**, separate independent audit **{audit['elapsed_seconds']:.2f}s**. These runtime components are kept distinct.

The useful change is to diagnose errors by event and market regime before changing more grid parameters. The weekly term is one controlled supply-bid hypothesis, not a general repair for the high-price tail or Nordic geography. The below-EUR 10/MWh target remains unmet; no automatic baseline promotion, browser integration or verified investment-return claim follows. Fitting 2025 prices and checking generation/physics does not establish future-year forecast accuracy.

- [All-zone error metrics and weekday/weekend bias]({prefix}hourly-error-zones.csv), [price regimes, monthly errors and worst event days]({prefix}hourly-error-periods.csv).
- [Prior joint calibration cases]({prefix}joint-search-cases.csv), [joint zonal price metrics]({prefix}joint-prices-by-zone.csv), [national five-fuel quantities and conditional bounds]({prefix}joint-generation-by-country.csv). These describe the preceding checkpoint, not the new weekly corrections.
- [Compact provenance and audit receipt]({prefix}summary.json). Raw inputs and full hourly witnesses remain locally cached outside Git. [Workbench methodology](/docs/workbench-methodology/).
'''
    receipt=dict(summary_sha256=digest(folder/'summary.json'),audit=audit,producer_sha256=s['producer_sha256'],helper_sha256=s['dependencies']['weekly_supply_bids_2025.py'],diagnosis_producer_sha256=s['dependencies']['hourly_error_events_2025.py'],renderer_sha256=digest(__file__),design=s['design'],results=results,annuals=s['annuals'],labels=labels,shown=order,
        diagnostics={k:{n:v for n,v in details[k].items() if n not in ['zones']} for k in order},active_weekly_coefficients={k:[r for r in v['support'] if r['coefficient']!=0] for k,v in coeff.items()},mechanisms={k:[r for r in v if r['zone'] in ['NO5','DE-LU','ES','FR']] for k,v in mechanisms.items()})
    return report,receipt
