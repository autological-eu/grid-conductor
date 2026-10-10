"""Same-observation annual evaluation of fixed hydro with simple resource bids."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from hybrid_fixed_hydro_2025 import ROOT,VARIANTS,HOURS,load,compiled,resource_costs,verified_fuel
from simple_resource_bids import cost_assumptions
from compare_daily_dispatch_prices import metrics,model_area,audit_observations
from hourly_renewable_estimates import digest
OUT=ROOT/'public/research/fixed-reservoir-screening-2025'
LABELS=dict(legacy='Legacy fixed hydro',fuel_only='Gas/oil fuel update',resource_bids='Combined simple resource bids')


def evaluate(folder):
    summary=json.loads((folder/'summary.json').read_text());replay=json.loads((folder/'replay.json').read_text())
    if summary['hours']!=8760 or replay['summary_sha256']!=digest(folder/'summary.json'):raise ValueError('Complete replayed annual run required')
    for name,sha in summary['provenance']['dependencies'].items():
        if digest(ROOT/'tools'/name)!=sha:raise ValueError('Changed calculation source')
    prices={}
    for variant in VARIANTS:
        if digest(folder/(variant+'.npz'))!=summary['cases'][variant]['witness_sha256']:raise ValueError('Changed annual witness')
        with np.load(folder/(variant+'.npz'),allow_pickle=False) as a:prices[variant]=a['prices'].copy()
    areas=summary['zones'];root=ROOT/'data/price-trace/dispatch-validation-2025-v2'
    manifest=json.loads((root/'manifest.json').read_text());rows=[];excluded=[];observations={}
    dates=pd.date_range('2025-01-01',periods=8760,freq='h');monthly=[]
    for zone,meta in sorted(manifest['zones'].items()):
        area,scope=model_area(zone);path=root/(zone+'.json')
        if area not in areas:excluded.append(dict(zone=zone,reason=scope));continue
        if digest(path)!=meta['hourly_sha256']:raise ValueError('Changed observations')
        observed=np.array([np.nan if v is None else v for v in json.loads(path.read_text())])
        audit_observations(zone,meta,observed)
        if not np.isfinite(observed).any():excluded.append(dict(zone=zone,reason='No observed A44 prices available'));continue
        observations[zone]=observed;models={}
        for variant in VARIANTS:
            models[variant]=metrics(prices[variant][:,areas.index(area)],observed)
            monthly.append(dict(zone=zone,variant=variant,months=[metrics(prices[variant][dates.month==i,areas.index(area)],observed[dates.month==i]) for i in range(1,13)]))
        rows.append(dict(zone=zone,area=area,mapping_scope=scope,observation_sha256=digest(path),models=models))
    # Equal weight per physical area; repeated Norway/Sweden/Italy proxies are not extra areas.
    macro={}
    for variant in VARIANTS:
        area_mae={area:np.mean([r['models'][variant]['mae_eur_mwh'] for r in rows if r['area']==area]) for area in sorted({r['area'] for r in rows})}
        macro[variant]=dict(physical_areas=len(area_mae),mean_area_mae_eur_mwh=float(np.mean(list(area_mae.values()))),area_mae_eur_mwh=area_mae)
    targets=json.loads((ROOT/'public/research/entsoe-fast-targets.json').read_text())['targets'];pairs=sorted({tuple(sorted(r['border'].split('>'))) for r in targets});borders=[]
    for a,b in pairs:
        if a not in observations or b not in observations:continue
        za,_=model_area(a);zb,_=model_area(b);observed=observations[a]-observations[b];valid=np.isfinite(observed);gap=valid&(abs(observed)>5)
        record=dict(border=a+'|'+b,known_hours=int(valid.sum()),observed_gap_hours=int(gap.sum()),same_model_area=za==zb,models={})
        for variant in VARIANTS:
            modeled=prices[variant][:,areas.index(za)]-prices[variant][:,areas.index(zb)];error=modeled[valid]-observed[valid]
            record['models'][variant]=dict(mae_eur_mwh=float(abs(error).mean()),bias_eur_mwh=float(error.mean()),
                modeled_gap_hours=int(np.count_nonzero(valid&(abs(modeled)>5))),
                direction_agreement_on_observed_gaps=float(np.mean(np.sign(modeled[gap])==np.sign(observed[gap]))) if gap.any() else None)
        borders.append(record)
    n,base,common=load();market=verified_fuel(ROOT/summary['provenance']['fuel_path']);assumptions,_=cost_assumptions()
    curves=[]
    for variant in VARIANTS:
        m=compiled(n,base,resource_costs(n,base['cost'],market,assumptions,variant));z=areas.index('0:DE');mask=m['offer_zones']=='0:DE'
        mask&=~m['emergency_mask']
        for hour in HOURS:
            bids=m['cost'][hour,mask];volume=m['availability'][hour,mask];order=np.argsort(bids,kind='stable')
            curves.append(dict(variant=variant,utc=str(dates[hour]),cost_eur_mwh=bids[order].tolist(),volume_mw=volume[order].tolist(),
                clearing_price_eur_mwh=float(prices[variant][hour,z]),observed_de_lu_eur_mwh=float(observations['DE-LU'][hour]),
                residual_domestic_demand_mw=float(base['load'][hour,z])))
    fig,axes=plt.subplots(3,1,figsize=(12,10),layout='constrained')
    for j,hour in enumerate(HOURS):
        for c in [c for c in curves if c['utc']==str(dates[hour])]:
            axes[j].step(np.r_[0,np.cumsum(c['volume_mw'])]/1000,np.r_[c['cost_eur_mwh'][0],c['cost_eur_mwh']],where='pre',label=LABELS[c['variant']])
        c=next(c for c in curves if c['utc']==str(dates[hour]) and c['variant']=='resource_bids')
        axes[j].axhline(c['clearing_price_eur_mwh'],color='black',linestyle='--',label='Combined network clearing price')
        axes[j].axhline(c['observed_de_lu_eur_mwh'],color='gray',linestyle=':',label='Observed DE-LU price')
        axes[j].axvline(c['residual_domestic_demand_mw']/1000,color='gray',alpha=.4)
        axes[j].set(title=c['utc']+' UTC — domestic offers, network clearing includes trade',ylabel='EUR/MWh',xlabel='Cumulative domestic offered capacity GW');axes[j].legend(fontsize=8,ncol=2)
    bid_image=OUT/'resource-bids-curves.png';fig.savefig(bid_image,dpi=120);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(12,11),layout='constrained');z=areas.index('0:DE')
    observed=pd.Series(observations['DE-LU'],index=dates).resample('7D').mean();axes[0].plot(observed.index,observed,label='Observed ENTSO-E DE-LU',color='black')
    for variant in VARIANTS:
        series=pd.Series(prices[variant][:,z],index=dates).resample('7D').mean();axes[0].plot(series.index,series,label=LABELS[variant],alpha=.8)
    axes[0].set(title='2025 German price proxy: seven-day means, identical observed coverage',ylabel='EUR/MWh');axes[0].legend(fontsize=8)
    x=np.arange(1,13)
    for j,variant in enumerate(VARIANTS):
        r=next(r for r in monthly if r['zone']=='DE-LU' and r['variant']==variant)
        axes[1].bar(x+(j-1)*.25,[m['mae_eur_mwh'] for m in r['months']],width=.25,label=LABELS[variant])
    axes[1].set(xticks=x,xlabel='Month',ylabel='MAE EUR/MWh',title='German proxy: monthly absolute error');axes[1].legend(fontsize=8)
    x=np.arange(len(rows))
    for j,variant in enumerate(VARIANTS):axes[2].bar(x+(j-1)*.25,[r['models'][variant]['mae_eur_mwh'] for r in rows],width=.25,label=LABELS[variant])
    axes[2].set(xticks=x,xticklabels=[r['zone'] for r in rows],ylabel='MAE EUR/MWh',title='All mapped observed zones, including adverse outcomes');axes[2].tick_params(axis='x',rotation=90);axes[2].legend(fontsize=8)
    price_image=OUT/'resource-bids-errors.png';fig.savefig(price_image,dpi=120);plt.close(fig)
    p=summary['provenance'].copy();audit=p.pop('capacity_audit');p['capacity_audit_canonical_sha256']=__import__('hashlib').sha256(json.dumps(audit,sort_keys=True).encode()).hexdigest()
    public=dict(status=summary['status'],hours=8760,zones=areas,cases=summary['cases'],provenance=p,replay=replay,
        water_residual_mwh=summary['water_residual_mwh'],common_preparation_seconds=summary['common_preparation_seconds'],
        elapsed_seconds=summary['elapsed_seconds'],peak_rss_mib=summary['peak_rss_mib'],
        retained_legacy_maximum_objective_difference_eur=summary['retained_legacy_maximum_objective_difference_eur'],
        retained_legacy_maximum_dual_difference_eur_mwh=summary['retained_legacy_maximum_dual_difference_eur_mwh'],
        mapped_zone_errors=rows,excluded=excluded,monthly_errors=monthly,physical_area_weighted_diagnostic=macro,border_spreads=borders,
        german_offer_examples=curves,fuel_monthly_inputs=market['monthly'],raw_fuel_provenance=market['provenance'],
        publication_producer_sha256=digest(__file__),source_summary_sha256=digest(folder/'summary.json'),
        observed_manifest_sha256=digest(root/'manifest.json'),images={p.name:digest(p) for p in [bid_image,price_image]})
    (OUT/'resource-bids.json').write_text(json.dumps(public,separators=(',',':'),allow_nan=False)+'\n')
    de=next(r for r in rows if r['zone']=='DE-LU')['models']
    table='\n'.join(f"| {LABELS[v]} | {summary['cases'][v]['loop_with_live_replay_seconds']:.2f} | {de[v]['mae_eur_mwh']:.2f} | {de[v]['bias_eur_mwh']:.2f} | {de[v]['rmse_eur_mwh']:.2f} | {macro[v]['mean_area_mae_eur_mwh']:.2f} |" for v in VARIANTS)
    cases='\n'.join(f"| {LABELS[v]} | {summary['cases'][v]['solver_seconds']:.2f} | {summary['cases'][v]['bid_compilation_seconds']:.2f} | {summary['cases'][v]['physics']['emergency_supply_twh']:.7f} | {summary['cases'][v]['physics']['shortage_hours']} |" for v in VARIANTS)
    checks='\n'.join(f"| {LABELS[v]} | {c['utc']} | {c['difference_eur']:.8g} |" for v in VARIANTS for c in summary['cases'][v]['native_checks'])
    no=[r for r in rows if r['zone'].startswith('NO')]
    no_table='\n'.join(f"| {r['zone']} | {r['models']['legacy']['mae_eur_mwh']:.2f} | {r['models']['fuel_only']['mae_eur_mwh']:.2f} | {r['models']['resource_bids']['mae_eur_mwh']:.2f} |" for r in no)
    delta=de['resource_bids']['mae_eur_mwh']-de['legacy']['mae_eur_mwh']
    improves=sum(r['models']['resource_bids']['mae_eur_mwh']<r['models']['legacy']['mae_eur_mwh'] for r in rows)
    conclusion=f"The combined bids {'reduce' if delta<0 else 'increase'} German MAE by EUR{abs(delta):.2f}/MWh, and improve MAE in {improves} of {len(rows)} mapped observed zones."
    text=f'''# European hourly dispatch — fixed hydro with resource bids

## Summary and conclusion

We implemented the proposed combination: **fast hourly physical-network clearing,
precomputed fixed hydro, and simple resource-specific generator offers**. It covers
all **8,760 UTC hours of 2025** in {summary['areas']} country/AC-island areas. No
price forecast, adaptive reservoir solve or observed electricity-price input is used.

{conclusion} The combined annual clearing/update/live-replay loop takes
**{summary['cases']['resource_bids']['loop_with_live_replay_seconds']:.2f} seconds**.
This is an untuned comparative experiment, **not accepted market-price accuracy**.
Audited commercial-zone mapping and observed zonal demand remain incomplete.
The browser still uses its existing two-zone screen.

| Bid formulation | Annual loop s | DE MAE EUR/MWh | DE bias EUR/MWh | DE RMSE EUR/MWh | Equal-area mean MAE EUR/MWh |
| --- | ---: | ---: | ---: | ---: | ---: |
{table}

Both price comparisons use the **same direct ENTSO-E A44 series**, hours and
geographic proxy. The older checkpoint's published EUR23.10/MWh used a different
DE-LU observation series; it must not be substituted into this comparison.
Equal-area MAE first averages zone errors sharing one physical area, then weights
each represented physical area equally ({macro['legacy']['physical_areas']} areas).
It is not demand-weighted European market accuracy.

## Generator strategies and data

- **Gas/CCGT/OCGT and oil:** offer = fuel price / efficiency + carbon price ×
  operational emission factor / efficiency + variable O&M. Replace the prepared
  total cost; do not add fuel or carbon twice. Gas/oil inputs are twelve observed
  World Bank monthly TTF/Brent benchmarks, converted with ECB daily FX and repeated
  over UTC hours. Carbon is a constant **EUR80/t assumption**, not historical EUA.
  Heating-value multiplier 1 and Brent at 1.7 MWh thermal/barrel remain proxies;
  Brent is not delivered power-plant oil fuel. No daily fluctuations are invented.
- **Coal/lignite:** the same explicit formula, with prepared technology-table
  fuel constants rather than observed 2025 commodity quotes.
- **Wind/solar:** weather-limited availability and EUR0/MWh offers in the complete
  simple-bid variant. Legacy and fuel-only retain EUR−5/MWh offers. This low-price
  rule is an assumption; subsidy-specific or strategic bids are not reconstructed.
- **Nuclear, biomass, waste, geothermal and run-of-river:** labelled prepared
  operating-cost/availability proxies. Nuclear has no commitment/ramp/must-run
  representation; source availability ending in 2024 is explicitly a 2025 proxy.
- **Reservoir hydro:** the same audited precomputed hourly electrical injections
  in every variant, never renewable availability or a variable bid volume.
  Turbine/inflow/efficiency/spill/stock/closure checks preserve the retained source
  schedule and its inherited model inventory boundaries. These are not observed
  Norwegian reservoir stocks. Other 67 battery/PHS units remain excluded.

The **fuel-only** ablation changes gas/oil bids alone, keeping other legacy offers.
The **complete simple-bid** variant uses the current resource-bidding compiler's
rules, including all five thermal types and zero-price renewables. These variants
were specified before this annual run. No electricity-price fitting, parameter
selection for market acceptance or empirical pass threshold is claimed.

IRENA end-2024/end-2025 linear wind/PV commissioning, original hourly weather,
generator capacity/availability, prepared network demand, GSKs and all constraints
are identical across variants. Demand is currently the **prepared PyPSA-Eur proxy**,
not an independently audited ENTSO-E zonal-demand input. The requested observed-demand
and bidding-zone upgrade remains blocked on source/mapping verification; schematic
map centroids are not geographic asset mappings. No missing zonal data are fabricated.

## Physical clearing and speed

Each hour clears synthetic supply against inelastic residual demand, after fixed
hydro injections. Original passive-network PTDF/GSK constraints and
{summary['passive_branches']} branch ratings are preserved, along with
{summary['controllable_links']} native controllable links, signed bounds and efficiencies.
These are N-0 physical approximations, not audited commercial JAO capacities.
Country labels remain separate by AC island, not NO1–NO5 commercial zones.

Identical-column, identical-hourly-price offers can be merged exactly: each has the
same area and network effect. Installed-capacity GSKs do not change with merging.
Hourly vectors update a persistent one-thread HiGHS simplex model and reuse its basis.
There is no temporal reservoir/forecast optimisation. Per-hour deadlines use the
solver's cumulative clock correctly; unchanged-input cold retries are recorded.

| Variant | Actual solver s | Bid compilation/merge s | Emergency TWh | Shortage hours |
| --- | ---: | ---: | ---: | ---: |
{cases}

Common source/hydro preparation took {summary['common_preparation_seconds']:.2f}s.
The full command for **three annual variants, nine native checks, component replay
and witness export** took {summary['elapsed_seconds']:.2f}s, peak RSS
{summary['peak_rss_mib']:.0f} MiB. These are separate from report generation and the
subsequent independent audit. The highlighted loop is not end-to-end runtime or a
browser benchmark. Offline hydro-schedule creation is excluded. The retained
legacy benchmark remains 19.17s plus 6.73s preparation; today's controlled legacy
run measures the same formulation with exact offer aggregation.

## German supply curves and clearing examples

![Domestic German supply offers and coupled clearing prices](/research/fixed-reservoir-screening-2025/resource-bids-curves.png)

Three preselected January/July/December hours show domestic offered capacity by
price. The vertical line is domestic residual demand; horizontal lines show the
network-cleared combined price and observed DE-LU price. **The domestic curve's
intersection is not the coupled clearing solution**: imports, exports and physical
constraints enter the Europe-wide solve. Examples and all bid volumes/prices are
included in the compact data download.

## Full-year observed-price evaluation

![Annual, monthly and all-zone price comparisons](/research/fixed-reservoir-screening-2025/resource-bids-errors.png)

All {len(rows)} eligible mapped observed zones are included, preserving missingness
and signed prices. Raw A44 request domains, response hashes and hourly aggregation
are rechecked. Full-year, monthly, negative-price and border-spread diagnostics are
available in the download: {len(borders)} observed border pairs. No congestion-rent
or investment benefit follows merely from price agreement.

The German combined model has {de['resource_bids']['model_negative_hours']} negative
hours versus {de['resource_bids']['observed_negative_hours']} observed. Simple
renewable and nuclear rules cannot reconstruct all negative-price behaviour.
Four unavailable observed series and unresolved Italian island mappings are
excluded explicitly in the data; country prices reused for Norway, Sweden and
mainland Italy are disclosed.

| Observed Norwegian zone | Legacy MAE EUR/MWh | Fuel-only MAE EUR/MWh | Complete bids MAE EUR/MWh |
| --- | ---: | ---: | ---: |
{no_table}

These five observations are compared with one Norwegian country proxy. Fixed
hydro avoids the rolling experiment's scheduling decisions, but does not validate
hydrology, resolve internal bottlenecks or recover distinct Norwegian prices.

## Numerical verification

Every variant completes 8760 optimal hours. An independent process reconstructs
sources/offers and saved primals, checks generation/link bounds and area balances,
then reconstructs nodal injections from GSKs and native link endpoints, checks
island balances and computes passive flows outside the LP constraint matrix.
All component residuals pass 1e−4 MW; water residual is
{summary['water_residual_mwh']:.3g} MWh with unchanged annual closure. No adaptive
storage or simultaneous charge/discharge is introduced.

| Variant | UTC hour | Native PyPSA minus fast objective EUR |
| --- | --- | ---: |
{checks}

Native PyPSA independently builds the same physical network and zonal GSK
constraints with fixed injections. Agreement verifies formulation, not market
prices. Controlled legacy hourly objectives reproduce the retained checkpoint
within EUR{summary['retained_legacy_maximum_objective_difference_eur']:.6f}; dual prices
can differ under degeneracy (maximum difference
EUR{summary['retained_legacy_maximum_dual_difference_eur_mwh']:.6f}/MWh).

## What remains before scenario acceptance

This establishes a fast, reproducible combined baseline and a fair price comparison.
It does not show that added bid complexity automatically improves prices everywhere.
Next are audited bidding-zone assets/demand, outages and commercial constraints,
explicit training/untouched validation periods and empirical thresholds, followed
by common-input native/replay investment pairs. Transmission and wind/solar cases
remain conditional on fixed hydro; adaptive battery/hydro valuation needs chronology.
No paused adaptive-hydro search or browser replacement has been resumed.

[Combined results, source/fuel provenance, all-zone/monthly/border errors and bid examples](/research/fixed-reservoir-screening-2025/resource-bids.json)

[Retained fixed-hydro checkpoint summary](/research/fixed-reservoir-screening-2025/summary.json.gz)
· [retained area summaries](/research/fixed-reservoir-screening-2025/area-summary.csv)
· [retained German hourly results](/research/fixed-reservoir-screening-2025/hourly-de.csv.gz)
· [water replay](/research/european-reservoir-clearing-2025/replay.json).

Reproduction: tools/hybrid_fixed_hydro_2025.py with a fresh --output directory,
then the same tool with --audit, then tools/evaluate_fixed_hydro_bids_2025.py --run.
Use the pinned Python environment, bounded resources and existing verified source
caches; raw inputs and full annual primals remain outside Git.
'''
    (ROOT/'docs/european-physical-synthetic-clearing-2025.md').write_text(text)
    print(json.dumps(dict(germany=de,macro=macro,zone_improvements=improves,mapped_zones=len(rows)),allow_nan=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);args=p.parse_args();evaluate(args.run)
