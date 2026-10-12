"""Publish the audited whole-network zonal model in the retained dispatch report."""
import argparse,json,collections,datetime as dt
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from nve_hydro_diagnostics import ROOT,digest
from compare_daily_dispatch_prices import metrics
from collect_bidding_zone_sources_2025 import SOURCES

OUT=ROOT/'public/research/fixed-reservoir-screening-2025'

def country(zone):
    if zone=='DE-LU':return 'DE'
    if zone=='IE-SEM':return 'IE'
    if zone.startswith(('NO','SE','DK','IT-')):return zone[:2]
    return zone

def publish(folder):
    s=json.loads((folder/'summary.json').read_text());a=json.loads((folder/'audit.json').read_text());m=json.loads((folder/'mapping.json').read_text())
    assert a['source_summary_sha256']==digest(folder/'summary.json')
    assert a['audit_producer_sha256']==digest(ROOT/'tools/audit_bidding_zone_network_2025.py')
    assert s['compiler_sha256']==digest(ROOT/'tools/bidding_zone_network_2025.py')
    c=s['cases']['country'];z=s['cases']['bidding_zone'];comparisons=[]
    with np.load(folder/'annual.npz',allow_pickle=False) as saved:
        cp=saved['country_prices'].copy();zp=saved['bidding_zone_prices'].copy()
    observations=ROOT/'data/price-trace/dispatch-validation-2025-v2'
    for r in z['observed_price_comparisons']:
        if r['metrics']['known_hours']==0:continue
        zone=r['zone'];label=r['model_area'];base=country(label)
        if base not in c['zones']:continue
        obs=np.array(json.loads((observations/(zone+'.json')).read_text()),dtype=float)
        before=cp[:,c['zones'].index(base)];after=zp[:,z['zones'].index(label)];common=np.isfinite(obs)&np.isfinite(before)&np.isfinite(after);matched=obs.copy();matched[~common]=np.nan
        comparisons.append(dict(zone=zone,country_control=metrics(before,matched),bidding_zone=metrics(after,matched),all_zonal_available_hours=r['metrics']))
    comparisons.sort(key=lambda r:r['bidding_zone']['mae_eur_mwh'],reverse=True)
    fig,axes=plt.subplots(2,1,figsize=(12,10),layout='constrained');x=np.arange(len(comparisons))
    axes[0].bar(x-.18,[r['country_control']['mae_eur_mwh'] for r in comparisons],.36,label='Country pools, refined grid',color='#94a3b8')
    axes[0].bar(x+.18,[r['bidding_zone']['mae_eur_mwh'] for r in comparisons],.36,label='Bidding-zone pools, same refined grid',color='#2563eb')
    axes[0].set(xticks=x,xticklabels=[r['zone'] for r in comparisons],ylabel='Price MAE EUR/MWh',title='All eligible observed areas, common available hours — no fitting');axes[0].tick_params(axis='x',rotation=90);axes[0].legend(fontsize=9)
    offsets=[0,744,1416,2160,2880,3624,4344,5088,5832,6552,7296,8016,8760]
    for zone in ['NO1','NO2','NO3','NO4','NO5']:
        series=zp[:,z['zones'].index(zone)];axes[1].plot(range(1,13),[np.nanmean(series[offsets[i]:offsets[i+1]]) for i in range(12)],marker='o',label=zone)
    axes[1].set(xlabel='UTC month in 2025',ylabel='Modeled mean price EUR/MWh',title='Norwegian zones now clear separately');axes[1].legend(ncol=5)
    fig.savefig(OUT/'bidding-zone-errors.png',dpi=110);plt.close(fig)
    missing=[zone for zone in z['zones'] if not any(r['model_area']==zone and r['metrics']['known_hours'] for r in z['observed_price_comparisons'])]
    methods=dict(collections.Counter(r['method'] for r in m['allocation']))
    mapping=dict(sources=m['sources'],nve_summary_sha256=m['nve_summary_sha256'],raw_buses=m['raw_buses'],refined_buses=m['refined_buses'],mixed_clusters=m['mixed_clusters'],protected_simplification_crossings=m['protected_simplification_crossings'],security_factor=m['security_factor'],allocation_methods=methods,extra_emergency=m['extra_emergency'],mapping_methods=dict(collections.Counter(r['method'] for r in m['membership'])),limitations=m['limitations'])
    public=dict(summary=s,audit=a,mapping=mapping,geographic_source_urls=SOURCES,source_collection_producer_sha256=digest(ROOT/'tools/collect_bidding_zone_sources_2025.py'),common_hour_comparisons=comparisons,model_areas_without_observations=missing,publication_producer_sha256=digest(__file__),image_sha256=digest(OUT/'bidding-zone-errors.png'))
    (OUT/'bidding-zone-model.json').write_text(json.dumps(public,separators=(',',':'),allow_nan=False)+'\n')
    errors='\n'.join(f"| {r['zone']} | {r['bidding_zone']['known_hours']} | {r['country_control']['mae_eur_mwh']:.2f} | {r['bidding_zone']['mae_eur_mwh']:.2f} | {r['bidding_zone']['bias_eur_mwh']:+.2f} | {r['bidding_zone']['correlation']:.3f} |" for r in comparisons)
    checks='\n'.join(f"| {case} | {r['hour']} | {r['objective_difference_eur']:.3g} |" for case,v in s['cases'].items() for r in v['native_checks'])
    failures='; '.join(f"hour {r['hour']}: {r['status']}" for r in z['failures']) or 'None'
    country_failures='; '.join(f"{(dt.datetime(2025,1,1)+dt.timedelta(hours=r['hour'])).isoformat()} UTC: {r['status']}" for r in c['failures']) or 'None'
    status=('All 8,760 zonal hours terminate optimal.' if z['optimal_hours']==8760 else f"**{z['optimal_hours']} of 8,760 zonal hours terminate optimal; remaining hours are excluded only where the model failed, with explicit counts. This is not a complete feasible annual benchmark.**")
    # Reproduce methodology from immutable inputs, not the previous Markdown.
    path=ROOT/'docs/european-physical-synthetic-clearing-2025.md'
    nve_path=ROOT/'data/hydro-observations-2025/nve-updated-model-v5/summary.json'
    assert digest(nve_path)==m['nve_summary_sha256']
    hydro=json.loads(nve_path.read_text())['hydro_source']
    water=f'''### Resource bids and source-backed hydro

Simple resource offers retain sourced monthly gas/oil prices (World Bank TTF/Brent
and ECB FX) and the existing carbon/efficiency assumptions. Observed electricity
prices do not enter bid construction. The pinned PyPSA-Eur v2026.08.0 backbone
uses retained 2025 weather profiles and source/replay coefficients. IRENA linear
end-2024/end-2025 wind/solar capacity interpolation is assumed commissioning,
not observed installation dates. Nuclear availability ending in 2024 is a proxy.

Norway uses [NVE's weather-driven HBV usable inflow]({hydro['method_url']}),
**{hydro['calendar_inflow_twh']:.3f} TWh** aligned to 8,760 UTC hours. Full weeks
preserve the original ERA5 hourly shape; partial boundary weeks use uniform rates
over their source week. DST weeks retain 167/169 hours. The generation/stock-derived
inflow column is excluded. Observed generation does not set the water budget.

Electrical-equivalent opening/closing stocks are
**{hydro['initial_electrical_stock_twh']:.3f} → {hydro['final_electrical_stock_twh']:.3f} TWh**,
with **{hydro['storage_electrical_capacity_twh']:.3f} TWh** reservoir capacity.
Water, stocks and capacity are converted to stored units by dividing by original
turbine efficiency 0.9; efficiency is applied once on discharge. Original turbine
MW remains unchanged. A shortage-aware delivery envelope and seasonal-pattern
penalty prepare the fixed schedule, not an annual economic optimum. Other countries
retain their source schedules. No daily reset or additional water is introduced.

HBV history was revised in June 2026, so inputs are retrospective. Gross reservoir
stock/net usable inflow are assumed compatible electrical equivalents; catchment
routing, cascades, country-pooled reservoir/run-of-river shares and regional water
allocation remain unresolved. Fixed Norwegian reservoir output remains 139.215 TWh;
total hydro including dispatched run-of-river may change with network constraints.
Previous-model total-generation bounds are not reused for this new model.
'''
    text=f'''# European hourly dispatch — whole-network bidding-zone model

## Summary and conclusion

The model now uses **{len(z['zones'])} distinct clearing areas across the entire
retained European network**, including NO1–NO5, SE1–SE4, DK1/DK2 and Italy's seven
zones. DE and LU share DE-LU; Ireland/Northern Ireland share the Single Electricity
Market. Mallorca joins ES. Separate peripheral source areas such as Corsica and
Kosovo are retained and explicitly lack observed-price verification; they are not
claims of SDAC participation or certified commercial boundaries.

**{len(m['mixed_clusters'])} old clusters crossed zone boundaries.** Rebuilding them
from source bus membership, rather than assigning a centroid, increases the grid
to **{m['refined_buses']} buses**. The audit also identified **{len(m['protected_simplification_crossings'])}
crossings lost at the earlier stub-removal stage**; the new backbone starts before
that removal. Original uniform security factor **{m['security_factor']:.3g}** remains.

{status} Annual zonal clearing takes **{z['loop_seconds']:.2f}s**, excluding one-time
preparation, native checks, replay, export and reporting. Emergency generation is
**{z['emergency_mwh']:.6f} MWh** over {z['shortage_hours']} solved hours. The model is
an untuned diagnostic, not an accepted market-price or investment estimator.

The comparison below isolates country versus bidding-zone pooling on **the same
rebuilt grid**. It is not directly attributable to the geography change alone when
compared with the earlier 128-bus report: topology and branch aggregation also changed.
All original hourly parent demand, available supply and fixed reservoir output are
conserved. We have not fitted supply, demand or water to ENTSO-E prices.

Country-control failures: **{country_failures}**. A fresh solver reproduced the
reported termination. Its comparisons use common solved hours; the zonal model
still covers the full year. Country pooling restricts spatial dispatch through
its GSK and can fail where finer zonal decisions find a feasible allocation.

## Geographic and physical formulation

1. Retrieve and hash pinned [Electricity Maps geographic areas](https://github.com/electricitymaps/electricitymaps-contrib/tree/master/geo),
   [NVE's official Norwegian price-area polygons](https://gis3.nve.no/map/rest/services/Mapservices/Omradekonsesjoner/MapServer/0)
   and [entsoe-py's Italian zones](https://github.com/EnergieID/entsoe-py/tree/master/entsoe/geo/geojson), including Calabria.
   These are retrospective releases; historical 2025 boundary certification is open.
2. Map original onshore buses to polygons. Uncontained coastal points use a bounded
   nearest-polygon proxy, explicitly recorded. Offshore nodes use an electrical
   path to a same-country shore connection, not a cluster-centroid assignment.
3. Apply pinned upstream voltage-layer, converter and DC-chain routines. Do not
   remove country-only stubs. Split each old cluster by actual member zone BEFORE
   branch aggregation, preserving cross-zone branches and native HVDC bounds/losses.
4. Maintain **one clearing balance and price per modeled market area**, including
   areas spanning AC islands. Physical island balances remain separate. Capacity
   GSK fractions distribute generation; actual fixed hydro and demand enter at
   their allocated physical buses. Native PTDFs retain constraints inside zones;
   membership in a common zone does not create an unconstrained inter-island link.
5. Check source-reconstructed demand, offers, hydro and saved-primal physics.
   Compare against native PyPSA formulations and report every failed hour.

This is a synthetic zonal dispatch model with model-derived N-0 constraints,
not EUPHEMIA's full order allocation, published JAO commercial domains, outages,
contingencies or operator redispatch. Static generation shift keys remain a proxy
for intrazonal dispatch. Native parity verifies the formulation, not market realism.

## Conserved supply, demand and water inputs

Original generator cost and weather-availability time series remain unchanged.
For a mixed cluster, sourced dated plant-capacity shares allocate thermal and
reservoir assets between child areas. Missing or unsupported location detail,
including aggregate renewable profiles, uses explicit raw-member-count shares.
These are allocation assumptions, not newly measured bidding-zone capacity or
weather. Allocation methods across original generators/reservoirs: **{methods}**.
Commissioning/out-of-service dates filter the plant-location weights where known.

Demand uses the existing preclustered 2025 hourly series, with member-count splits
where its earlier spatial aggregation crossed a boundary. Each original parent's
hourly load remains exactly conserved. This does not turn inherited source demand
into independently audited observed zonal load. The Norwegian 137.04 versus
131.52/134.55 TWh scope discrepancy remains unresolved; no scaling forces agreement.

Fixed reservoir schedules split by the same source shares, preserving each parent's
hourly output, inflow/efficiency, inventory trajectory and terminal boundaries.
No rescheduling, new water, spill or dispatch-for-availability substitution occurs.
Newly separate areas receive the existing EUR10,000 emergency-offer rule where
needed ({len(m['extra_emergency'])} additional diagnostic offers); those MW are never
reported as real fleet capacity. Shortage energy is disclosed separately.

{water}

## Full-year price comparison

![Controlled full-year errors and separate Norwegian modeled prices](/research/fixed-reservoir-screening-2025/bidding-zone-errors.png)

All {len(comparisons)} eligible observed areas use hashed and XML-reparsed ENTSO-E
A44 observations, UTC-aligned hourly. Country and zonal MAE below use common
available hours; downloads also contain all available zonal-hour metrics.
Missing model observations: **{', '.join(missing)}**. Observations never enter offers.
This is descriptive full-year evidence, not a declared held-out acceptance test.

| Observed area | Common hours | Country-pool MAE | Zonal MAE | Zonal bias | Correlation |
| --- | ---: | ---: | ---: | ---: | ---: |
{errors}

Errors are EUR/MWh. Separate zone prices do not guarantee better MAE: inherited
capacity, demand, intrazonal GSK and fixed hydro schedules may still be wrong.
The download includes all metrics, shortage counts and failure/retry records.
Failed zonal hours: **{failures}**. No failed hour is filled with another model's price.

## Numerical verification and measured runtime

Independent saved replay rebuilds sources and checks parent-level supply conservation,
hourly demand/hydro conservation, generator/link bounds, zonal and physical-island
balances, native passive flows and objectives. Maximum changes after allocation:
available supply **{a['maximum_parent_available_supply_change_mw']:.3g} MW**,
demand **{a['maximum_hourly_demand_change_mw']:.3g} MW**, fixed hydro
**{a['maximum_fixed_hydro_change_mw']:.3g} MW**. Replay tolerance remains 0.0001.
Country optimal hours: **{c['optimal_hours']}**; zonal: **{z['optimal_hours']}**.

| Native formulation | Hour index | Native minus fast objective EUR |
| --- | ---: | ---: |
{checks}

Three targeted fixtures verify boundary assignment/rejection, constrained cross-zone
prices and native parity, and common-zone clearing across AC islands with HVDC
losses. The latter rejects fictitious free energy transfer. Source allocation and
physical replay are required independently of objective agreement.

One-time preparation **{s['preparation_seconds']:.2f}s**; country clearing
**{c['loop_seconds']:.2f}s**; zonal clearing **{z['loop_seconds']:.2f}s**;
complete producer with both controls/native checks/export **{s['end_to_end_seconds']:.2f}s**;
peak RSS **{s['peak_rss_mib']:.0f} MiB**. Independent audit and publishing are additional.
No seconds-scale end-to-end claim is made for rebuilding source inputs.

## Reproduction and next weaknesses

Restore geographic sources with `python3 tools/collect_bidding_zone_sources_2025.py`;
pinned hashes reject changes to mutable provider releases. Restore packed metadata
with `python3 tools/pack_model_metadata.py --restore`.
Use the pinned interpreter for `tools/run_bidding_zone_network_2025.py --out <fresh-root>`,
then `tools/audit_bidding_zone_network_2025.py <fresh-root>` and
`tools/report_bidding_zone_network_2025.py <fresh-root>`. Geographic source bytes
and full witnesses stay ignored under `data/bidding-zone-network-2025/`; compact
downloads contain source/code hashes, checks and all observed metrics. Do not
overwrite a completed root or resume with changed coefficients.

**Next:** replace member-count supply/demand allocations with audited zonal fleet,
site/weather and demand data; reconcile total-load definitions. Investigate remaining
fixed-schedule failures/extremes and GSK sensitivity before changing hydro strategy.
Historical boundaries, commercial constraints, empirical thresholds/held-out periods,
paired-investment and static-app integration gates remain open. The public browser
still uses its reduced two-zone screen; publication does not replace that engine.

[Current zonal evidence and all price comparisons](/research/fixed-reservoir-screening-2025/bidding-zone-model.json)
 · [Previous source-backed water/location evidence](/research/fixed-reservoir-screening-2025/nve-hydro-diagnostics.json)
 · [Workbench methodology](/docs/workbench-methodology/)
'''
    path.write_text(text);print('Existing report updated with',len(comparisons),'observed areas')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);publish(p.parse_args().folder)
